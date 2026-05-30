import json
import hashlib
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger
from pydantic import BaseModel, Field
from crisisnet_common import (
    LLMClient,
    SocialMediaPost,
    HelpRequestVerification,
    AggregatedHelpRequest
)


class DeduplicationKey(BaseModel):
    location: str
    content_hash: str


class SocialMediaProcessor:
    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client
        self.posts: List[SocialMediaPost] = []
        self.aggregated_requests: Dict[str, AggregatedHelpRequest] = {}
        self.review_queue: List[AggregatedHelpRequest] = []
        
    async def process_posts(self, new_posts: List[Dict[str, Any]]) -> List[AggregatedHelpRequest]:
        """处理新的社交媒体帖子"""
        processed_requests = []
        
        for post_data in new_posts:
            post = self._parse_post(post_data)
            self.posts.append(post)
            
            if self._is_help_request(post):
                aggregated = await self._aggregate_request(post)
                if aggregated:
                    processed_requests.append(aggregated)
        
        return processed_requests
    
    def _parse_post(self, post_data: Dict[str, Any]) -> SocialMediaPost:
        """解析社交媒体帖子数据"""
        return SocialMediaPost(
            post_id=post_data.get("post_id", f"post_{len(self.posts)}"),
            content=post_data.get("content", ""),
            author=post_data.get("author", "anonymous"),
            timestamp=post_data.get("timestamp", datetime.utcnow()),
            location=post_data.get("location"),
            has_image=post_data.get("has_image", False),
            image_urls=post_data.get("image_urls", []),
            author_history_posts=post_data.get("author_history_posts", 0),
            author_verified=post_data.get("author_verified", False),
            likes=post_data.get("likes", 0),
            shares=post_data.get("shares", 0)
        )
    
    def _is_help_request(self, post: SocialMediaPost) -> bool:
        """判断是否是求助信息"""
        help_keywords = ["求助", "救命", "被困", "需要帮助", "求救", "救", "紧急", "危", "受伤"]
        return any(keyword in post.content for keyword in help_keywords)
    
    async def _aggregate_request(self, post: SocialMediaPost) -> Optional[AggregatedHelpRequest]:
        """聚合相似的求助信息"""
        location = post.location or "unknown"
        content_hash = self._compute_content_hash(post.content)
        
        # 查找相似的请求
        similar_request = self._find_similar_request(location, post.content)
        
        if similar_request:
            # 合并到现有请求
            similar_request.original_posts.append(post)
            similar_request.post_count += 1
            similar_request.heat_score = self._calculate_heat_score(similar_request)
            logger.info(f"Aggregated help request at {location}, now {similar_request.post_count} posts")
            return similar_request
        else:
            # 创建新的聚合请求
            request_id = f"req_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{len(self.aggregated_requests)}"
            aggregated = AggregatedHelpRequest(
                request_id=request_id,
                location=location,
                content_summary=post.content[:200],
                original_posts=[post],
                post_count=1,
                heat_score=self._calculate_heat_score_for_single(post),
                status="needs_review"
            )
            
            # 进行可信度验证
            aggregated.verification = await self._verify_credibility(aggregated)
            
            self.aggregated_requests[request_id] = aggregated
            self.review_queue.append(aggregated)
            logger.info(f"New help request created: {request_id} at {location}")
            return aggregated
    
    def _compute_content_hash(self, content: str) -> str:
        """计算内容哈希用于去重"""
        cleaned_content = content.lower().strip()
        return hashlib.md5(cleaned_content.encode()).hexdigest()[:16]
    
    def _find_similar_request(self, location: str, content: str) -> Optional[AggregatedHelpRequest]:
        """查找相似的请求"""
        time_threshold = timedelta(minutes=30)
        now = datetime.utcnow()
        
        for request in self.aggregated_requests.values():
            if request.status not in ["approved", "rejected"]:
                if request.location == location:
                    if now - request.created_at < time_threshold:
                        if self._content_similarity(content, request.content_summary) > 0.5:
                            return request
        return None
    
    def _content_similarity(self, content1: str, content2: str) -> float:
        """简单的内容相似度计算"""
        words1 = set(content1.lower().split())
        words2 = set(content2.lower().split())
        if not words1 or not words2:
            return 0.0
        intersection = words1 & words2
        union = words1 | words2
        return len(intersection) / len(union)
    
    def _calculate_heat_score(self, request: AggregatedHelpRequest) -> float:
        """计算热度分数"""
        base_score = request.post_count * 10
        total_likes = sum(p.likes for p in request.original_posts)
        total_shares = sum(p.shares for p in request.original_posts)
        return base_score + total_likes * 2 + total_shares * 3
    
    def _calculate_heat_score_for_single(self, post: SocialMediaPost) -> float:
        """计算单条帖子的热度分数"""
        return 10 + post.likes * 2 + post.shares * 3
    
    async def _verify_credibility(self, request: AggregatedHelpRequest) -> HelpRequestVerification:
        """使用 LLM 验证可信度"""
        prompt = self._build_verification_prompt(request)
        
        class VerificationResult(BaseModel):
            is_credible: bool
            credibility_score: float = Field(ge=0.0, le=1.0)
            reasoning: str
            risk_factors: List[str]
            supporting_factors: List[str]
        
        example = VerificationResult(
            is_credible=True,
            credibility_score=0.8,
            reasoning="有图片佐证，多名用户在相同地点报告类似情况",
            risk_factors=["发布者历史较少"],
            supporting_factors=["有图片", "多个独立报告", "位置信息明确"]
        )
        
        try:
            result = await self.llm_client.call(
                prompt,
                response_schema=VerificationResult,
                schema_example=example.model_dump()
            )
            
            return HelpRequestVerification(
                is_credible=result.is_credible,
                credibility_score=result.credibility_score,
                reasoning=result.reasoning,
                risk_factors=result.risk_factors,
                supporting_factors=result.supporting_factors
            )
        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return HelpRequestVerification(
                is_credible=False,
                credibility_score=0.5,
                reasoning="自动验证失败，需要人工审核",
                risk_factors=["系统验证失败"],
                supporting_factors=[]
            )
    
    def _build_verification_prompt(self, request: AggregatedHelpRequest) -> str:
        """构建验证提示词"""
        posts_summary = "\n".join([
            f"- {p.author}: {p.content[:100]} (图片: {'有' if p.has_image else '无'}, "
            f"认证: {'是' if p.author_verified else '否'})"
            for p in request.original_posts[:5]
        ])
        
        prompt = f"""
请评估以下求助信息的可信度。

位置: {request.location}
求助内容摘要: {request.content_summary}
相关帖子数量: {request.post_count}

相关帖子详情:
{posts_summary}

请从以下方面评估:
1. 是否有图片佐证
2. 发帖人历史可信度
3. 是否有多个独立报告
4. 位置信息是否明确
5. 内容逻辑是否合理

请输出 JSON 格式:
- is_credible: 是否可信 (true/false)
- credibility_score: 可信度分数 (0.0-1.0)
- reasoning: 推理过程
- risk_factors: 风险因素列表
- supporting_factors: 支持可信的因素列表

请用中文回答。
"""
        return prompt
    
    def get_review_queue(self) -> List[AggregatedHelpRequest]:
        """获取待审核队列"""
        return [req for req in self.review_queue if req.status == "needs_review"]
    
    async def review_request(
        self,
        request_id: str,
        decision: Literal["approved", "rejected"],
        reviewer_notes: Optional[str] = None
    ) -> Optional[AggregatedHelpRequest]:
        """审核求助请求"""
        request = self.aggregated_requests.get(request_id)
        if not request:
            logger.warning(f"Request {request_id} not found")
            return None
        
        request.status = decision
        request.reviewed_at = datetime.utcnow()
        request.reviewer_notes = reviewer_notes
        
        # 从审核队列移除
        self.review_queue = [req for req in self.review_queue if req.request_id != request_id]
        
        logger.info(f"Request {request_id} {decision} by reviewer")
        return request
    
    def get_approved_requests(self) -> List[AggregatedHelpRequest]:
        """获取已批准的请求"""
        return [req for req in self.aggregated_requests.values() if req.status == "approved"]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_posts": len(self.posts),
            "total_requests": len(self.aggregated_requests),
            "pending_review": len(self.get_review_queue()),
            "approved": len(self.get_approved_requests()),
            "rejected": len([r for r in self.aggregated_requests.values() if r.status == "rejected"]),
            "by_location": defaultdict(int)
        }
