import uuid
from enum import Enum
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field


class NegotiationStatus(Enum):
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILED = "failed"
    ESCALATED = "escalated"  # 3 轮失败后升级
    CANCELLED = "cancelled"  # 被人类撤销


class NegotiationStep(Enum):
    REQUEST = "request"       # 1. 请求
    RESPONSE = "response"     # 2. 响应
    CONFIRM = "confirm"       # 3. 确认


class ResourceType(Enum):
    MEDICINE = "medicine"
    WATER = "water"
    FOOD = "food"
    EQUIPMENT = "equipment"


class NegotiationMessage(BaseModel):
    step: NegotiationStep
    sender: str
    receiver: str
    content: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    message_id: str = Field(default_factory=lambda: str(uuid.uuid4()))


class NegotiationProtocol:
    """预定义的协商协议模板系统"""
    
    @staticmethod
    def create_medical_supply_request(
        agent_id: str,
        resource_type: str,
        quantity: int,
        target_zone: str,
        urgency: str = "normal",
        medical_reason: str = ""
    ) -> NegotiationMessage:
        """步骤 1: 医疗物资申请"""
        return NegotiationMessage(
            step=NegotiationStep.REQUEST,
            sender=agent_id,
            receiver="warehouse_1",
            content={
                "protocol_type": "medical_supply",
                "action": "request_supply",
                "resource_type": resource_type,
                "quantity": quantity,
                "target_zone": target_zone,
                "urgency": urgency,
                "medical_reason": medical_reason
            }
        )
    
    @staticmethod
    def create_supply_response(
        warehouse_agent: str,
        original_request: NegotiationMessage,
        available: bool,
        alternative_suggestion: Optional[Dict] = None,
        delivery_eta: Optional[int] = None  # 分钟
    ) -> NegotiationMessage:
        """步骤 2: 仓库响应"""
        return NegotiationMessage(
            step=NegotiationStep.RESPONSE,
            sender=warehouse_agent,
            receiver=original_request.sender,
            content={
                "protocol_type": "medical_supply",
                "action": "respond_supply",
                "request_id": original_request.message_id,
                "available": available,
                "alternative_suggestion": alternative_suggestion,
                "delivery_eta": delivery_eta,
                "original_request": original_request.content
            }
        )
    
    @staticmethod
    def create_confirmation(
        requester_agent: str,
        response: NegotiationMessage,
        accepted: bool,
        confirmation_note: str = ""
    ) -> NegotiationMessage:
        """步骤 3: 确认响应"""
        return NegotiationMessage(
            step=NegotiationStep.CONFIRM,
            sender=requester_agent,
            receiver=response.sender,
            content={
                "protocol_type": "medical_supply",
                "action": "confirm_deal",
                "response_id": response.message_id,
                "accepted": accepted,
                "confirmation_note": confirmation_note,
                "original_response": response.content
            }
        )


class NegotiationSession(BaseModel):
    """协商会话管理"""
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    participants: List[str] = Field(default_factory=list)
    messages: List[NegotiationMessage] = Field(default_factory=list)
    status: NegotiationStatus = NegotiationStatus.INITIATED
    created_at: datetime = Field(default_factory=datetime.now)
    max_rounds: int = 3
    current_round: int = 0
    escalation_note: Optional[str] = None
    
    def add_message(self, message: NegotiationMessage) -> Tuple[bool, bool]:
        """
        添加消息并检查是否需要升级
        返回: (success, needs_escalation)
        """
        if self.status in [NegotiationStatus.SUCCESS, NegotiationStatus.FAILED, 
                          NegotiationStatus.ESCALATED, NegotiationStatus.CANCELLED]:
            return False, False
        
        self.messages.append(message)
        
        if message.step == NegotiationStep.CONFIRM:
            if message.content.get("accepted", False):
                self.status = NegotiationStatus.SUCCESS
                return True, False
            else:
                self.current_round += 1
                if self.current_round >= self.max_rounds:
                    self.status = NegotiationStatus.ESCALATED
                    return True, True
                return True, False
        
        if message.step == NegotiationStep.RESPONSE:
            if not message.content.get("available", False) and not message.content.get("alternative_suggestion"):
                self.current_round += 1
                if self.current_round >= self.max_rounds:
                    self.status = NegotiationStatus.ESCALATED
                    return True, True
        
        return True, False
    
    def cancel(self, reason: str = ""):
        """撤销协商"""
        self.status = NegotiationStatus.CANCELLED
        self.escalation_note = reason


class ActionTracker:
    """动作追踪与回滚管理"""
    
    def __init__(self):
        self.pending_actions: Dict[str, Dict] = {}  # 待执行的动作
        self.executed_actions: List[Dict] = []
        self.cancelled_actions: List[Dict] = []
        self.max_history = 100
    
    def register_pending_action(self, action_id: str, agent_role: str, 
                               action_payload: Dict, metadata: Dict = None):
        """注册即将执行的动作"""
        self.pending_actions[action_id] = {
            "action_id": action_id,
            "agent_role": agent_role,
            "action_payload": action_payload,
            "metadata": metadata or {},
            "registered_at": datetime.now(),
            "status": "pending"
        }
    
    def mark_executed(self, action_id: str, execution_data: Dict = None):
        """标记动作已执行"""
        if action_id in self.pending_actions:
            action = self.pending_actions.pop(action_id)
            action["status"] = "executed"
            action["executed_at"] = datetime.now()
            action["execution_data"] = execution_data
            self.executed_actions.append(action)
            if len(self.executed_actions) > self.max_history:
                self.executed_actions = self.executed_actions[-self.max_history:]
    
    def cancel_action(self, action_id: str, reason: str = "") -> Optional[Dict]:
        """
        取消动作（如果还没执行）
        返回被取消的动作信息
        """
        if action_id in self.pending_actions:
            action = self.pending_actions.pop(action_id)
            action["status"] = "cancelled"
            action["cancelled_at"] = datetime.now()
            action["cancellation_reason"] = reason
            self.cancelled_actions.append(action)
            return action
        return None
    
    def modify_action(self, action_id: str, new_payload: Dict, reason: str = "") -> Optional[Dict]:
        """
        修改待执行的动作
        返回修改后的动作信息
        """
        if action_id in self.pending_actions:
            action = self.pending_actions[action_id]
            action["original_payload"] = action["action_payload"].copy()
            action["action_payload"] = new_payload
            action["modified_at"] = datetime.now()
            action["modification_reason"] = reason
            return action
        return None
    
    def get_pending_actions(self) -> List[Dict]:
        """获取所有待执行动作"""
        return list(self.pending_actions.values())
