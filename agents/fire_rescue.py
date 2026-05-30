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


class FireRescueDecision(BaseModel):
    action: str = Field(description="move_to, extinguish, rescue, request_support, wait")
    target_zone: str = ""
    reasoning: str = ""


class FireRescueAgent(BaseAgent):
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        decision_interval_ticks: int = 2
    ):
        super().__init__(AgentRole.FIRE_RESCUE, redis_client, llm_client, decision_interval_ticks)
        self.state.remaining_resources = {
            ResourceType.WATER_PUMP: 3
        }
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_decision_prompt(observation, context)
        
        example = {
            "action": "move_to",
            "target_zone": "zone_05",
            "reasoning": "zone_05 灾害强度最高，需要立即前往"
        }
        
        try:
            decision = await self.llm.call(
                prompt,
                response_schema=FireRescueDecision,
                schema_example=example
            )
            return decision.model_dump()
        except Exception as e:
            logger.error(f"FireRescue decision failed: {e}")
            return {
                "action": "wait",
                "target_zone": "",
                "reasoning": "LLM 调用失败，原地待命"
            }
    
    def _build_decision_prompt(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        world_state = observation.get("world_state", {})
        agent_state = observation.get("agent_state", {})
        
        prompt = f"""
你是 CrisisNet 的消防救援智能体。你的职责是灭火、救援被困人员。

当前环境状态 (Tick {context.get('tick', 0)}):
{json.dumps(world_state, ensure_ascii=False, indent=2)}

你的状态:
{json.dumps(agent_state, ensure_ascii=False, indent=2)}

请决定下一步行动，输出 JSON 格式：
- action: 行动类型 (move_to, extinguish, rescue, request_support, wait)
- target_zone: 目标区域 (如果需要)
- reasoning: 决策理由

请用中文回答。
"""
        return prompt
    
    async def _execute_decision(self, decision: Dict[str, Any]):
        action = decision.get("action")
        
        if action == "move_to" and decision.get("target_zone"):
            self.state.position = decision["target_zone"]
            logger.info(f"FireRescue moving to {decision['target_zone']}")
        
        await self._publish_message("eoc", {
            "type": "agent_report",
            "action": action,
            "position": self.state.position,
            "reasoning": decision.get("reasoning", "")
        })
