import asyncio
import json
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum
from loguru import logger
import redis.asyncio as redis
from crisisnet_common import AgentRole, AgentMessage


class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


class ApprovalLevel(Enum):
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class ApprovalRequest:
    def __init__(
        self,
        request_id: str,
        agent_role: str,
        decision: Dict[str, Any],
        reasoning: str,
        level: ApprovalLevel = ApprovalLevel.MEDIUM,
        timeout_seconds: int = 300,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.request_id = request_id
        self.agent_role = agent_role
        self.decision = decision
        self.reasoning = reasoning
        self.level = level
        self.timeout_seconds = timeout_seconds
        self.metadata = metadata or {}
        self.status = ApprovalStatus.PENDING
        self.created_at = datetime.now()
        self.resolved_at: Optional[datetime] = None
        self.resolved_by: Optional[str] = None
        self.reviewer_notes: Optional[str] = None
        self.modified_decision: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request_id": self.request_id,
            "agent_role": self.agent_role,
            "decision": self.decision,
            "reasoning": self.reasoning,
            "level": self.level.value,
            "timeout_seconds": self.timeout_seconds,
            "metadata": self.metadata,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "resolved_at": self.resolved_at.isoformat() if self.resolved_at else None,
            "resolved_by": self.resolved_by,
            "reviewer_notes": self.reviewer_notes,
            "modified_decision": self.modified_decision
        }


class HumanInTheLoop:
    def __init__(
        self,
        redis_client: redis.Redis,
        auto_approve_low: bool = False,
        default_timeout: int = 300
    ):
        self.redis = redis_client
        self.auto_approve_low = auto_approve_low
        self.default_timeout = default_timeout
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.approval_callbacks: Dict[str, asyncio.Future] = {}
        self.running = False

    async def request_approval(
        self,
        agent_role: AgentRole,
        decision: Dict[str, Any],
        reasoning: str,
        level: ApprovalLevel = ApprovalLevel.MEDIUM,
        metadata: Optional[Dict[str, Any]] = None
    ) -> ApprovalRequest:
        request_id = f"APR_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        request = ApprovalRequest(
            request_id=request_id,
            agent_role=agent_role.value if isinstance(agent_role, AgentRole) else agent_role,
            decision=decision,
            reasoning=reasoning,
            level=level,
            timeout_seconds=self.default_timeout,
            metadata=metadata
        )
        
        self.pending_requests[request_id] = request
        
        if level == ApprovalLevel.LOW and self.auto_approve_low:
            logger.info(f"Auto-approving low level request: {request_id}")
            await self.approve(request_id, "auto_approve")
            return request
        
        await self._publish_request(request)
        logger.info(f"Approval request created: {request_id} for {agent_role}")
        
        return request

    async def wait_for_approval(
        self,
        request_id: str,
        timeout: Optional[int] = None
    ) -> ApprovalRequest:
        request = self.pending_requests.get(request_id)
        if not request:
            raise ValueError(f"Request {request_id} not found")
        
        if request.status != ApprovalStatus.PENDING:
            return request
        
        future = asyncio.Future()
        self.approval_callbacks[request_id] = future
        
        try:
            timeout = timeout or request.timeout_seconds
            await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            request.status = ApprovalStatus.EXPIRED
            logger.warning(f"Approval request {request_id} expired")
        
        return request

    async def approve(
        self,
        request_id: str,
        approved_by: str = "human",
        notes: Optional[str] = None
    ) -> bool:
        request = self.pending_requests.get(request_id)
        if not request:
            logger.warning(f"Request {request_id} not found for approval")
            return False
        
        request.status = ApprovalStatus.APPROVED
        request.resolved_at = datetime.now()
        request.resolved_by = approved_by
        request.reviewer_notes = notes
        
        await self._publish_resolution(request)
        
        if request_id in self.approval_callbacks:
            self.approval_callbacks[request_id].set_result(True)
            del self.approval_callbacks[request_id]
        
        logger.info(f"Request {request_id} approved by {approved_by}")
        return True

    async def reject(
        self,
        request_id: str,
        rejected_by: str = "human",
        notes: Optional[str] = None
    ) -> bool:
        request = self.pending_requests.get(request_id)
        if not request:
            logger.warning(f"Request {request_id} not found for rejection")
            return False
        
        request.status = ApprovalStatus.REJECTED
        request.resolved_at = datetime.now()
        request.resolved_by = rejected_by
        request.reviewer_notes = notes
        
        await self._publish_resolution(request)
        
        if request_id in self.approval_callbacks:
            self.approval_callbacks[request_id].set_result(False)
            del self.approval_callbacks[request_id]
        
        logger.info(f"Request {request_id} rejected by {rejected_by}")
        return True

    async def modify(
        self,
        request_id: str,
        modified_decision: Dict[str, Any],
        modified_by: str = "human",
        notes: Optional[str] = None
    ) -> bool:
        request = self.pending_requests.get(request_id)
        if not request:
            logger.warning(f"Request {request_id} not found for modification")
            return False
        
        request.status = ApprovalStatus.MODIFIED
        request.resolved_at = datetime.now()
        request.resolved_by = modified_by
        request.reviewer_notes = notes
        request.modified_decision = modified_decision
        
        await self._publish_resolution(request)
        
        if request_id in self.approval_callbacks:
            self.approval_callbacks[request_id].set_result(True)
            del self.approval_callbacks[request_id]
        
        logger.info(f"Request {request_id} modified by {modified_by}")
        return True

    async def _publish_request(self, request: ApprovalRequest):
        msg = AgentMessage(
            msg_id=request.request_id,
            timestamp=datetime.now(),
            sender=AgentRole.EOC,
            recipient="broadcast",
            payload={
                "type": "approval_request",
                "request": request.to_dict()
            }
        )
        await self.redis.publish("approval_requests", json.dumps(msg.model_dump()))

    async def _publish_resolution(self, request: ApprovalRequest):
        msg = AgentMessage(
            msg_id=f"RES_{request.request_id}",
            timestamp=datetime.now(),
            sender=AgentRole.EOC,
            recipient="broadcast",
            payload={
                "type": "approval_resolution",
                "request": request.to_dict()
            }
        )
        await self.redis.publish("approval_resolutions", json.dumps(msg.model_dump()))

    def get_pending_requests(self) -> List[ApprovalRequest]:
        return [
            r for r in self.pending_requests.values() 
            if r.status == ApprovalStatus.PENDING
        ]

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        return self.pending_requests.get(request_id)

    async def start_listening(self):
        self.running = True
        logger.info("HumanInTheLoop listener started")

    async def stop_listening(self):
        self.running = False


