import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole, AgentMessage, AgentState, LLMClient, WorldState, EnvironmentUpdate, ResourceType,
    TaskQueue, RingBufferMemory, LongTermMemory, AgentFSM, AgentFSMState,
    ResourceInventory, ReputationManager, AgentConfig, AgentConfigManager,
    Task, TaskPriority, TaskType, ActionResult,
    EnhancedAgentMessage, MessageType,
    FallbackLLMClient, RuleEngine
)


class EnhancedBaseAgent:
    def __init__(
        self,
        role: AgentRole,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        fallback_client: Optional[FallbackLLMClient] = None,
        rule_engine: Optional[RuleEngine] = None,
        config_manager: Optional[AgentConfigManager] = None
    ):
        self.role = role
        self.redis = redis_client
        self.llm = llm_client
        self.fallback_client = fallback_client
        self.rule_engine = rule_engine
        
        self.config_manager = config_manager or AgentConfigManager()
        self.config = self.config_manager.load_config(role)
        
        self.state = AgentState(
            role=role,
            position=self.config.initial_location
        )
        self.current_world_state: Optional[WorldState] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
        
        self.task_queue = TaskQueue()
        self.short_term_memory = RingBufferMemory()
        self.long_term_memory = LongTermMemory()
        self.fsm = AgentFSM()
        self.resources = ResourceInventory()
        self.reputation = ReputationManager()
        
        self.llm_failure_count = 0
        self.last_heartbeat_tick = 0
        self.running = False
        self.last_decision_tick = 0
        
        self._setup_fsm_actions()
    
    def _setup_fsm_actions(self):
        self.fsm.add_entry_action(AgentFSMState.SAFE_MODE, self._on_enter_safe_mode)
        self.fsm.add_entry_action(AgentFSMState.OUT_OF_SERVICE, self._on_enter_out_of_service)
        self.fsm.add_exit_action(AgentFSMState.SAFE_MODE, self._on_exit_safe_mode)
    
    def _on_enter_safe_mode(self, old_state, new_state, **kwargs):
        logger.warning(f"{self.role} entering SAFE MODE, only performing safe actions")
    
    def _on_exit_safe_mode(self, old_state, new_state, **kwargs):
        logger.info(f"{self.role} exiting SAFE MODE, resuming normal operations")
        self.llm_failure_count = 0
    
    def _on_enter_out_of_service(self, old_state, new_state, **kwargs):
        logger.error(f"{self.role} is OUT OF SERVICE, requires repair")
    
    async def _save_state(self):
        state_data = self.state.model_dump()
        await self.redis.hset(f"agent:{self.role.value}:state", mapping=state_data)
    
    async def _load_state(self):
        state_data = await self.redis.hgetall(f"agent:{self.role.value}:state")
        if state_data:
            self.state = AgentState(**{k.decode(): v for k, v in state_data.items()})
    
    async def _publish_message(
        self,
        recipient: AgentRole | str,
        msg_type: MessageType,
        payload: Dict[str, Any],
        correlation_id: Optional[str] = None
    ):
        msg = EnhancedAgentMessage(
            msg_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            sender=self.role,
            recipient=recipient,
            msg_type=msg_type,
            payload=payload,
            correlation_id=correlation_id
        )
        
        channel = f"messages:{recipient}" if recipient != "broadcast" else "messages:broadcast"
        await self.redis.publish(channel, json.dumps(msg.model_dump()))
        logger.debug(f"{self.role.value} published {msg_type} to {recipient}")
    
    async def _publish_heartbeat(self):
        payload = {
            "state": self.fsm.get_state().value,
            "position": self.state.position,
            "resources": self.resources.get_all(),
            "current_task": self.task_queue.current_task.task_id if self.task_queue.current_task else None
        }
        await self._publish_message("broadcast", MessageType.HEARTBEAT, payload)
    
    async def _subscribe_to_messages(self):
        pubsub = self.redis.pubsub()
        await pubsub.subscribe(
            f"messages:{self.role.value}",
            "messages:broadcast",
            "environment_updates"
        )
        
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    data = json.loads(message["data"])
                    await self.message_queue.put(data)
                except Exception as e:
                    logger.error(f"Failed to parse message: {e}")
    
    async def _process_message(self, msg_data: Dict):
        try:
            msg = EnhancedAgentMessage(**msg_data)
        except:
            try:
                old_msg = AgentMessage(**msg_data)
                await self._on_legacy_message_received(old_msg)
                return
            except Exception as e:
                logger.error(f"Failed to parse message: {e}")
                return
        
        if msg.recipient == "broadcast" or msg.recipient == self.role:
            if msg.sender != self.role:
                if not self.reputation.should_trust(msg.sender):
                    logger.warning(f"Ignoring message from untrusted agent {msg.sender}")
                    return
            
            await self._on_enhanced_message_received(msg)
    
    async def _on_enhanced_message_received(self, msg: EnhancedAgentMessage):
        if msg.msg_type == MessageType.TASK_ANNOUNCEMENT:
            await self._handle_task_announcement(msg)
        elif msg.msg_type == MessageType.BID_RESPONSE:
            await self._handle_bid_response(msg)
        elif msg.msg_type == MessageType.COMMIT:
            await self._handle_commit(msg)
        elif msg.msg_type == MessageType.CANCEL_TASK:
            await self._handle_cancel_task(msg)
        elif msg.msg_type == MessageType.RESOURCE_REQUEST:
            await self._handle_resource_request(msg)
        elif msg.msg_type == MessageType.RESOURCE_OFFER:
            await self._handle_resource_offer(msg)
        elif msg.msg_type == MessageType.REPUTATION_UPDATE:
            await self._handle_reputation_update(msg)
        elif msg.msg_type == MessageType.WORLD_STATE:
            if "world_state" in msg.payload:
                self.current_world_state = WorldState(**msg.payload["world_state"])
        elif msg.msg_type == MessageType.ACK:
            pass
    
    async def _on_legacy_message_received(self, msg: AgentMessage):
        if "world_state" in msg.payload:
            self.current_world_state = WorldState(**msg.payload["world_state"])
    
    async def _handle_task_announcement(self, msg: EnhancedAgentMessage):
        if not self.fsm.can_accept_tasks():
            return
        
        task_data = msg.payload.get("task")
        if not task_data:
            return
        
        suitability = self._evaluate_task_suitability(task_data)
        if suitability > 0:
            bid_payload = {
                "task_id": task_data.get("task_id"),
                "suitability": suitability,
                "distance": self._calculate_distance(task_data.get("target_zone", "")),
                "current_load": len(self.task_queue.get_pending_tasks())
            }
            await self._publish_message(
                msg.sender, MessageType.BID_RESPONSE, bid_payload, msg.msg_id
            )
    
    async def _handle_bid_response(self, msg: EnhancedAgentMessage):
        pass
    
    async def _handle_commit(self, msg: EnhancedAgentMessage):
        task_id = msg.payload.get("task_id")
        task = self.task_queue.get_task_by_id(task_id)
        if task:
            task.assigned_to = msg.sender
            logger.info(f"Task {task_id} committed to {msg.sender}")
    
    async def _handle_cancel_task(self, msg: EnhancedAgentMessage):
        task_id = msg.payload.get("task_id")
        if task_id:
            self.task_queue.cancel_task(task_id)
    
    async def _handle_resource_request(self, msg: EnhancedAgentMessage):
        pass
    
    async def _handle_resource_offer(self, msg: EnhancedAgentMessage):
        pass
    
    async def _handle_reputation_update(self, msg: EnhancedAgentMessage):
        updates = msg.payload.get("updates", {})
        for agent_str, score in updates.items():
            try:
                agent = AgentRole(agent_str)
                self.reputation.set_reputation(agent, score)
            except ValueError:
                pass
    
    def _evaluate_task_suitability(self, task_data: Dict) -> float:
        task_type = task_data.get("task_type")
        suitability = 0.5
        
        if self.role == AgentRole.FIRE_RESCUE and task_type in [TaskType.FIREFIGHTING, TaskType.RESCUE]:
            suitability = 0.9
        elif self.role == AgentRole.MEDICAL and task_type == TaskType.MEDICAL_TREATMENT:
            suitability = 0.9
        elif self.role == AgentRole.LOGISTICS and task_type == TaskType.RESOURCE_TRANSPORT:
            suitability = 0.9
        
        return suitability
    
    def _calculate_distance(self, target_zone: str) -> float:
        if target_zone == self.state.position:
            return 0.0
        return 1.0
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        try:
            if not self.fsm.is_active():
                return {"action": "wait", "reason": "Agent not active"}
            
            decision = await self._call_llm_with_fallback(observation, context)
            self.llm_failure_count = 0
            return decision
            
        except Exception as e:
            self.llm_failure_count += 1
            logger.error(f"LLM decision failed (count={self.llm_failure_count}): {e}")
            
            if self.llm_failure_count >= self.config.safe_mode_threshold:
                self.fsm.transition("enter_safe_mode")
            
            return await self._fallback_decision(observation, context)
    
    async def _call_llm_with_fallback(self, observation: Dict, context: Dict) -> Dict:
        prompt = self._build_prompt(observation, context)
        
        if self.fallback_client:
            return await self.fallback_client.call(
                prompt=prompt,
                observation=observation,
                context=context,
                role=self.role
            )
        
        return await self.llm.call(prompt=prompt)
    
    async def _fallback_decision(self, observation: Dict, context: Dict) -> Dict:
        if self.rule_engine:
            return self.rule_engine.decide(self.role, observation, context)
        
        return {"action": "wait", "reason": "Fallback to default action"}
    
    def _build_prompt(self, observation: Dict, context: Dict) -> str:
        parts = []
        parts.append(f"You are {self.role.value} agent in a disaster response simulation.")
        parts.append(f"Current state: {self.fsm.get_state().value}")
        
        if self.task_queue.current_task:
            parts.append(f"Current task: {self.task_queue.current_task.task_type} at {self.task_queue.current_task.target_zone}")
        
        parts.append("\n" + self.short_term_memory.build_context_string(5))
        
        location = self.state.position
        parts.append("\n" + self.long_term_memory.get_relevant_context(location=location, max_events=3))
        
        parts.append(f"\nObservation: {observation}")
        parts.append(f"Context: {context}")
        parts.append("\nRespond with JSON {\"action\": \"...\", \"reason\": \"...\"}")
        
        return "\n".join(parts)
    
    async def execute_next_task(self) -> Optional[ActionResult]:
        task = self.task_queue.get_next_task()
        if not task:
            return None
        
        logger.info(f"Executing task {task.task_id}: {task.task_type}")
        
        try:
            result = await self._execute_task(task)
            self.task_queue.complete_task(task.task_id, result.success)
            
            observation = {"task_completed": task.task_id}
            action = {"task_executed": task.model_dump()}
            self.short_term_memory.add(
                tick=self.current_world_state.tick if self.current_world_state else 0,
                observation=observation,
                action=action,
                result=result.model_dump()
            )
            
            return result
        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            self.task_queue.complete_task(task.task_id, False)
            return ActionResult(success=False, message=str(e))
    
    async def _execute_task(self, task: Task) -> ActionResult:
        if task.target_zone != self.state.position and self.fsm.is_state(AgentFSMState.IDLE):
            self.fsm.transition("start_movement")
            self.state.position = task.target_zone
            self.fsm.transition("arrive_at_scene")
        
        for rt, amount in task.resource_requirements.items():
            if not self.resources.consume(rt, amount):
                await self._request_resource(rt, amount)
        
        return ActionResult(
            success=True,
            effect={"task_completed": task.task_id},
            message=f"Completed {task.task_type}"
        )
    
    async def _request_resource(self, resource_type: ResourceType, amount: int):
        payload = {
            "resource_type": resource_type.value,
            "amount": amount,
            "urgency": 0.8
        }
        await self._publish_message(AgentRole.EOC, MessageType.RESOURCE_REQUEST, payload)
    
    async def _should_make_decision(self) -> bool:
        if not self.current_world_state:
            return False
        tick_diff = self.current_world_state.tick - self.last_decision_tick
        return tick_diff >= self.config.decision_interval
    
    async def _on_tick(self):
        if self.current_world_state:
            if (self.current_world_state.tick - self.last_heartbeat_tick) >= self.config.heartbeat_interval:
                await self._publish_heartbeat()
                self.last_heartbeat_tick = self.current_world_state.tick
        
        if not self.fsm.is_active():
            return
        
        await self.execute_next_task()
        
        if await self._should_make_decision():
            observation = {
                "world_state": self.current_world_state.model_dump() if self.current_world_state else None,
                "agent_state": self.state.model_dump(),
                "fsm_state": self.fsm.get_state().value,
                "pending_tasks": len(self.task_queue.get_pending_tasks())
            }
            context = {
                "tick": self.current_world_state.tick if self.current_world_state else 0,
                "role": self.role.value
            }
            
            decision = await self.decide(observation, context)
            self.last_decision_tick = self.current_world_state.tick if self.current_world_state else 0
            
            logger.info(f"{self.role.value} decision: {decision}")
            
            await self._process_decision(decision, observation, context)
    
    async def _process_decision(self, decision: Dict, observation: Dict, context: Dict):
        action = decision.get("action")
        
        if action == "create_task":
            task_data = decision.get("task", {})
            self.task_queue.add_task(
                task_type=TaskType(task_data.get("task_type", TaskType.PATROL)),
                target_zone=task_data.get("target_zone", self.state.position),
                priority=TaskPriority(task_data.get("priority", TaskPriority.MEDIUM)),
                description=task_data.get("description", "")
            )
        elif action == "move":
            target = decision.get("target_zone")
            if target:
                self.fsm.transition("start_movement")
                self.state.position = target
                self.fsm.transition("arrive_at_scene")
        elif action == "retreat":
            self.fsm.transition("retreat")
        elif action == "request_resources":
            resources = decision.get("resources", {})
            for rt, amount in resources.items():
                await self._request_resource(ResourceType(rt), amount)
        elif action == "wait":
            pass
    
    async def run(self):
        self.running = True
        logger.info(f"{self.role.value} agent starting...")
        
        await self._load_state()
        
        subscribe_task = asyncio.create_task(self._subscribe_to_messages())
        
        try:
            while self.running:
                try:
                    msg_data = await asyncio.wait_for(self.message_queue.get(), timeout=0.1)
                    await self._process_message(msg_data)
                    await self._on_tick()
                except asyncio.TimeoutError:
                    await self._on_tick()
        finally:
            subscribe_task.cancel()
            await self._save_state()
            logger.info(f"{self.role.value} agent stopped")
    
    async def stop(self):
        self.running = False
