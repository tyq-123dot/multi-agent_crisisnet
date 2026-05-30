import asyncio
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from loguru import logger
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole,
    AgentMessage,
    AgentState,
    LLMClient,
    WorldState,
    EnvironmentUpdate,
    ResourceType
)


class BaseAgent:
    def __init__(
        self,
        role: AgentRole,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        decision_interval_ticks: int = 5
    ):
        self.role = role
        self.redis = redis_client
        self.llm = llm_client
        self.decision_interval_ticks = decision_interval_ticks
        self.last_decision_tick = 0
        self.running = False
        
        self.state = AgentState(
            role=role,
            position="zone_01"
        )
        self.current_world_state: Optional[WorldState] = None
        self.message_queue: asyncio.Queue = asyncio.Queue()
    
    async def _save_state(self):
        state_data = self.state.model_dump()
        await self.redis.hset(f"agent:{self.role.value}:state", mapping=state_data)
    
    async def _load_state(self):
        state_data = await self.redis.hgetall(f"agent:{self.role.value}:state")
        if state_data:
            self.state = AgentState(**{k.decode(): v for k, v in state_data.items()})
    
    async def _publish_message(self, recipient: AgentRole | str, payload: Dict[str, Any], correlation_id: Optional[str] = None):
        msg = AgentMessage(
            msg_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            sender=self.role,
            recipient=recipient,
            payload=payload,
            correlation_id=correlation_id
        )
        
        channel = f"messages:{recipient}" if recipient != "broadcast" else "messages:broadcast"
        await self.redis.publish(channel, json.dumps(msg.model_dump()))
        logger.debug(f"{self.role.value} published message to {recipient}")
    
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
        msg = AgentMessage(**msg_data)
        
        if msg.recipient == "broadcast" or msg.recipient == self.role:
            if "world_state" in msg.payload:
                self.current_world_state = WorldState(**msg.payload["world_state"])
            
            await self._on_message_received(msg)
    
    async def _on_message_received(self, msg: AgentMessage):
        pass
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        return {"action": "wait", "reason": "Base agent default action"}
    
    async def _should_make_decision(self) -> bool:
        if not self.current_world_state:
            return False
        tick_diff = self.current_world_state.tick - self.last_decision_tick
        return tick_diff >= self.decision_interval_ticks
    
    async def _on_tick(self):
        if await self._should_make_decision():
            observation = {
                "world_state": self.current_world_state.model_dump() if self.current_world_state else None,
                "agent_state": self.state.model_dump()
            }
            context = {
                "tick": self.current_world_state.tick if self.current_world_state else 0,
                "role": self.role.value
            }
            
            decision = await self.decide(observation, context)
            self.last_decision_tick = self.current_world_state.tick if self.current_world_state else 0
            
            logger.info(f"{self.role.value} made decision: {decision}")
            
            await self._execute_decision(decision)
    
    async def _execute_decision(self, decision: Dict[str, Any]):
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
