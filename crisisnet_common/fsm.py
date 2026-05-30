from typing import Dict, List, Callable, Optional
from loguru import logger
from crisisnet_common.enhanced_models import AgentFSMState


class StateTransition:
    def __init__(
        self,
        from_state: AgentFSMState,
        to_state: AgentFSMState,
        trigger: str,
        condition: Optional[Callable] = None,
        action: Optional[Callable] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.trigger = trigger
        self.condition = condition
        self.action = action


class AgentFSM:
    def __init__(self, initial_state: AgentFSMState = AgentFSMState.IDLE):
        self.current_state = initial_state
        self.previous_state: Optional[AgentFSMState] = None
        self.transitions: Dict[str, List[StateTransition]] = {}
        self.state_entry_actions: Dict[AgentFSMState, List[Callable]] = {}
        self.state_exit_actions: Dict[AgentFSMState, List[Callable]] = {}
        self.state_invalid_actions: Dict[AgentFSMState, List[str]] = {}
        
        self._setup_default_transitions()
        self._setup_default_validations()
    
    def _setup_default_transitions(self):
        default_transitions = [
            StateTransition(AgentFSMState.IDLE, AgentFSMState.EN_ROUTE, "start_movement"),
            StateTransition(AgentFSMState.EN_ROUTE, AgentFSMState.ON_SCENE, "arrive_at_scene"),
            StateTransition(AgentFSMState.ON_SCENE, AgentFSMState.IDLE, "task_complete"),
            StateTransition(AgentFSMState.ON_SCENE, AgentFSMState.RETREATING, "retreat"),
            StateTransition(AgentFSMState.RETREATING, AgentFSMState.IDLE, "retreat_complete"),
            StateTransition(AgentFSMState.EN_ROUTE, AgentFSMState.RETREATING, "retreat"),
            StateTransition(AgentFSMState.IDLE, AgentFSMState.OUT_OF_SERVICE, "breakdown"),
            StateTransition(AgentFSMState.ON_SCENE, AgentFSMState.OUT_OF_SERVICE, "breakdown"),
            StateTransition(AgentFSMState.OUT_OF_SERVICE, AgentFSMState.IDLE, "repaired"),
            StateTransition(AgentFSMState.EN_ROUTE, AgentFSMState.SAFE_MODE, "enter_safe_mode"),
            StateTransition(AgentFSMState.ON_SCENE, AgentFSMState.SAFE_MODE, "enter_safe_mode"),
            StateTransition(AgentFSMState.IDLE, AgentFSMState.SAFE_MODE, "enter_safe_mode"),
            StateTransition(AgentFSMState.SAFE_MODE, AgentFSMState.IDLE, "exit_safe_mode"),
        ]
        
        for t in default_transitions:
            self.add_transition(t)
    
    def _setup_default_validations(self):
        self.state_invalid_actions = {
            AgentFSMState.OUT_OF_SERVICE: ["start_movement", "task_complete", "retreat"],
            AgentFSMState.SAFE_MODE: ["start_movement", "retreat"],
        }
    
    def add_transition(self, transition: StateTransition):
        if transition.trigger not in self.transitions:
            self.transitions[transition.trigger] = []
        self.transitions[transition.trigger].append(transition)
    
    def add_entry_action(self, state: AgentFSMState, action: Callable):
        if state not in self.state_entry_actions:
            self.state_entry_actions[state] = []
        self.state_entry_actions[state].append(action)
    
    def add_exit_action(self, state: AgentFSMState, action: Callable):
        if state not in self.state_exit_actions:
            self.state_exit_actions[state] = []
        self.state_exit_actions[state].append(action)
    
    def can_transition(self, trigger: str, **kwargs) -> bool:
        if trigger not in self.transitions:
            return False
        
        for transition in self.transitions[trigger]:
            if transition.from_state == self.current_state:
                if transition.condition is None or transition.condition(**kwargs):
                    return True
        
        return False
    
    def transition(self, trigger: str, **kwargs) -> bool:
        if trigger in self.state_invalid_actions.get(self.current_state, []):
            logger.warning(f"Cannot perform {trigger} in state {self.current_state}")
            return False
        
        if trigger not in self.transitions:
            logger.warning(f"No transition defined for trigger {trigger}")
            return False
        
        for transition in self.transitions[trigger]:
            if transition.from_state == self.current_state:
                if transition.condition is None or transition.condition(**kwargs):
                    self._execute_transition(transition, **kwargs)
                    return True
        
        logger.warning(f"No valid transition from {self.current_state} on {trigger}")
        return False
    
    def _execute_transition(self, transition: StateTransition, **kwargs):
        old_state = self.current_state
        
        if old_state in self.state_exit_actions:
            for action in self.state_exit_actions[old_state]:
                try:
                    action(old_state, transition.to_state, **kwargs)
                except Exception as e:
                    logger.error(f"Error in exit action: {e}")
        
        self.previous_state = old_state
        self.current_state = transition.to_state
        
        if transition.action:
            try:
                transition.action(old_state, transition.to_state, **kwargs)
            except Exception as e:
                logger.error(f"Error in transition action: {e}")
        
        if transition.to_state in self.state_entry_actions:
            for action in self.state_entry_actions[transition.to_state]:
                try:
                    action(old_state, transition.to_state, **kwargs)
                except Exception as e:
                    logger.error(f"Error in entry action: {e}")
        
        logger.info(f"State transition: {old_state} -> {transition.to_state} (trigger: {transition.trigger})")
    
    def get_state(self) -> AgentFSMState:
        return self.current_state
    
    def is_state(self, state: AgentFSMState) -> bool:
        return self.current_state == state
    
    def can_accept_tasks(self) -> bool:
        return self.current_state in [
            AgentFSMState.IDLE,
            AgentFSMState.ON_SCENE
        ]
    
    def is_active(self) -> bool:
        return self.current_state not in [
            AgentFSMState.OUT_OF_SERVICE,
            AgentFSMState.SAFE_MODE
        ]
    
    def force_state(self, state: AgentFSMState):
        self.previous_state = self.current_state
        self.current_state = state
        logger.warning(f"Forcefully set state to {state}")
