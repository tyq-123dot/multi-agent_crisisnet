import json
from typing import Dict, Any, Optional
from loguru import logger
from pydantic import BaseModel, Field
import redis.asyncio as redis
from crisisnet_common import (
    AgentRole,
    LLMClient,
    SocialMediaProcessor,
    CaseDatabase
)
from agents.base import BaseAgent


class PublicInfoDecision(BaseModel):
    action: str = Field(description="announce, relay_help, monitor, wait")
    announcement: str = ""
    help_requests: list = Field(default_factory=list)
    reasoning: str = ""


class PublicInfoAgent(BaseAgent):
    def __init__(
        self,
        redis_client: redis.Redis,
        llm_client: LLMClient,
        case_database: Optional[CaseDatabase] = None,
        decision_interval_ticks: int = 4
    ):
        super().__init__(AgentRole.PUBLIC_INFO, redis_client, llm_client, decision_interval_ticks)
        self.social_processor = SocialMediaProcessor(llm_client)
        self.case_database = case_database
        self.social_feed: list = []
    
    async def _on_message_received(self, msg):
        if "new_events" in msg.payload:
            self.social_feed.extend(msg.payload["new_events"])
            
            # 处理社交媒体帖子
            social_posts = [
                event for event in msg.payload["new_events"]
                if event.get("type") == "social_post"
            ]
            if social_posts:
                await self.social_processor.process_posts(social_posts)
    
    async def decide(self, observation: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        prompt = await self._build_decision_prompt(observation, context)
        
        example = {
            "action": "announce",
            "announcement": "请远离 zone_05，该区域正在进行救援工作",
            "help_requests": [],
            "reasoning": "需要发布避险公告"
        }
        
        try:
            decision = await self.llm.call(
                prompt,
                response_schema=PublicInfoDecision,
                schema_example=example
            )
            return decision.model_dump()
        except Exception as e:
            logger.error(f"PublicInfo decision failed: {e}")
            return {
                "action": "wait",
                "announcement": "",
                "help_requests": [],
                "reasoning": "LLM 调用失败"
            }
    
    async def _build_decision_prompt(self, observation: Dict[str, Any], context: Dict[str, Any]) -> str:
        world_state = observation.get("world_state", {})
        social_feed = self.social_feed[-10:]
        
        # 获取待审核的求助请求
        review_queue = self.social_processor.get_review_queue()
        review_queue_summary = []
        for req in review_queue[:5]:
            verif = req.verification
            review_queue_summary.append({
                "request_id": req.request_id,
                "location": req.location,
                "content": req.content_summary,
                "post_count": req.post_count,
                "heat_score": req.heat_score,
                "credibility_score": verif.credibility_score if verif else 0.5,
                "is_credible": verif.is_credible if verif else False
            })
        
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
你是 CrisisNet 的公共信息智能体。你的职责是监控社交媒体、发布避险公告、转发求救信息。

当前环境状态 (Tick {context.get('tick', 0)}):
{json.dumps(world_state, ensure_ascii=False, indent=2)}

最近的社交媒体/事件:
{json.dumps(social_feed, ensure_ascii=False, indent=2)}

待审核的求助请求:
{json.dumps(review_queue_summary, ensure_ascii=False, indent=2)}
{few_shot_prompt}

请决定下一步行动，输出 JSON 格式:
- action: 行动类型 (announce, relay_help, monitor, wait)
- announcement: 公告内容 (如果是 announce)
- help_requests: 求救信息列表 (如果是 relay_help)
- reasoning: 决策理由

注意: 求助信息需要经过人工审核后才能转发到 EOC。

请用中文回答。
"""
        return prompt
    
    async def _execute_decision(self, decision: Dict[str, Any]):
        action = decision.get("action")
        
        if action == "announce" and decision.get("announcement"):
            logger.info(f"Public announcement: {decision['announcement']}")
            await self._publish_message("broadcast", {
                "type": "public_announcement",
                "content": decision["announcement"]
            })
        
        if action == "relay_help" and decision.get("help_requests"):
            # 只转发已批准的请求
            approved_requests = self.social_processor.get_approved_requests()
            for help_req in approved_requests:
                await self._publish_message("eoc", {
                    "type": "help_request",
                    "request": {
                        "request_id": help_req.request_id,
                        "location": help_req.location,
                        "content": help_req.content_summary,
                        "post_count": help_req.post_count,
                        "heat_score": help_req.heat_score
                    }
                })
        
        # 发送待审核队列状态
        review_queue = self.social_processor.get_review_queue()
        await self._publish_message("eoc", {
            "type": "agent_report",
            "action": action,
            "reasoning": decision.get("reasoning", ""),
            "review_queue": [
                {
                    "request_id": r.request_id,
                    "location": r.location,
                    "content": r.content_summary,
                    "post_count": r.post_count,
                    "heat_score": r.heat_score,
                    "verification": r.verification.model_dump() if r.verification else None
                }
                for r in review_queue
            ]
        })
