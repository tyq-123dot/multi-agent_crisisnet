import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger
import redis.asyncio as redis

from crisisnet_common import Config, LLMClient, MockLLMClient
from env_sim import EnvironmentSimulator
from agents import (
    EOCAgent,
    FireRescueAgent,
    MedicalAgent,
    LogisticsAgent,
    PublicInfoAgent
)


def setup_logging():
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/test_events.log", rotation="500 MB", level="INFO")


async def test_simulation():
    setup_logging()
    logger.info("Starting CrisisNet Test Simulation (with Mock LLM)...")
    
    config = Config()
    config.simulation.total_ticks = 20
    config.simulation.ticks_per_real_second = 2.0
    
    redis_client = redis.Redis(
        host=config.redis.host,
        port=config.redis.port,
        db=config.redis.db + 1,
        decode_responses=False
    )
    
    await redis_client.flushdb()
    
    llm_clients = {}
    for role in ["eoc", "fire_rescue", "medical", "logistics", "public_info"]:
        llm_clients[role] = MockLLMClient(
            model=f"mock-{role}",
            llm_log_file="logs/mock_llm_calls.jsonl"
        )
    
    env_sim = EnvironmentSimulator(
        redis_client=redis_client,
        tick_interval=1.0 / config.simulation.ticks_per_real_second,
        total_ticks=config.simulation.total_ticks,
        random_seed=config.simulation.random_seed
    )
    
    agents = [
        EOCAgent(redis_client, llm_clients["eoc"], 3),
        FireRescueAgent(redis_client, llm_clients["fire_rescue"], 2),
        MedicalAgent(redis_client, llm_clients["medical"], 2),
        LogisticsAgent(redis_client, llm_clients["logistics"], 3),
        PublicInfoAgent(redis_client, llm_clients["public_info"], 4)
    ]
    
    tasks = []
    tasks.append(asyncio.create_task(env_sim.run()))
    
    for agent in agents:
        tasks.append(asyncio.create_task(agent.run()))
    
    try:
        await asyncio.gather(*tasks)
        logger.info("Test simulation completed successfully!")
    except KeyboardInterrupt:
        logger.info("Test interrupted by user")
        await env_sim.stop()
        for agent in agents:
            await agent.stop()
    finally:
        await redis_client.close()
        logger.info("Test shutdown complete.")


if __name__ == "__main__":
    asyncio.run(test_simulation())
