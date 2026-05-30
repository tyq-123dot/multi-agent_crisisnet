import asyncio
import json
import random
from datetime import datetime
from typing import Dict, List, Optional
from loguru import logger
import redis.asyncio as redis
from crisisnet_common import (
    WorldState,
    ZoneState,
    EnvironmentUpdate,
    ResourcePool,
    ResourceType,
    AgentRole,
    AgentMessage
)


class EnvironmentSimulator:
    def __init__(
        self,
        redis_client: redis.Redis,
        tick_interval: float = 1.0,
        total_ticks: int = 500,
        random_seed: int = 42
    ):
        self.redis = redis_client
        self.tick_interval = tick_interval
        self.total_ticks = total_ticks
        self.current_tick = 0
        self.running = False
        self.random = random.Random(random_seed)
        
        self.world_state = self._init_world_state()
        self.resource_pool = self._init_resource_pool()
        self.pending_events: List[Dict] = []
    
    def _init_world_state(self) -> WorldState:
        zones = {}
        for i in range(1, 10):
            zone_id = f"zone_{i:02d}"
            zones[zone_id] = ZoneState(
                zone_id=zone_id, disaster_intensity=0.0)
        
        zones["zone_05"].disaster_intensity = 0.8
        zones["zone_06"].disaster_intensity = 0.6
        
        return WorldState(
            tick=0,
            zones=zones,
            timestamp=datetime.now()
        )
    
    def _init_resource_pool(self) -> ResourcePool:
        return ResourcePool(resources={
            ResourceType.HELICOPTER: 2,
            ResourceType.MEDKIT: 100,
            ResourceType.WATER_PUMP: 10,
            ResourceType.FOOD_RATION: 500,
            ResourceType.COLD_TRUCK: 3,
            ResourceType.AMBULANCE: 5
        })
    
    async def _save_resource_pool(self):
        pool_data = {k.value: v for k, v in self.resource_pool.resources.items()}
        await self.redis.hset("resource_pool", mapping=pool_data)
    
    def _update_disaster_spread(self):
        for zone_id, zone in self.world_state.zones.items():
            if zone.disaster_intensity > 0:
                neighbors = self._get_neighbors(zone_id)
                for neighbor_id in neighbors:
                    if self.world_state.zones[neighbor_id].disaster_intensity < 0.3:
                    spread = zone.disaster_intensity * 0.1 * self.random.random()
                    self.world_state.zones[neighbor_id].disaster_intensity = min(
                        1.0,
                        self.world_state.zones[neighbor_id].disaster_intensity + spread
                    )
            
            zone.disaster_intensity = max(0.0, zone.disaster_intensity - 0.005)
            
            if zone.disaster_intensity > 0.3:
                zone.casualties += int(zone.disaster_intensity * 5)
                zone.trapped_people += int(zone.disaster_intensity * 2)
    
    def _get_neighbors(self, zone_id: str) -> List[str]:
        zone_num = int(zone_id.split("_")[1])
        neighbors = []
        if zone_num > 1:
            neighbors.append(f"zone_{zone_num-1:02d}")
        if zone_num < 9:
            neighbors.append(f"zone_{zone_num+1:02d}")
        return neighbors
    
    def _generate_random_event(self) -> Optional[Dict]:
        event_types = [
            {"type": "bridge_collapse", "zone": f"zone_{self.random.randint(1, 9):02d}", "severity": 0.5},
            {"type": "citizen_help", "zone": f"zone_{self.random.randint(1, 9):02d}", "message": "有人被困在三楼"},
            {"type": "road_blocked", "zone": f"zone_{self.random.randint(1, 9):02d}"}
        ]
        if self.random.random() < 0.1:
            return self.random.choice(event_types)
        return None
    
    async def _publish_environment_update(self):
        new_event = self._generate_random_event()
        if new_event:
            self.pending_events.append(new_event)
        
        env_update = EnvironmentUpdate(
            world_state=self.world_state,
            new_events=self.pending_events.copy()
        )
        
        msg = AgentMessage(
            msg_id=f"env_update_{self.current_tick}",
            timestamp=datetime.now(),
            sender=AgentRole.EOC,
            recipient="broadcast",
            payload=env_update.model_dump()
        )
        
        await self.redis.publish("environment_updates", json.dumps(msg.model_dump()))
        await self.redis.set("current_world_state", json.dumps(self.world_state.model_dump()))
        self.pending_events = []
    
    async def _save_agent_state(self, role: AgentRole, state: Dict):
        await self.redis.hset(f"agent:{role.value}:state", mapping=state)
    
    async def _tick(self):
        self.current_tick += 1
        self.world_state.tick = self.current_tick
        self.world_state.timestamp = datetime.now()
        
        self._update_disaster_spread()
        
        await self._publish_environment_update()
        await self._save_resource_pool()
        
        logger.info(f"Tick {self.current_tick}/{self.total_ticks} completed")
    
    async def run(self):
        self.running = True
        logger.info("Environment Simulator starting...")
        
        await self._save_resource_pool()
        await self._publish_environment_update()
        
        while self.running and self.current_tick < self.total_ticks:
            await asyncio.sleep(self.tick_interval)
            await self._tick()
        
        logger.info("Environment Simulator stopped")
    
    async def stop(self):
        self.running = False
