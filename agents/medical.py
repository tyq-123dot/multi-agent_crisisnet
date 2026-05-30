import json
import uuid
from typing import Dict, Any
from loguru import logger
from pydantic import BaseModel, Field
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole,
    LLMClient,
    ResourceType,
    NegotiationRequest,
    NegotiationResponse
)
from agents.base import BaseAgent


class MedicalDecision(BaseModel):
    action: str = Field(description="treat, move_to, negotiate, request_support, wait")
    target_zone: str = ""
    negotiate_with: str = ""
    requested_resource: str = ""
    reasoning: str = ""


class MedicalAgent(BaseAgent):
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        decision_interval_ticks: int = 2
    ):
        super().__init__(AgentRole.MEDICAL, redis_client, llm_client, decision_interval_ticks)
        self.state.remaining_resources = {
            ResourceType.MEDKIT: 20,
            ResourceType.AMBULANCE: 2
        }
        self.pending_negotiations: Dict[str, Dict] = {}
    
    async def _on_message_received(self, msg):
        if "negotiation_request" in msg.payload:
            await self._handle_negotiation_request(msg)
        elif "negotiation_response" in msg.payload:
            await self._handle_negotiation_response(msg)
    
    async def _handle_negotiation_request(self, msg):
        req = NegotiationRequest(**msg.payload["negotiation_request"])
        logger.info(f"Medical received negotiation request from {req.requester}")
        
        prompt = f"""
你收到了来自 {req.requester.value} 的协商请求：
- 请求资源: {req.requested_resource.value} x{req.quantity}
- 对方提供的交换条件: {req.offer}
- 你的资源: {self.state.remaining_resources}

请决定：accept, reject, 还是 counter（提出反条件）
"""
        try:
            class NegotiationResp(BaseModel):
                decision: str
                counter_offer: Dict[str, Any] = Field(default_factory=dict)
            
            resp = await self.llm.call(prompt, response_schema=NegotiationResp)
            
            response = NegotiationResponse(
                negotiation_id=req.negotiation_id,
                responder=self.role,
                decision=resp.decision,
                counter_offer=resp.counter_offer
            )
            
            await self._publish_message(
                req.requester,
                {"negotiation_response": response.model_dump()},
                req.negotiation_id
            )
        except Exception as e:
            logger.error(f"Negotiation handling failed: {e}")
    
    async def _handle_negotiation_response(self, msg):
        resp = NegotiationResponse(**msg.payload["negotiation_response"])
        if resp.decision == "accept":
            logger.info(f"Negotiation {resp.negotiation_id} accepted!")
            if resp.negotiation_id in self.pending_negotiations:
                del self.pending_negotiations[resp.negotiation_id]
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_decision_prompt(observation, context)
        
        example = {
            "action": "treat",
            "target_zone": "zone_05",
            "negotiate_with": "",
            "requested_resource": "",
            "reasoning": "zone_05 有大量伤员需要治疗"
        }
        
        try:
            decision = await self.llm.call(
                prompt,
                response_schema=MedicalDecision,
                schema_example=example
            )
            return decision.model_dump()
        except Exception as e:
            logger.error(f"Medical decision failed: {e}")
            return {
                "action": "wait",
                "target_zone": "",
                "negotiate_with": "",
                "requested_resource": "",
                "reasoning": "LLM 调用失败，原地待命"
            }
    
    def _build_decision_prompt(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        world_state = observation.get("world_state", {})
        agent_state = observation.get("agent_state", {})
        
        prompt = f"""
你是 CrisisNet 的医疗救援智能体。你的职责是治疗伤员、协调医疗资源。

当前环境状态 (Tick {context.get('tick', 0)}):
{json.dumps(world_state, ensure_ascii=False, indent=2)}

你的状态:
{json.dumps(agent_state, ensure_ascii=False, indent=2)}

请决定下一步行动，输出 JSON 格式：
- action: 行动类型 (treat, move_to, negotiate, request_support, wait)
- target_zone: 目标区域
- negotiate_with: 协商对象 (logistics, fire_rescue 等)
- requested_resource: 请求的资源类型
- reasoning: 决策理由

请用中文回答。
"""
        return prompt
    
    async def _execute_decision(self, decision: Dict[str, Any]):
        action = decision.get("action")
        
        if action == "move_to" and decision.get("target_zone"):
            self.state.position = decision["target_zone"]
        
        if action == "negotiate" and decision.get("negotiate_with"):
            negotiation_id = str(uuid.uuid4())
            req = NegotiationRequest(
                negotiation_id=negotiation_id,
                requester=self.role,
                requested_resource=ResourceType(decision["requested_resource"]),
                quantity=1,
                offer={"priority_treatment": "for their team members"}
            )
            self.pending_negotiations[negotiation_id] = {"request": req.model_dump()}
            
            await self._publish_message(
                AgentRole(decision["negotiate_with"]),
                {"negotiation_request": req.model_dump()},
                negotiation_id
            )
        
        await self._publish_message("eoc", {
            "type": "agent_report",
            "action": action,
            "position": self.state.position,
            "reasoning": decision.get("reasoning", "")
        })
