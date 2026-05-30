from typing import Dict, Optional
from loguru import logger
from crisisnet_common.models import ResourceType, AgentRole


class ResourceInventory:
    def __init__(self, initial_resources: Optional[Dict[ResourceType, int]] = None):
        self.resources: Dict[ResourceType, int] = initial_resources or {}
        self.max_capacity: Dict[ResourceType, int] = {}
    
    def set_max_capacity(self, resource_type: ResourceType, capacity: int):
        self.max_capacity[resource_type] = capacity
    
    def has_enough(self, resource_type: ResourceType, amount: int = 1) -> bool:
        return self.resources.get(resource_type, 0) >= amount
    
    def consume(self, resource_type: ResourceType, amount: int = 1) -> bool:
        if self.has_enough(resource_type, amount):
            self.resources[resource_type] -= amount
            logger.debug(f"Consumed {amount} {resource_type}, remaining: {self.resources.get(resource_type, 0)}")
            return True
        logger.warning(f"Not enough {resource_type}, needed {amount}, have {self.resources.get(resource_type, 0)}")
        return False
    
    def add(self, resource_type: ResourceType, amount: int = 1):
        current = self.resources.get(resource_type, 0)
        max_cap = self.max_capacity.get(resource_type, float('inf'))
        new_amount = min(current + amount, max_cap)
        self.resources[resource_type] = new_amount
        logger.debug(f"Added {amount} {resource_type}, now: {new_amount}")
    
    def get_amount(self, resource_type: ResourceType) -> int:
        return self.resources.get(resource_type, 0)
    
    def get_all(self) -> Dict[ResourceType, int]:
        return self.resources.copy()
    
    def is_empty(self, resource_type: ResourceType) -> bool:
        return self.get_amount(resource_type) <= 0
    
    def get_low_resources(self, threshold: float = 0.2) -> Dict[ResourceType, int]:
        low = {}
        for rt, amount in self.resources.items():
            max_cap = self.max_capacity.get(rt, 100)
            if amount / max_cap < threshold:
                low[rt] = amount
        return low


class ResourceSharingManager:
    def __init__(self):
        self.pending_requests: Dict[str, Dict] = {}
    
    def create_request(
        self,
        request_id: str,
        requester: AgentRole,
        resource_type: ResourceType,
        amount: int,
        urgency: float = 0.5
    ) -> Dict:
        request = {
            "request_id": request_id,
            "requester": requester,
            "resource_type": resource_type,
            "amount": amount,
            "urgency": urgency,
            "status": "pending"
        }
        self.pending_requests[request_id] = request
        return request
    
    def cancel_request(self, request_id: str):
        if request_id in self.pending_requests:
            self.pending_requests[request_id]["status"] = "cancelled"
    
    def get_priority_requests(self) -> list:
        requests = [r for r in self.pending_requests.values() if r["status"] == "pending"]
        requests.sort(key=lambda r: (-r["urgency"], -r["amount"]))
        return requests
    
    def should_respond_to_request(self, requester: AgentRole, my_reputation: int = 50) -> bool:
        return my_reputation >= 30
    
    def get_resource_priority_score(
        self,
        resource_type: ResourceType,
        requester: AgentRole,
        requester_casualties: int = 0
    ) -> float:
        base_scores = {
            ResourceType.MEDKIT: 10.0,
            ResourceType.AMBULANCE: 9.0,
            ResourceType.WATER_PUMP: 8.0,
            ResourceType.HELICOPTER: 7.0,
            ResourceType.FOOD_RATION: 5.0,
            ResourceType.COLD_TRUCK: 4.0,
        }
        
        score = base_scores.get(resource_type, 1.0)
        score += requester_casualties * 0.5
        
        if requester == AgentRole.MEDICAL:
            score *= 1.5
        
        return score
