import asyncio
import sys
import os
import argparse
from loguru import logger
import yaml
import redis.asyncio as redis

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from crisisnet_common import (
    Config,
    LLMClient,
    CaseDatabase,
    RuleEngine,
    FallbackLLMClient,
    LLMFallbackMode,
    DataAdapterManager,
    MockGISAdapter,
    MockIoTAdapter,
    MockSocialMediaAdapter,
    MockHotlineAdapter,
    MockWeatherAdapter,
    DecisionAuditStore,
    HumanInTheLoop,
    DirectCommandManager
)
from env_sim import EnvironmentSimulator
from agents import (
    EOCAgent,
    FireRescueAgent,
    MedicalAgent,
    LogisticsAgent,
    PublicInfoAgent
)


def setup_logging(log_level: str = "INFO", events_log_file: str = "logs/events.log"):
    logger.remove()
    logger.add(sys.stderr, level=log_level)
    logger.add(events_log_file, rotation="500 MB", level="INFO")


def load_config(config_file: str = "config.yaml") -> Config:
    if os.path.exists(config_file):
        with open(config_file, "r", encoding="utf-8") as f:
            config_data = yaml.safe_load(f)
        return Config(**config_data)
    return Config()


async def main():
    parser = argparse.ArgumentParser(description="CrisisNet - Multi-Agent Disaster Response Simulation")
    parser.add_argument("--config", type=str, default="config.yaml", help="Path to config file")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")
    parser.add_argument("--use-mock-data", action="store_true", default=True, help="Use mock data adapters")
    parser.add_argument("--fallback-mode", type=str, default="cloud_first", 
                       choices=["cloud_only", "cloud_first", "ollama_first", "rule_only", "hybrid"],
                       help="LLM fallback mode")
    args = parser.parse_args()

    config = load_config(args.config)

    log_level = "DEBUG" if args.debug else config.logging.level
    setup_logging(log_level, config.logging.events_log_file)

    logger.info("Starting CrisisNet...")

    redis_client = redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db,
        password=config.redis.password,
        decode_responses=False
    )

    await redis_client.flushdb()

    # Initialize case database with sample cases
    case_db = CaseDatabase(persist_directory="data/case_db")
    await case_db.initialize_sample_cases()
    logger.info("Case database initialized")

    # Initialize rule engine
    rule_engine = RuleEngine()
    logger.info("Rule engine initialized")

    # Initialize decision audit store
    audit_store = DecisionAuditStore(db_path="data/decisions.db")
    logger.info("Decision audit store initialized")

    # Initialize human in the loop
    hitl = HumanInTheLoop(redis_client, auto_approve_low=True)
    logger.info("Human in the loop initialized")

    # Initialize direct command manager
    command_manager = DirectCommandManager(redis_client)
    logger.info("Direct command manager initialized")

    # Initialize data adapters
    data_manager = DataAdapterManager()
    if args.use_mock_data:
        data_manager.register_adapter(MockGISAdapter())
        data_manager.register_adapter(MockIoTAdapter())
        data_manager.register_adapter(MockSocialMediaAdapter())
        data_manager.register_adapter(MockHotlineAdapter())
        data_manager.register_adapter(MockWeatherAdapter())
        logger.info("Mock data adapters registered")

    # Map fallback mode
    fallback_mode_map = {
        "cloud_only": LLMFallbackMode.CLOUD_ONLY,
        "cloud_first": LLMFallbackMode.CLOUD_FIRST,
        "ollama_first": LLMFallbackMode.OLLAMA_FIRST,
        "rule_only": LLMFallbackMode.RULE_ONLY,
        "hybrid": LLMFallbackMode.HYBRID
    }
    fallback_mode = fallback_mode_map.get(args.fallback_mode, LLMFallbackMode.CLOUD_FIRST)

    # Initialize LLM clients with fallback
    llm_clients = {}
    api_key = config.llm.api_key or config.api_keys.openai or "dummy_key"
    
    for role in ["eoc", "fire_rescue", "medical", "logistics", "public_info"]:
        agent_config = getattr(config.agents, role)
        
        cloud_llm = LLMClient(
            api_key=api_key,
            base_url=config.llm.base_url,
            model=agent_config.llm_model,
            llm_log_file=config.logging.llm_log_file
        )
        
        fallback_llm = FallbackLLMClient(
            cloud_llm=cloud_llm,
            ollama_url="http://localhost:11434",
            ollama_model="llama3:8b",
            rule_engine=rule_engine,
            agent_role=role,
            fallback_mode=fallback_mode
        )
        
        llm_clients[role] = fallback_llm

    logger.info(f"LLM clients initialized with fallback mode: {fallback_mode.value}")

    # Environment simulator
    env_sim = EnvironmentSimulator(
        redis_client=redis_client,
        tick_interval=1.0 / config.simulation.ticks_per_real_second,
        total_ticks=config.simulation.total_ticks,
        random_seed=config.simulation.random_seed
    )

    # Initialize agents with all new features
    agents = [
        EOCAgent(
            redis_client=redis_client,
            llm_client=llm_clients["eoc"],
            case_database=case_db,
            decision_interval_ticks=config.agents.eoc.decision_interval_ticks
        ),
        FireRescueAgent(
            redis_client=redis_client,
            llm_client=llm_clients["fire_rescue"],
            decision_interval_ticks=config.agents.fire_rescue.decision_interval_ticks
        ),
        MedicalAgent(
            redis_client=redis_client,
            llm_client=llm_clients["medical"],
            decision_interval_ticks=config.agents.medical.decision_interval_ticks
        ),
        LogisticsAgent(
            redis_client=redis_client,
            llm_client=llm_clients["logistics"],
            decision_interval_ticks=config.agents.logistics.decision_interval_ticks
        ),
        PublicInfoAgent(
            redis_client=redis_client,
            llm_client=llm_clients["public_info"],
            case_database=case_db,
            decision_interval_ticks=config.agents.public_info.decision_interval_ticks
        )
    ]

    # Start data adapters
    adapter_tasks = []
    if args.use_mock_data:
        adapter_tasks = await data_manager.start()
        logger.info("Data adapters started")

    # Start all tasks
    tasks = []
    tasks.append(asyncio.create_task(env_sim.run()))

    for agent in agents:
        tasks.append(asyncio.create_task(agent.run()))

    try:
        await asyncio.gather(*tasks, *adapter_tasks)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
        await env_sim.stop()
        for agent in agents:
            await agent.stop()
        await data_manager.stop()
    finally:
        await redis_client.close()
        
        # Print final stats
        logger.info("=== Final Statistics ===")
        stats = audit_store.get_stats()
        logger.info(f"Total decisions: {stats['total_decisions']}")
        logger.info(f"Approved decisions: {stats['approved_decisions']}")
        logger.info(f"By mode: {stats['by_mode']}")
        
        logger.info("CrisisNet shutdown complete.")


if __name__ == "__main__":
    asyncio.run(main())
