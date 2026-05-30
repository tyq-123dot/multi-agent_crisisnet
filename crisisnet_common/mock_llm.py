import json
import time
import random
from datetime import datetime
from typing import Dict, Any, Optional, Type, TypeVar
from loguru import logger
from pydantic import BaseModel

T = TypeVar('T', bound=BaseModel)


class MockLLMClient:
    def __init__(
        self,
        api_key: str = "mock_key",
        base_url: str = "",
        model: str = "mock-model",
        temperature: float = 0.1,
        llm_log_file: str = "logs/llm_calls.jsonl"
    ):
        self.model = model
        self.temperature = temperature
        self.llm_log_file = llm_log_file
        self.random = random.Random(42)
    
    def _log_llm_call(self, prompt: str, response: Dict[str, Any], success: bool):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "prompt": prompt[:100] + "..." if len(prompt) > 100 else prompt,
            "response": response,
            "success": success
        }
        try:
            with open(self.llm_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write LLM log: {e}")
    
    async def call(
        self,
        prompt: str,
        response_schema: Optional[Type[T]] = None,
        schema_example: Optional[Dict[str, Any]] = None
    ) -> T | Dict[str, Any]:
        await __import__('asyncio').sleep(0.1)
        
        if schema_example:
            response = schema_example.copy()
            
            if "priority_zones" in response:
                zones = [f"zone_{i:02d}" for i in range(1, 10)]
                response["priority_zones"] = {
                    zone: round(self.random.random(), 2) 
                    for zone in self.random.sample(zones, 3)
                }
            
            if "reasoning" in response:
                response["reasoning"] = "模拟决策：基于当前情况的判断"
            
            if "action" in response and response["action"] == "":
                response["action"] = "wait"
            
            self._log_llm_call(prompt, response, True)
            
            if response_schema:
                return response_schema(**response)
            return response
        
        fallback = {
            "action": "wait",
            "reasoning": "模拟默认动作"
        }
        self._log_llm_call(prompt, fallback, True)
        return fallback