class DirectCommand:
    def __init__(
        self,
        command_id: str,
        command: str,
        issued_by: str,
        target_agents: Optional[List[AgentRole]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ):
        self.command_id = command_id
        self.command = command
        self.issued_by = issued_by
        self.target_agents = target_agents
        self.metadata = metadata or {}
        self.created_at = datetime.now()
        self.executed: bool = False
        self.executed_at: Optional[datetime] = None


class DirectCommandManager:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client
        self.pending_commands: Dict[str, DirectCommand] = {}
        self.command_queue: asyncio.Queue = asyncio.Queue()

    async def issue_command(
        self,
        command: str,
        issued_by: str = "human",
        target_agents: Optional[List[AgentRole]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DirectCommand:
        command_id = f"CMD_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        cmd = DirectCommand(
            command_id=command_id,
            command=command,
            issued_by=issued_by,
            target_agents=target_agents,
            metadata=metadata
        )
        
        self.pending_commands[command_id] = cmd
        await self.command_queue.put(cmd)
        
        msg = AgentMessage(
            msg_id=command_id,
            timestamp=datetime.now(),
            sender=AgentRole.EOC,
            recipient="broadcast",
            payload={
                "type": "direct_command",
                "command_id": command_id,
                "command": command,
                "issued_by": issued_by,
                "target_agents": [a.value for a in target_agents] if target_agents else None,
                "metadata": metadata
            }
        )
        
        await self.redis.publish("direct_commands", json.dumps(msg.model_dump()))
        
        logger.info(f"Direct command issued: {command_id}")
        return cmd

    async def get_next_command(
        self,
        timeout: Optional[float] = None
    ) -> Optional[DirectCommand]:
        try:
            if timeout:
                return await asyncio.wait_for(self.command_queue.get(), timeout=timeout)
            return await self.command_queue.get()
        except asyncio.TimeoutError:
            return None

    def mark_executed(self, command_id: str):
        if command_id in self.pending_commands:
            cmd = self.pending_commands[command_id]
            cmd.executed = True
            cmd.executed_at = datetime.now()
            logger.info(f"Command {command_id} marked as executed")

    def get_pending_commands(self) -> List[DirectCommand]:
        return [c for c in self.pending_commands.values() if not c.executed]


def requires_approval(
    decision: Dict[str, Any],
    agent_role: AgentRole
) -> tuple[bool, ApprovalLevel]:
    action = decision.get("action", "")
    
    high_risk_actions = [
        "deploy_team", "rescue_operation", "set_priorities", 
        "resolve_conflict"
    ]
    
    if action in high_risk_actions:
        return True, ApprovalLevel.HIGH
    
    if agent_role == AgentRole.EOC:
        return True, ApprovalLevel.MEDIUM
    
    return False, ApprovalLevel.LOW
