from typing import Dict
from loguru import logger
from crisisnet_common.models import AgentRole


class ReputationManager:
    def __init__(self, initial_score: int = 50, min_score: int = 0, max_score: int = 100):
        self.initial_score = initial_score
        self.min_score = min_score
        self.max_score = max_score
        self.reputation_table: Dict[AgentRole, int] = {}
        self.interaction_history: Dict[AgentRole, list] = {}
    
    def get_reputation(self, agent: AgentRole) -> int:
        return self.reputation_table.get(agent, self.initial_score)
    
    def set_reputation(self, agent: AgentRole, score: int):
        self.reputation_table[agent] = max(self.min_score, min(self.max_score, score))
        logger.debug(f"Set reputation of {agent} to {self.reputation_table[agent]}")
    
    def update_on_task_completion(self, agent: AgentRole, on_time: bool = True, success: bool = True):
        current = self.get_reputation(agent)
        
        if success and on_time:
            delta = 1
        elif success:
            delta = 0
        else:
            delta = -5
        
        self.set_reputation(agent, current + delta)
        self._record_interaction(agent, "task_completion", delta)
    
    def update_on_false_information(self, agent: AgentRole):
        current = self.get_reputation(agent)
        delta = -10
        self.set_reputation(agent, current + delta)
        self._record_interaction(agent, "false_info", delta)
    
    def update_on_refused_request(self, agent: AgentRole, was_reasonable: bool = True):
        current = self.get_reputation(agent)
        delta = -2 if was_reasonable else -1
        self.set_reputation(agent, current + delta)
        self._record_interaction(agent, "refused_request", delta)
    
    def update_on_good_collaboration(self, agent: AgentRole):
        current = self.get_reputation(agent)
        delta = 2
        self.set_reputation(agent, current + delta)
        self._record_interaction(agent, "good_collab", delta)
    
    def should_trust(self, agent: AgentRole, threshold: int = 30) -> bool:
        return self.get_reputation(agent) >= threshold
    
    def get_agents_below_threshold(self, threshold: int = 30) -> list:
        return [
            agent for agent, score in self.reputation_table.items()
            if score < threshold
        ]
    
    def _record_interaction(self, agent: AgentRole, interaction_type: str, delta: int):
        if agent not in self.interaction_history:
            self.interaction_history[agent] = []
        self.interaction_history[agent].append({
            "type": interaction_type,
            "delta": delta,
            "timestamp": __import__("datetime").datetime.utcnow().isoformat()
        })
    
    def get_all_reputations(self) -> Dict[AgentRole, int]:
        return self.reputation_table.copy()
