import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Type, TypeVar
from enum import Enum
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from pydantic import BaseModel, ValidationError

from crisisnet_common import LLMClient, RuleEngine, AgentRole


T = TypeVar('T', bound=BaseModel)


class LLMFallbackMode(Enum):
    CLOUD_ONLY = "cloud_only"
    CLOUD_FIRST = "cloud_first"
    OLLAMA_FIRST = "ollama_first"
    RULE_ONLY = "rule_only"
    HYBRID = "hybrid"


class FallbackLLMClient:
    def __init__(
        self,
        cloud_llm: Optional[LLMClient] = None,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3:8b",
        rule_engine: Optional[RuleEngine] = None,
        agent_role: Optional[AgentRole] = None,
        fallback_mode: LLMFallbackMode = LLMFallbackMode.CLOUD_FIRST,
        cloud_timeout: float = 10.0,
        ollama_timeout: float = 30.0
    ):
        self.cloud_llm = cloud_llm
        self.ollama_url = ollama_url
        self.ollama_model = ollama_model
        self.rule_engine = rule_engine or RuleEngine()
        self.agent_role = agent_role
        self.fallback_mode = fallback_mode
        self.cloud_timeout = cloud_timeout
        self.ollama_timeout = ollama_timeout
        
        self.cloud_available = True
        self.ollama_available = True
        self.last_cloud_error = 0
        self.last_ollama_error = 0
        self.cooldown_period = 60
        
        self._call_stats = {
            "cloud_calls": 0,
            "cloud_success": 0,
            "cloud_failures": 0,
            "ollama_calls": 0,
            "ollama_success": 0,
            "ollama_failures": 0,
            "rule_calls": 0
        }

    async def _check_ollama_health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Ollama health check failed: {e}")
            return False

    async def _call_ollama(
        self,
        prompt: str,
        response_schema: Optional[Type[T]] = None,
        schema_example: Optional[Dict[str, Any]] = None
    ) -> T | Dict[str, Any]:
        self._call_stats["ollama_calls"] += 1
        
        system_prompt = "You are a helpful AI assistant. Always respond in JSON format."
        if response_schema:
            system_prompt += f"\nYour response must conform to the following schema:\n{response_schema.model_json_schema()}"
            if schema_example:
                system_prompt += f"\nExample:\n{json.dumps(schema_example, ensure_ascii=False)}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        request_payload = {
            "model": self.ollama_model,
            "messages": messages,
            "stream": False,
            "format": "json",
            "options": {
                "temperature": 0.1,
                "num_predict": 500
            }
        }
        
        try:
            async with httpx.AsyncClient(timeout=self.ollama_timeout) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/chat",
                    json=request_payload
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["message"]["content"]
                parsed_response = json.loads(content)
                
                self._call_stats["ollama_success"] += 1
                self.ollama_available = True
                logger.info(f"Ollama call successful: {self.ollama_model}")
                
                if response_schema:
                    return response_schema(**parsed_response)
                return parsed_response
                
        except Exception as e:
            self._call_stats["ollama_failures"] += 1
            self.ollama_available = False
            self.last_ollama_error = time.time()
            logger.error(f"Ollama call failed: {e}")
            raise

    def _call_rule_engine(
        self,
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        self._call_stats["rule_calls"] += 1
        logger.info(f"Falling back to rule engine for {self.agent_role.value if self.agent_role else 'unknown'}")
        
        if self.agent_role:
            return self.rule_engine.decide(self.agent_role, observation, context)
        
        return {
            "action": "wait",
            "reasoning": "规则引擎：LLM不可用，进入等待状态。"
        }

    async def call(
        self,
        prompt: str,
        observation: Dict[str, Any] = None,
        context: Dict[str, Any] = None,
        response_schema: Optional[Type[T]] = None,
        schema_example: Optional[Dict[str, Any]] = None
    ) -> T | Dict[str, Any]:
        observation = observation or {}
        context = context or {}
        
        mode = self.fallback_mode
        
        if mode == LLMFallbackMode.RULE_ONLY:
            return self._call_rule_engine(observation, context)
        
        if mode == LLMFallbackMode.CLOUD_ONLY and self.cloud_llm:
            return await self._try_cloud(prompt, response_schema, schema_example, observation, context)
        
        if mode == LLMFallbackMode.OLLAMA_FIRST:
            return await self._try_ollama_first(prompt, response_schema, schema_example, observation, context)
        
        return await self._try_cloud_first(prompt, response_schema, schema_example, observation, context)

    async def _try_cloud(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        schema_example: Optional[Dict[str, Any]],
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> T | Dict[str, Any]:
        if not self.cloud_llm:
            return self._call_rule_engine(observation, context)
        
        try:
            if time.time() - self.last_cloud_error < self.cooldown_period:
                logger.info("Cloud LLM in cooldown, skipping...")
                raise Exception("Cloud LLM in cooldown")
            
            self._call_stats["cloud_calls"] += 1
            result = await self.cloud_llm.call(prompt, response_schema, schema_example)
            self._call_stats["cloud_success"] += 1
            self.cloud_available = True
            return result
        except Exception as e:
            self._call_stats["cloud_failures"] += 1
            self.cloud_available = False
            self.last_cloud_error = time.time()
            logger.warning(f"Cloud LLM failed: {e}")
            raise

    async def _try_cloud_first(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        schema_example: Optional[Dict[str, Any]],
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> T | Dict[str, Any]:
        try:
            return await self._try_cloud(prompt, response_schema, schema_example, observation, context)
        except Exception:
            try:
                return await self._try_ollama(prompt, response_schema, schema_example, observation, context)
            except Exception:
                return self._call_rule_engine(observation, context)

    async def _try_ollama_first(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        schema_example: Optional[Dict[str, Any]],
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> T | Dict[str, Any]:
        try:
            return await self._try_ollama(prompt, response_schema, schema_example, observation, context)
        except Exception:
            try:
                return await self._try_cloud(prompt, response_schema, schema_example, observation, context)
            except Exception:
                return self._call_rule_engine(observation, context)

    async def _try_ollama(
        self,
        prompt: str,
        response_schema: Optional[Type[T]],
        schema_example: Optional[Dict[str, Any]],
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> T | Dict[str, Any]:
        if time.time() - self.last_ollama_error < self.cooldown_period:
            logger.info("Ollama in cooldown, skipping...")
            raise Exception("Ollama in cooldown")
        
        if not await self._check_ollama_health():
            self.ollama_available = False
            self.last_ollama_error = time.time()
            raise Exception("Ollama not available")
        
        return await self._call_ollama(prompt, response_schema, schema_example)

    def get_stats(self) -> Dict[str, Any]:
        return {
            **self._call_stats,
            "cloud_available": self.cloud_available,
            "ollama_available": self.ollama_available,
            "current_mode": self.fallback_mode.value
        }

    def reset_stats(self):
        self._call_stats = {
            "cloud_calls": 0,
            "cloud_success": 0,
            "cloud_failures": 0,
            "ollama_calls": 0,
            "ollama_success": 0,
            "ollama_failures": 0,
            "rule_calls": 0
        }
