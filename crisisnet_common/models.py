from enum import Enum
from datetime import datetime
from typing import Dict, List, Optional, Literal, Any
from pydantic import BaseModel, Field


class AgentRole(str, Enum):
    EOC = "eoc"
    FIRE_RESCUE = "fire_rescue"
    MEDICAL = "medical"
    LOGISTICS = "logistics"
    PUBLIC_INFO = "public_info"


class ResourceType(str, Enum):
    HELICOPTER = "helicopter"
    MEDKIT = "medkit"
    WATER_PUMP = "water_pump"
    FOOD_RATION = "food_ration"
    COLD_TRUCK = "cold_truck"
    AMBULANCE = "ambulance"


class AgentMessage(BaseModel):
    msg_id: str
    timestamp: datetime
    sender: AgentRole
    recipient: AgentRole | Literal["broadcast", "eoc"]
    payload: Dict[str, Any]
    correlation_id: Optional[str] = None


class ZoneState(BaseModel):
    zone_id: str
    disaster_intensity: float = Field(ge=0.0, le=1.0, default=0.0)
    road_available: bool = True
    casualties: int = 0
    trapped_people: int = 0


class WorldState(BaseModel):
    tick: int
    zones: Dict[str, ZoneState]
    timestamp: datetime


class ResourcePool(BaseModel):
    resources: Dict[ResourceType, int] = Field(default_factory=dict)
    
    def has_enough(self, resource_type: ResourceType, quantity: int = 1) -> bool:
        return self.resources.get(resource_type, 0) >= quantity
    
    def consume(self, resource_type: ResourceType, quantity: int = 1) -> bool:
        if self.has_enough(resource_type, quantity):
            self.resources[resource_type] -= quantity
            return True
        return False
    
    def add(self, resource_type: ResourceType, quantity: int = 1):
        self.resources[resource_type] = self.resources.get(resource_type, 0) + quantity


class AgentState(BaseModel):
    role: AgentRole
    position: str
    remaining_resources: Dict[ResourceType, int] = Field(default_factory=dict)
    current_task: Optional[str] = None
    task_progress: float = 0.0


class EnvironmentUpdate(BaseModel):
    world_state: WorldState
    new_events: List[Dict[str, Any]] = Field(default_factory=list)


class EOCDirective(BaseModel):
    priority_zones: Dict[str, float] = Field(default_factory=dict)
    arbitration: Optional[Dict[str, Any]] = None
    macro_instruction: Optional[str] = None


class NegotiationRequest(BaseModel):
    negotiation_id: str
    requester: AgentRole
    requested_resource: ResourceType
    quantity: int
    offer: Dict[str, Any]
    round: int = 1


class NegotiationResponse(BaseModel):
    negotiation_id: str
    responder: AgentRole
    decision: Literal["accept", "reject", "counter"]
    counter_offer: Optional[Dict[str, Any]] = None


class SocialMediaPost(BaseModel):
    post_id: str
    content: str
    author: str
    timestamp: datetime
    location: Optional[str] = None
    has_image: bool = False
    image_urls: List[str] = Field(default_factory=list)
    author_history_posts: int = 0
    author_verified: bool = False
    likes: int = 0
    shares: int = 0


class HelpRequestVerification(BaseModel):
    is_credible: bool
    credibility_score: float = Field(ge=0.0, le=1.0)
    reasoning: str
    risk_factors: List[str] = Field(default_factory=list)
    supporting_factors: List[str] = Field(default_factory=list)


class AggregatedHelpRequest(BaseModel):
    request_id: str
    location: str
    content_summary: str
    original_posts: List[SocialMediaPost] = Field(default_factory=list)
    post_count: int = 0
    heat_score: float = 0.0
    verification: Optional[HelpRequestVerification] = None
    status: Literal["pending", "approved", "rejected", "needs_review"] = "needs_review"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    reviewer_notes: Optional[str] = None

