import json
from typing import Dict, Any, Optional
from loguru import logger
from pydantic import BaseModel, Field
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole,
    AgentMessage,
    EOCDirective,
    LLMClient,
    CaseDatabase
)
from agents.base import BaseAgent


class EOCDecision(BaseModel):
    priority_zones: Dict[str, float] = Field(default_factory=dict)
    arbitration: Dict[str, Any] = Field(default_factory=dict)
    macro_instruction: str = ""
    reasoning: str = ""


class EOCAgent(BaseAgent):
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        case_database: Optional[CaseDatabase] = None,
        decision_interval_ticks: int = 5
    ):
        super().__init__(AgentRole.EOC, redis_client, llm_client, decision_interval_ticks)
        self.agent_reports: Dict[AgentRole, Dict] = {}
        self.conflicts: list = []
        self.case_database = case_database
        self.help_request_review_queue: list = []
    
    async def _on_message_received(self, msg: AgentMessage):
        if msg.sender != self.role:
            self.agent_reports[msg.sender] = {
                "tick": self.current_world_state.tick if self.current_world_state else 0,
                "payload": msg.payload
            }
            
            if "conflict" in msg.payload:
                self.conflicts.append(msg.payload["conflict"])
            
            # 收集待审核的求助请求
            if "review_queue" in msg.payload:
                self.help_request_review_queue = msg.payload["review_queue"]
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = await self._build_decision_prompt(observation, context)
        
        example = {
            "priority_zones": {"zone_05": 0.9, "zone_06": 0.7, "zone_04": 0.5},
            "arbitration": {},
            "macro_instruction": "优先救援 zone_05 的被困人员",
            "reasoning": "zone_05 灾害强度最高，需要优先处理"
        }
        
        try:
            decision = await self.llm.call(
                prompt,
                response_schema=EOCDecision,
                schema_example=example
            )
            
            return decision.model_dump()
        except Exception as e:
            logger.error(f"EOC decision failed: {e}")
            return {
                "priority_zones": {},
                "arbitration": {},
                "macro_instruction": "继续执行当前任务",
                "reasoning": "LLM 调用失败，使用默认指令"
            }
    
    async def _build_decision_prompt(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        world_state = observation.get("world_state", {})
        agent_reports = self.agent_reports
        conflicts = self.conflicts
        
        # 检索历史案例
        few_shot_prompt = ""
        if self.case_database:
            query = f"当前灾害状态: {json.dumps(world_state, ensure_ascii=False)}"
            cases = await self.case_database.retrieve_similar_cases(
                query=query,
                disaster_type=None,
                top_k=2
            )
            if cases:
                few_shot_prompt = self.case_database.build_few_shot_prompt(cases)
        
        prompt = f"""
你是 CrisisNet 应急指挥中心 (EOC) 的 AI 指挥官。你的职责是协调各个应急响应团队，分配资源，并解决冲突。

当前环境状态 (Tick {context.get('tick', 0)}):
{json.dumps(world_state, ensure_ascii=False, indent=2)}

各团队报告:
{json.dumps({k.value: v for k, v in agent_reports.items()}, ensure_ascii=False, indent=2)}

待解决冲突:
{json.dumps(conflicts, ensure_ascii=False, indent=2)}

待审核的求助请求:
{json.dumps(self.help_request_review_queue, ensure_ascii=False, indent=2)}
{few_shot_prompt}

请分析当前情况，输出以下 JSON 格式的决策：
- priority_zones: 区域优先级字典，key 是区域 ID，value 是 0-1 的优先级
- arbitration: 冲突仲裁结果
- macro_instruction: 宏观指令
- reasoning: 决策理由

请用中文回答。
"""
        return prompt
    
    async def _execute_decision(self, decision: Dict[str, Any]):
        directive = EOCDirective(
            priority_zones=decision.get("priority_zones", {}),
            arbitration=decision.get("arbitration"),
            macro_instruction=decision.get("macro_instruction", "")
        )
        
        await self._publish_message("broadcast", {
            "type": "eoc_directive",
            "directive": directive.model_dump(),
            "reasoning": decision.get("reasoning", ""),
            "help_request_review_queue": self.help_request_review_queue
        })
        
        if "conflicts" in decision.get("arbitration", {}):
            self.conflicts = []
        
        logger.info(f"EOC issued directive: {directive.macro_instruction}")
