from typing import Dict, Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class LLMConfig(BaseSettings):
    base_url: str = "https://api.openai.com/v1"
    api_key: str = ""


class RedisConfig(BaseSettings):
    host: str = "localhost"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None


class SimulationConfig(BaseSettings):
    ticks_per_real_second: float = 1.0
    total_ticks: int = 500
    map_file: str = "data/city_grid.geojson"
    random_seed: int = 42


class AgentConfig(BaseSettings):
    decision_interval_ticks: int = 5
    llm_model: str = "gpt-4o-mini"


class AgentsConfig(BaseSettings):
    eoc: AgentConfig = Field(default_factory=lambda: AgentConfig(decision_interval_ticks=5, llm_model="gpt-4o-mini"))
    fire_rescue: AgentConfig = Field(default_factory=lambda: AgentConfig(decision_interval_ticks=2, llm_model="gpt-4o-mini"))
    medical: AgentConfig = Field(default_factory=lambda: AgentConfig(decision_interval_ticks=2, llm_model="gpt-4o-mini"))
    logistics: AgentConfig = Field(default_factory=lambda: AgentConfig(decision_interval_ticks=3, llm_model="gpt-4o-mini"))
    public_info: AgentConfig = Field(default_factory=lambda: AgentConfig(decision_interval_ticks=4, llm_model="gpt-4o-mini"))


class APIKeysConfig(BaseSettings):
    openai: Optional[str] = None
    openweather: Optional[str] = None


class LoggingConfig(BaseSettings):
    level: str = "INFO"
    llm_log_file: str = "logs/llm_calls.jsonl"
    events_log_file: str = "logs/events.log"


class Config(BaseSettings):
    simulation: SimulationConfig = Field(default_factory=SimulationConfig)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    agents: AgentsConfig = Field(default_factory=AgentsConfig)
    api_keys: APIKeysConfig = Field(default_factory=APIKeysConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    
    model_config = {
        "env_nested_delimiter": "__"
    }
