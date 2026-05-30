import json
from typing import Dict, Any
from loguru import logger
from pydantic import BaseModel, Field
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole,
    LLMClient,
    ResourceType
)
from agents.base import BaseAgent


class LogisticsDecision(BaseModel):
    action: str = Field(description="dispatch, move_to, re_route, request_airlift, wait")
    target_zone: str = ""
    resource_type: str = ""
    quantity: int = 1
    reasoning: str = ""


class LogisticsAgent(BaseAgent):
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        decision_interval_ticks: int = 3
    ):
        super().__init__(AgentRole.LOGISTICS, redis_client, llm_client, decision_interval_ticks)
        self.state.remaining_resources = {
            ResourceType.FOOD_RATION: 200,
            ResourceType.MEDKIT: 50,
            ResourceType.COLD_TRUCK: 2
        }
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_decision_prompt(observation, context)
        
        example = {
            "action": "dispatch",
            "target_zone": "zone_05",
            "resource_type": "medkit",
            "quantity": 10,
            "reasoning": "zone_05 需要医疗物资"
        }
        
        try:
            decision = await self.llm.call(
                prompt,
                response_schema=LogisticsDecision,
                schema_example=example
            )
            return decision.model_dump()
        except Exception as e:
            logger.error(f"Logistics decision failed: {e}")
            return {
                "action": "wait",
                "target_zone": "",
                "resource_type": "",
                "quantity": 1,
                "reasoning": "LLM 调用失败，原地待命"
            }
    
    def _build_decision_prompt(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        world_state = observation.get("world_state", {})
        agent_state = observation.get("agent_state", {})
        
        prompt = f"""
你是 CrisisNet 的物流智能体。你的职责是调度物资运输、保障供应链。

当前环境状态 (Tick {context.get('tick', 0)}):
{json.dumps(world_state, ensure_ascii=False, indent=2)}

你的状态:
{json.dumps(agent_state, ensure_ascii=False, indent=2)}

请决定下一步行动，输出 JSON 格式：
- action: 行动类型 (dispatch, move_to, re_route, request_airlift, wait)
- target_zone: 目标区域
- resource_type: 资源类型 (medkit, food_ration, water_pump 等)
- quantity: 数量
- reasoning: 决策理由

请用中文回答。
"""
        return prompt
    
    async def _execute_decision(self, decision: Dict[str, Any]):
        action = decision.get("action")
        
        if action == "dispatch":
            resource_type = decision.get("resource_type")
            quantity = decision.get("quantity", 1)
            if resource_type in self.state.remaining_resources:
                available = self.state.remaining_resources[ResourceType(resource_type)]
                if available >= quantity:
                    self.state.remaining_resources[ResourceType(resource_type)] -= quantity
                    logger.info(f"Dispatched {quantity} {resource_type} to {decision.get('target_zone')}")
        
        await self._publish_message("eoc", {
            "type": "agent_report",
            "action": action,
            "position": self.state.position,
            "reasoning": decision.get("reasoning", "")
        })
