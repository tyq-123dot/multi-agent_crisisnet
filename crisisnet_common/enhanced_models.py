from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field
from crisisnet_common.models import AgentRole, ResourceType


class TaskPriority(int, Enum):
    CRITICAL = 0
    URGENT = 1
    HIGH = 2
    MEDIUM = 3
    LOW = 4


class TaskStatus(str, Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class TaskType(str, Enum):
    RESCUE = "rescue"
    FIREFIGHTING = "firefighting"
    MEDICAL_TREATMENT = "medical_treatment"
    RESOURCE_TRANSPORT = "resource_transport"
    PATROL = "patrol"
    RECONNAISSANCE = "reconnaissance"
    RETREAT = "retreat"
    REPAIR = "repair"
    REFUEL = "refuel"


class Task(BaseModel):
    task_id: str
    task_type: TaskType
    target_zone: str
    priority: TaskPriority
    deadline: Optional[datetime] = None
    description: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[AgentRole] = None
    progress: float = 0.0
    dependencies: List[str] = Field(default_factory=list)
    resource_requirements: Dict[ResourceType, int] = Field(default_factory=dict)


class AgentFSMState(str, Enum):
    IDLE = "idle"
    EN_ROUTE = "en_route"
    ON_SCENE = "on_scene"
    RETREATING = "retreating"
    OUT_OF_SERVICE = "out_of_service"
    SAFE_MODE = "safe_mode"


class MessageType(str, Enum):
    TASK_ANNOUNCEMENT = "task_announcement"
    BID_RESPONSE = "bid_response"
    COMMIT = "commit"
    STATUS_UPDATE = "status_update"
    CANCEL_TASK = "cancel_task"
    ACK = "ack"
    RESOURCE_REQUEST = "resource_request"
    RESOURCE_OFFER = "resource_offer"
    HEARTBEAT = "heartbeat"
    WORLD_STATE = "world_state"
    REPUTATION_UPDATE = "reputation_update"


class EnhancedAgentMessage(BaseModel):
    msg_id: str
    timestamp: datetime
    sender: AgentRole
    recipient: AgentRole | Literal["broadcast", "eoc"]
    msg_type: MessageType
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None


class MemoryEntry(BaseModel):
    tick: int
    observation: Dict[str, Any]
    action: Dict[str, Any]
    result: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class KeyEvent(BaseModel):
    event_id: str
    event_type: str
    location: str
    details: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    importance: float = 1.0
    archived: bool = False


class ActionResult(BaseModel):
    success: bool
    effect: Dict[str, Any] = Field(default_factory=dict)
    message: str = ""
    details: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    decision_interval: int = 5
    max_speed: float = 5.0
    water_capacity: int = 1000
    initial_location: str = "zone_01"
    llm_model: str = "deepseek-chat"
    max_resource_capacity: Dict[ResourceType, int] = Field(default_factory=dict)
    safe_mode_threshold: int = 3
    heartbeat_interval: int = 1
