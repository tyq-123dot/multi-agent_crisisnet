import heapq
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from loguru import logger
from crisisnet_common.enhanced_models import (
    Task, TaskPriority, TaskStatus, TaskType,
    AgentRole
)


class TaskQueue:
    def __init__(self, max_size: int = 100):
        self.max_size = max_size
        self.heap: List[Tuple[int, int, Task]] = []
        self.task_map: Dict[str, Task] = {}
        self.counter = 0
        self.current_task: Optional[Task] = None
    
    def add_task(
        self,
        task_type: TaskType,
        target_zone: str,
        priority: TaskPriority = TaskPriority.MEDIUM,
        deadline: Optional[datetime] = None,
        description: str = "",
        dependencies: Optional[List[str]] = None,
        resource_requirements: Optional[Dict] = None
    ) -> Task:
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            target_zone=target_zone,
            priority=priority,
            deadline=deadline,
            description=description,
            dependencies=dependencies or [],
            resource_requirements=resource_requirements or {}
        )
        
        if len(self.heap) >= self.max_size:
            logger.warning(f"Task queue full, removing lowest priority task")
            self._remove_lowest_priority()
        
        heapq.heappush(self.heap, (priority.value, self.counter, task))
        self.task_map[task_id] = task
        self.counter += 1
        
        logger.debug(f"Added task {task_id} to queue: {task_type} at {target_zone}")
        return task
    
    def get_next_task(self) -> Optional[Task]:
        while self.heap:
            priority, counter, task = heapq.heappop(self.heap)
            
            if task.task_id not in self.task_map:
                continue
            
            if task.status != TaskStatus.PENDING:
                continue
            
            if not self._are_dependencies_met(task):
                heapq.heappush(self.heap, (priority, counter, task))
                continue
            
            if self._is_deadline_reached(task):
                task.status = TaskStatus.FAILED
                logger.warning(f"Task {task.task_id} missed deadline, marked as failed")
                continue
            
            task.status = TaskStatus.IN_PROGRESS
            self.current_task = task
            return task
        
        return None
    
    def _are_dependencies_met(self, task: Task) -> bool:
        for dep_id in task.dependencies:
            dep_task = self.task_map.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _is_deadline_reached(self, task: Task) -> bool:
        if not task.deadline:
            return False
        return datetime.utcnow() > task.deadline
    
    def _remove_lowest_priority(self):
        if not self.heap:
            return
        
        max_priority = -1
        max_index = 0
        
        for i, (p, c, t) in enumerate(self.heap):
            if p > max_priority:
                max_priority = p
                max_index = i
        
        if max_index < len(self.heap):
            _, _, task = self.heap.pop(max_index)
            if task.task_id in self.task_map:
                del self.task_map[task.task_id]
                logger.warning(f"Removed lowest priority task {task.task_id}")
    
    def complete_task(self, task_id: str, success: bool = True):
        if task_id in self.task_map:
            task = self.task_map[task_id]
            task.status = TaskStatus.COMPLETED if success else TaskStatus.FAILED
            task.progress = 1.0 if success else task.progress
            
            if self.current_task and self.current_task.task_id == task_id:
                self.current_task = None
            
            logger.info(f"Task {task_id} completed with success={success}")
    
    def cancel_task(self, task_id: str):
        if task_id in self.task_map:
            task = self.task_map[task_id]
            task.status = TaskStatus.CANCELLED
            logger.info(f"Task {task_id} cancelled")
            
            if self.current_task and self.current_task.task_id == task_id:
                self.current_task = None
    
    def requeue_task(self, task_id: str, new_priority: Optional[TaskPriority] = None):
        if task_id in self.task_map:
            task = self.task_map[task_id]
            if new_priority:
                task.priority = new_priority
            task.status = TaskStatus.PENDING
            task.progress = 0.0
            
            heapq.heappush(self.heap, (task.priority.value, self.counter, task))
            self.counter += 1
            
            logger.debug(f"Requeued task {task_id} with priority {task.priority}")
    
    def get_pending_tasks(self) -> List[Task]:
        return [t for t in self.task_map.values() if t.status == TaskStatus.PENDING]
    
    def get_in_progress_tasks(self) -> List[Task]:
        result = []
        if self.current_task:
            result.append(self.current_task)
        return result
    
    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        return self.task_map.get(task_id)
    
    def update_task_progress(self, task_id: str, progress: float):
        task = self.task_map.get(task_id)
        if task:
            task.progress = max(0.0, min(1.0, progress))
    
    def preempt_task(self, new_task: Task) -> Optional[Task]:
        old_task = self.current_task
        if old_task and new_task.priority.value < old_task.priority.value:
            logger.warning(f"Preempting task {old_task.task_id} with {new_task.task_id}")
            
            old_task.status = TaskStatus.PENDING
            old_task.progress = 0.0
            heapq.heappush(self.heap, (old_task.priority.value, self.counter, old_task))
            self.counter += 1
            
            new_task.status = TaskStatus.IN_PROGRESS
            self.current_task = new_task
            return old_task
        
        return None
    
    def clear(self):
        self.heap.clear()
        self.task_map.clear()
        self.current_task = None
        logger.info("Task queue cleared")
    
    def size(self) -> int:
        return len(self.task_map)
