import asyncio
import json
import random
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
from abc import ABC, abstractmethod
from loguru import logger
import httpx
from enum import Enum


class DataSourceType(Enum):
    GIS = "gis"
    IOT = "iot"
    SOCIAL_MEDIA = "social_media"
    HOTLINE = "hotline"
    WEATHER = "weather"


class DataAdapter(ABC):
    def __init__(self, name: str, source_type: DataSourceType):
        self.name = name
        self.source_type = source_type
        self.connected = False
        self.last_update = None
        self.callback: Optional[Callable] = None

    @abstractmethod
    async def connect(self) -> bool:
        pass

    @abstractmethod
    async def fetch_data(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    async def listen(self, callback: Callable):
        pass

    def set_callback(self, callback: Callable):
        self.callback = callback


class MockGISAdapter(DataAdapter):
    def __init__(self):
        super().__init__("MockGIS", DataSourceType.GIS)
        self.zones = self._init_mock_zones()
        self.pois = self._init_mock_pois()

    def _init_mock_zones(self) -> Dict[str, Any]:
        return {
            "zone_01": {"name": "市中心", "population": 50000, "roads": ["main_st", "broadway"]},
            "zone_02": {"name": "北区", "population": 30000, "roads": ["north_ave", "park_st"]},
            "zone_03": {"name": "南区", "population": 35000, "roads": ["south_rd", "lake_st"]},
            "zone_04": {"name": "东区", "population": 25000, "roads": ["east_blvd", "river_st"]},
            "zone_05": {"name": "西区", "population": 40000, "roads": ["west_hwy", "hill_st"]},
        }

    def _init_mock_pois(self) -> List[Dict[str, Any]]:
        return [
            {"type": "hospital", "name": "市第一医院", "zone": "zone_01", "capacity": 500},
            {"type": "fire_station", "name": "中心消防站", "zone": "zone_01", "trucks": 5},
            {"type": "hospital", "name": "北区医院", "zone": "zone_02", "capacity": 200},
            {"type": "fire_station", "name": "北区消防局", "zone": "zone_02", "trucks": 3},
            {"type": "shelter", "name": "市体育馆", "zone": "zone_03", "capacity": 2000},
            {"type": "hospital", "name": "南区诊所", "zone": "zone_03", "capacity": 100},
        ]

    async def connect(self) -> bool:
        self.connected = True
        logger.info("MockGIS adapter connected")
        return True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        events = []
        
        if random.random() < 0.3:
            zones = list(self.zones.keys())
            zone = random.choice(zones)
            road = random.choice(self.zones[zone]["roads"])
            events.append({
                "type": "road_condition",
                "source": "gis",
                "zone": zone,
                "road": road,
                "status": random.choice(["clear", "blocked", "congested"]),
                "timestamp": datetime.now().isoformat()
            })
        
        self.last_update = datetime.now()
        return events

    async def listen(self, callback: Callable):
        logger.info("MockGIS listening started")
        while self.connected:
            try:
                data = await self.fetch_data()
                if data and callback:
                    for event in data:
                        await callback(event)
                await asyncio.sleep(10)
            except Exception as e:
                logger.error(f"MockGIS listen error: {e}")
                await asyncio.sleep(5)


class MockIoTAdapter(DataAdapter):
    def __init__(self):
        super().__init__("MockIoT", DataSourceType.IOT)
        self.sensors = self._init_mock_sensors()

    def _init_mock_sensors(self) -> List[Dict[str, Any]]:
        return [
            {"id": "water_01", "type": "water_level", "zone": "zone_05", "location": "河边"},
            {"id": "water_02", "type": "water_level", "zone": "zone_04", "location": "水库"},
            {"id": "quake_01", "type": "seismometer", "zone": "zone_01", "location": "市中心"},
            {"id": "temp_01", "type": "temperature", "zone": "zone_02", "location": "北区"},
            {"id": "rain_01", "type": "rain_gauge", "zone": "zone_03", "location": "气象站"},
        ]

    async def connect(self) -> bool:
        self.connected = True
        logger.info("MockIoT adapter connected")
        return True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        events = []
        
        for sensor in self.sensors:
            if random.random() < 0.2:
                if sensor["type"] == "water_level":
                    level = random.uniform(0, 5)
                    events.append({
                        "type": "sensor_reading",
                        "source": "iot",
                        "sensor_id": sensor["id"],
                        "sensor_type": "water_level",
                        "zone": sensor["zone"],
                        "value": level,
                        "unit": "meters",
                        "alert": level > 3,
                        "timestamp": datetime.now().isoformat()
                    })
                elif sensor["type"] == "rain_gauge":
                    rainfall = random.uniform(0, 100)
                    events.append({
                        "type": "sensor_reading",
                        "source": "iot",
                        "sensor_id": sensor["id"],
                        "sensor_type": "rainfall",
                        "zone": sensor["zone"],
                        "value": rainfall,
                        "unit": "mm/hour",
                        "alert": rainfall > 50,
                        "timestamp": datetime.now().isoformat()
                    })
        
        self.last_update = datetime.now()
        return events

    async def listen(self, callback: Callable):
        logger.info("MockIoT listening started")
        while self.connected:
            try:
                data = await self.fetch_data()
                if data and callback:
                    for event in data:
                        await callback(event)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"MockIoT listen error: {e}")
                await asyncio.sleep(2)


