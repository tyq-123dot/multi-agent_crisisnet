import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, Type, TypeVar
from loguru import logger
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import httpx
from pydantic import BaseModel, ValidationError


T = TypeVar('T', bound=BaseModel)


class LLMClient:
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        temperature: float = 0.1,
        llm_log_file: str = "logs/llm_calls.jsonl"
    ):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.temperature = temperature
        self.llm_log_file = llm_log_file
        self._last_call_time = 0
        self._min_interval = 0.2  # 5 QPS limit
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_ttl = 120  # 2 minutes
    
    def _log_llm_call(self, prompt: str, response: Dict[str, Any], success: bool):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "model": self.model,
            "prompt": prompt,
            "response": response,
            "success": success
        }
        try:
            with open(self.llm_log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to write LLM log: {e}")
    
    async def _rate_limit(self):
        current_time = time.time()
        time_since_last = current_time - self._last_call_time
        if time_since_last < self._min_interval:
            await asyncio.sleep(self._min_interval - time_since_last)
        self._last_call_time = time.time()
    
    def _get_cache_key(self, prompt: str, schema: Optional[str]) -> str:
        return f"{self.model}:{hash(prompt)}:{hash(schema or '')}"
    
    @retry(
        stop=stop_after_attempt(2),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, ValidationError))
    )
    async def call(
        self,
        prompt: str,
        response_schema: Optional[Type[T]] = None,
        schema_example: Optional[Dict[str, Any]] = None
    ) -> T | Dict[str, Any]:
        cache_key = self._get_cache_key(prompt, str(response_schema) if response_schema else None)
        
        if cache_key in self._cache:
            cached_result = self._cache[cache_key]
            if time.time() - cached_result["timestamp"] < self._cache_ttl:
                logger.debug("Using cached LLM response")
                return cached_result["data"]
        
        await self._rate_limit()
        
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
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "response_format": {"type": "json_object"}
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json=request_payload
                )
                response.raise_for_status()
                result = response.json()
                
                content = result["choices"][0]["message"]["content"]
                parsed_response = json.loads(content)
                
                self._log_llm_call(prompt, parsed_response, True)
                
                self._cache[cache_key] = {
                    "timestamp": time.time(),
                    "data": parsed_response
                }
                
                if response_schema:
                    return response_schema(**parsed_response)
                return parsed_response
                
        except (httpx.HTTPError, json.JSONDecodeError, ValidationError) as e:
            self._log_llm_call(prompt, {"error": str(e)}, False)
            logger.error(f"LLM call failed: {e}")
            raise