class MockSocialMediaAdapter(DataAdapter):
    def __init__(self):
        super().__init__("MockSocialMedia", DataSourceType.SOCIAL_MEDIA)
        self.keywords = ["求救", "求助", "被困", "救命", "受灾", "危险", "#暴雨求救#", "#地震#"]

    async def connect(self) -> bool:
        self.connected = True
        logger.info("MockSocialMedia adapter connected")
        return True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        events = []
        
        if random.random() < 0.4:
            zones = [f"zone_{i:02d}" for i in range(1, 10)]
            zone = random.choice(zones)
            
            messages = [
                "我家在三楼，水已经漫上来了，快来救我们！",
                "这里有人受伤，需要医疗援助！",
                "房子快塌了，我们被困在里面！",
                "道路被冲毁了，需要救援船只！",
                "停电停水，食物快吃完了！",
            ]
            
            message = random.choice(messages)
            has_image = random.random() < 0.3
            
            events.append({
                "type": "social_post",
                "source": "social_media",
                "platform": random.choice(["weibo", "douyin", "wechat"]),
                "content": message,
                "zone": zone,
                "author_id": f"user_{random.randint(1000, 9999)}",
                "has_image": has_image,
                "likes": random.randint(0, 1000),
                "shares": random.randint(0, 500),
                "timestamp": datetime.now().isoformat()
            })
        
        self.last_update = datetime.now()
        return events

    async def listen(self, callback: Callable):
        logger.info("MockSocialMedia listening started")
        while self.connected:
            try:
                data = await self.fetch_data()
                if data and callback:
                    for event in data:
                        await callback(event)
                await asyncio.sleep(8)
            except Exception as e:
                logger.error(f"MockSocialMedia listen error: {e}")
                await asyncio.sleep(3)


class MockHotlineAdapter(DataAdapter):
    def __init__(self):
        super().__init__("MockHotline", DataSourceType.HOTLINE)

    async def connect(self) -> bool:
        self.connected = True
        logger.info("MockHotline adapter connected")
        return True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        events = []
        
        if random.random() < 0.25:
            zones = [f"zone_{i:02d}" for i in range(1, 10)]
            zone = random.choice(zones)
            
            ticket_types = ["medical_emergency", "rescue_request", "supply_request", "information"]
            ticket_type = random.choice(ticket_types)
            
            descriptions = {
                "medical_emergency": "老人心脏病发作，急需救护车",
                "rescue_request": "一家人被困在屋顶",
                "supply_request": "需要饮用水和方便面",
                "information": "询问什么时候恢复供电"
            }
            
            events.append({
                "type": "hotline_ticket",
                "source": "hotline",
                "ticket_id": f"HTL{datetime.now().strftime('%Y%m%d%H%M%S')}",
                "ticket_type": ticket_type,
                "zone": zone,
                "description": descriptions[ticket_type],
                "caller_phone": f"138{random.randint(10000000, 99999999)}",
                "priority": random.randint(1, 5),
                "timestamp": datetime.now().isoformat()
            })
        
        self.last_update = datetime.now()
        return events

    async def listen(self, callback: Callable):
        logger.info("MockHotline listening started")
        while self.connected:
            try:
                data = await self.fetch_data()
                if data and callback:
                    for event in data:
                        await callback(event)
                await asyncio.sleep(15)
            except Exception as e:
                logger.error(f"MockHotline listen error: {e}")
                await asyncio.sleep(5)


class MockWeatherAdapter(DataAdapter):
    def __init__(self):
        super().__init__("MockWeather", DataSourceType.WEATHER)

    async def connect(self) -> bool:
        self.connected = True
        logger.info("MockWeather adapter connected")
        return True

    async def fetch_data(self) -> List[Dict[str, Any]]:
        events = []
        
        if random.random() < 0.3:
            events.append({
                "type": "weather_update",
                "source": "weather",
                "temperature": random.uniform(15, 35),
                "humidity": random.uniform(40, 95),
                "wind_speed": random.uniform(0, 30),
                "precipitation": random.uniform(0, 100),
                "alert": random.random() < 0.2,
                "alert_level": random.choice(["yellow", "orange", "red"]) if random.random() < 0.2 else None,
                "timestamp": datetime.now().isoformat()
            })
        
        self.last_update = datetime.now()
        return events

    async def listen(self, callback: Callable):
        logger.info("MockWeather listening started")
        while self.connected:
            try:
                data = await self.fetch_data()
                if data and callback:
                    for event in data:
                        await callback(event)
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"MockWeather listen error: {e}")
                await asyncio.sleep(10)


class DataAdapterManager:
    def __init__(self):
        self.adapters: Dict[str, DataAdapter] = {}
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

    def register_adapter(self, adapter: DataAdapter):
        self.adapters[adapter.name] = adapter
        logger.info(f"Registered adapter: {adapter.name}")

    async def connect_all(self) -> bool:
        success = True
        for name, adapter in self.adapters.items():
            try:
                await adapter.connect()
            except Exception as e:
                logger.error(f"Failed to connect {name}: {e}")
                success = False
        return success

    async def _adapter_worker(self, adapter: DataAdapter):
        async def callback(event: Dict[str, Any]):
            await self.event_queue.put(event)
            logger.debug(f"Event received from {adapter.name}: {event['type']}")
        
        await adapter.listen(callback)

    async def start(self):
        self.running = True
        
        await self.connect_all()
        
        tasks = []
        for adapter in self.adapters.values():
            task = asyncio.create_task(self._adapter_worker(adapter))
            tasks.append(task)
        
        return tasks

    async def get_event(self, timeout: Optional[float] = None) -> Optional[Dict[str, Any]]:
        try:
            if timeout:
                return await asyncio.wait_for(self.event_queue.get(), timeout=timeout)
            return await self.event_queue.get()
        except asyncio.TimeoutError:
            return None

    async def stop(self):
        self.running = False
        for adapter in self.adapters.values():
            adapter.connected = False

    def get_status(self) -> Dict[str, Any]:
        return {
            name: {
                "connected": adapter.connected,
                "last_update": adapter.last_update.isoformat() if adapter.last_update else None,
                "type": adapter.source_type.value
            }
            for name, adapter in self.adapters.items()
        }
