import asyncio
import json
import os
import sys
import random
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

import websockets
import redis.asyncio as redis
from loguru import logger

sys.path.insert(0, str(Path(__file__).parent))

from crisisnet_common import Config
from crisisnet_common.trust_verification import (
    TrustVerificationLayer,
    ActionSuggestion,
    ActionType,
    PermissionLevel
)
from crisisnet_common.human_in_the_loop import (
    HumanInTheLoopGateway,
    SuggestionCard,
    DecisionStatus
)
from crisisnet_common.negotiation_protocol import (
    NegotiationSession,
    NegotiationMessage,
    NegotiationStatus,
    NegotiationStep,
    NegotiationProtocol,
    ActionTracker
)


class CrisisNetWebSocketServer:
    """WebSocket 服务器，用于连接前端和后端仿真系统"""
    
    def __init__(self, config: Config, host: str = "localhost", port: int = 8000):
        self.config = config
        self.host = host
        self.port = port
        self.clients: set = set()
        self.redis_client = None
        self.current_state = self._get_initial_state()
        self.tick = 0
        self.is_running = False
        
        self.trust_layer = TrustVerificationLayer({
            "map_bounds": {"min_lat": 39.8, "max_lat": 40.0, "min_lng": 116.2, "max_lng": 116.6},
            "safe_zones": ["zone_01", "zone_02", "zone_07", "zone_08", "zone_09"],
            "danger_zones": ["zone_04"]
        })
        
        self.hitl_gateway = HumanInTheLoopGateway({
            "timeout_seconds": 30,
            "auto_approve_non_critical": True
        })
        
        # 协商会话管理
        self.negotiation_sessions: Dict[str, NegotiationSession] = {}
        
        # 动作追踪与回滚
        self.action_tracker = ActionTracker()
        
        self.hitl_gateway.subscribe(self._on_gateway_update)
    
    def _get_initial_state(self) -> Dict[str, Any]:
        """获取初始仿真状态"""
        return {
            "tick": 0,
            "worldState": {
                "zones": {
                    f"zone_{i:02d}": {
                        "disasterIntensity": 0.1 if i in [1, 2, 7, 8, 9] else 0.5,
                        "trapped": 0,
                        "casualties": 0,
                        "roadAvailable": True
                    }
                    for i in range(1, 10)
                },
                "eocPriorities": {},
                "infrastructureStatus": {
                    "power": "online",
                    "water": "online",
                    "gas": "online"
                }
            },
            "agents": [
                {
                    "id": "eoc",
                    "role": "eoc",
                    "position": {"lat": 39.9042, "lng": 116.4074},
                    "currentTask": "分析态势，提供决策建议",
                    "resources": {},
                    "lastDecision": {},
                    "thinking": "正在分析当前灾害分布..."
                },
                {
                    "id": "fire_1",
                    "role": "fire",
                    "position": {"lat": 39.9082, "lng": 116.4124},
                    "currentTask": "待命",
                    "resources": {"water": 100, "pumps": 3},
                    "lastDecision": {"action": "wait"},
                    "thinking": "等待指令"
                },
                {
                    "id": "medical_1",
                    "role": "medical",
                    "position": {"lat": 39.9012, "lng": 116.4024},
                    "currentTask": "待命",
                    "resources": {"medkits": 50, "ambulances": 3},
                    "lastDecision": {"action": "wait"},
                    "thinking": "等待指令"
                },
                {
                    "id": "warehouse_1",
                    "role": "warehouse",
                    "position": {"lat": 39.9102, "lng": 116.4004},
                    "currentTask": "管理物资库存",
                    "resources": {"food": 500, "medkits": 200, "water": 300},
                    "lastDecision": {"action": "manage_warehouse"},
                    "thinking": "盘点库存中..."
                },
                {
                    "id": "transport_1",
                    "role": "transport",
                    "position": {"lat": 39.9062, "lng": 116.3994},
                    "currentTask": "待命",
                    "resources": {"trucks": 5, "drivers": 5},
                    "lastDecision": {"action": "wait"},
                    "thinking": "等待运输任务"
                },
                {
                    "id": "police_1",
                    "role": "police",
                    "position": {"lat": 39.9002, "lng": 116.4094},
                    "currentTask": "巡逻与交通管制",
                    "resources": {"officers": 10, "vehicles": 4},
                    "lastDecision": {"action": "patrol"},
                    "thinking": "监控道路状况"
                },
                {
                    "id": "utility_1",
                    "role": "utility",
                    "position": {"lat": 39.9052, "lng": 116.4044},
                    "currentTask": "巡检基础设施",
                    "resources": {"repair_teams": 3, "equipment": "full"},
                    "lastDecision": {"action": "inspect"},
                    "thinking": "检查水电煤气状况"
                },
                {
                    "id": "public_info",
                    "role": "public_info",
                    "position": {"lat": 39.9032, "lng": 116.4104},
                    "currentTask": "监控并发布公告",
                    "resources": {},
                    "lastDecision": {"action": "monitor"},
                    "thinking": "分析社交媒体信息..."
                }
            ],
            "events": [],
            "negotiations": [],
            "escalated_conflicts": [],
            "pending_actions": [],
            "suggestions": {"pending": [], "recent": []},
            "kpis": {
                "rescued": 0,
                "trapped": 0,
                "casualtyRate": 0,
                "deliverySuccess": 100,
                "avgResponseTime": 0
            },
            "resources": {
                "helicopter": 3,
                "medkit": 200,
                "water_pump": 15,
                "food": 500
            }
        }
    
    def _on_gateway_update(self, card: SuggestionCard):
        """网关状态更新回调"""
        self.current_state["suggestions"] = self.hitl_gateway.get_all_suggestions()
    
    def _simulate_negotiation(self):
        """模拟医疗与仓库的协商会话"""
        if self.tick % 15 == 0 and random.random() < 0.3:
            # 创建新的协商会话
            session = NegotiationSession(
                participants=["medical_1", "warehouse_1"]
            )
            
            # 步骤 1: 医疗发起物资申请
            resource_options = ["medicine", "medkits", "water"]
            qty = random.randint(10, 50)
            target_zones = ["zone_03", "zone_04", "zone_05"]
            
            request_msg = NegotiationProtocol.create_medical_supply_request(
                agent_id="medical_1",
                resource_type=random.choice(resource_options),
                quantity=qty,
                target_zone=random.choice(target_zones),
                urgency=random.choice(["normal", "urgent", "critical"]),
                medical_reason=f"Zone has {random.randint(5, 20)} casualties"
            )
            
            session.add_message(request_msg)
            
            # 步骤 2: 仓库响应
            available = random.random() > 0.2
            alternative = None
            if not available:
                alternative = {
                    "alternative_resource": "bandages",
                    "alternative_quantity": qty * 2,
                    "note": "Insufficient stock, offering alternative"
                }
            
            response_msg = NegotiationProtocol.create_supply_response(
                warehouse_agent="warehouse_1",
                original_request=request_msg,
                available=available,
                alternative_suggestion=alternative,
                delivery_eta=random.randint(10, 30) if available else None
            )
            
            session.add_message(response_msg)
            
            # 步骤 3: 医疗确认
            accepted = available or (alternative and random.random() > 0.3)
            confirm_msg = NegotiationProtocol.create_confirmation(
                requester_agent="medical_1",
                response=response_msg,
                accepted=accepted,
                confirmation_note="OK, let's proceed" if accepted else "No, let's try again"
            )
            
            success, needs_escalate = session.add_message(confirm_msg)
            
            self.negotiation_sessions[session.session_id] = session
            
            if needs_escalate:
                self._handle_escalation(session)
            
            # 更新前端状态
            self._update_negotiations_state()
    
    def _handle_escalation(self, session: NegotiationSession):
        """处理协商冲突升级"""
        session.status = NegotiationStatus.ESCALATED
        session.escalation_note = "Failed to reach agreement after 3 rounds"
        
        escalation_data = {
            "session_id": session.session_id,
            "participants": session.participants,
            "messages": [msg.dict() for msg in session.messages],
            "escalated_at": datetime.now().isoformat(),
            "summary": f"Conflict between {', '.join(session.participants)}"
        }
        
        self.current_state["escalated_conflicts"].insert(0, escalation_data)
        if len(self.current_state["escalated_conflicts"]) > 10:
            self.current_state["escalated_conflicts"] = self.current_state["escalated_conflicts"][:10]
        
        logger.warning(f"Conflict escalated: {session.session_id}")
    
    def _update_negotiations_state(self):
        """更新协商状态到前端"""
        self.current_state["negotiations"] = [
            {
                "session_id": s.session_id,
                "participants": s.participants,
                "status": s.status.value,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat()
            }
            for s in self.negotiation_sessions.values()
        ]
    
    def _update_state(self):
        """更新仿真状态"""
        self.tick += 1
        state = self.current_state
        state["tick"] = self.tick
        
        for zone_id, zone in state["worldState"]["zones"].items():
            if zone_id in ["zone_04", "zone_05"]:
                zone["disasterIntensity"] = min(1.0, zone["disasterIntensity"] + random.uniform(-0.05, 0.1))
                zone["trapped"] += random.randint(0, 2)
                zone["casualties"] += random.randint(0, 1)
            else:
                zone["disasterIntensity"] = max(0, zone["disasterIntensity"] + random.uniform(-0.02, 0.03))
        
        state["worldState"]["eocPriorities"] = {
            "zone_04": random.uniform(0.8, 1.0),
            "zone_05": random.uniform(0.6, 0.9),
            "zone_03": random.uniform(0.4, 0.7)
        }
        
        state["kpis"]["rescued"] = min(100, state["kpis"]["rescued"] + random.randint(0, 2))
        state["kpis"]["trapped"] = sum(z["trapped"] for z in state["worldState"]["zones"].values())
        
        # 模拟协商会话
        self._simulate_negotiation()
        
        # 更新待执行动作列表
        state["pending_actions"] = self.action_tracker.get_pending_actions()
        
        if self.tick % 8 == 0:
            self._simulate_agent_decisions()
        
        if random.random() < 0.3:
            event_types = ["eoc", "resource", "negotiation", "public"]
            messages = [
                "EOC 发布区域优先级建议",
                "消防请求支援",
                "医疗与仓库协调医疗物资",
                "公宣发布避险指南"
            ]
            event = {
                "id": len(state["events"]) + 1,
                "time": datetime.now().strftime("%H:%M:%S"),
                "type": random.choice(event_types),
                "message": random.choice(messages),
                "tick": self.tick
            }
            state["events"].append(event)
            if len(state["events"]) > 20:
                state["events"].pop(0)
        
        self._update_agent_tasks(state)
        state["suggestions"] = self.hitl_gateway.get_all_suggestions()
    
    def _update_agent_tasks(self, state):
        """更新智能体任务"""
        for agent in state["agents"]:
            if agent["role"] == "fire" and self.tick % 10 == 0:
                agent["currentTask"] = "前往 zone_04 灭火"
                agent["thinking"] = "检测到 zone_04 火灾严重，准备前往"
            elif agent["role"] == "police" and self.tick % 12 == 0:
                agent["currentTask"] = "在 zone_03 进行交通管制"
                agent["thinking"] = "灾区附近需要维持秩序"
            elif agent["role"] == "utility" and self.tick % 15 == 0:
                agent["currentTask"] = "修复 zone_02 的电力"
                agent["thinking"] = "检测到电路故障"
    
    def _simulate_agent_decisions(self):
        """模拟智能体决策"""
        state = self.current_state
        
        agent_roles = ["police", "utility", "warehouse", "transport", "medical", "fire", "eoc"]
        random.shuffle(agent_roles)
        selected_role = random.choice(agent_roles)
        
        agent = next((a for a in state["agents"] if a["role"] == selected_role), None)
        if not agent:
            return
        
        action_payload, permission_level = self._generate_role_action(selected_role)
        
        suggestion = ActionSuggestion(
            agent_role=selected_role,
            agent_id=agent["id"],
            action_type=ActionType.CRITICAL,
            permission_level=permission_level,
            action_payload=action_payload,
            reasoning=self._generate_reasoning(selected_role, action_payload)
        )
        
        world_state_dict = {"zones": state["worldState"]["zones"]}
        passed, verification_results, fallback = self.trust_layer.verify_action(
            suggestion, world_state_dict, state["resources"]
        )
        
        # 提交到网关
        asyncio.create_task(
            self.hitl_gateway.submit_suggestion(suggestion, verification_results, permission_level)
        )
        
        # 同时记录到动作追踪器
        if passed and permission_level in [PermissionLevel.LEVEL_2, PermissionLevel.LEVEL_3]:
            action_id = f"action_{self.tick}_{agent['id']}"
            self.action_tracker.register_pending_action(
                action_id=action_id,
                agent_role=selected_role,
                action_payload=action_payload,
                metadata={"tick": self.tick, "suggestion_id": suggestion.agent_id}
            )
        
        state["events"].append({
            "id": len(state["events"]) + 1,
            "time": datetime.now().strftime("%H:%M:%S"),
            "type": "suggestion",
            "message": f"{selected_role} 智能体提议执行动作（权限级别 {permission_level.name}）",
            "tick": self.tick
        })
        
        if len(state["events"]) > 20:
            state["events"].pop(0)
    
    def _generate_role_action(self, role: str):
        """根据智能体角色生成动作和权限级别"""
        if role == "police":
            action_chance = random.random()
            if action_chance < 0.3:
                return {"action": "mass_evacuate", "target_zone": "zone_04"}, PermissionLevel.LEVEL_1
            elif action_chance < 0.7:
                return {"action": "traffic_control", "target_zone": "zone_03"}, PermissionLevel.LEVEL_2
            else:
                return {"action": "report", "status": "patrol_complete"}, PermissionLevel.LEVEL_3
        
        elif role == "utility":
            action_chance = random.random()
            if action_chance < 0.2:
                return {"action": "cut_power", "target_zone": "zone_05"}, PermissionLevel.LEVEL_1
            elif action_chance < 0.6:
                return {"action": "repair_utility", "target_zone": "zone_02", "utility": "power"}, PermissionLevel.LEVEL_2
            else:
                return {"action": "update_infrastructure", "status": "stable"}, PermissionLevel.LEVEL_3
        
        elif role == "warehouse":
            action_chance = random.random()
            if action_chance < 0.3:
                return {"action": "relocate_supplies", "from_zone": "zone_07", "to_zone": "zone_03", "resources": {"medkits": 30}}, PermissionLevel.LEVEL_2
            else:
                return {"action": "manage_warehouse", "inventory": "check"}, PermissionLevel.LEVEL_3
        
        elif role == "transport":
            action_chance = random.random()
            if action_chance < 0.3:
                return {"action": "requisition_vehicle", "count": 2, "reason": "紧急运输"}, PermissionLevel.LEVEL_1
            elif action_chance < 0.8:
                return {"action": "reroute_truck", "new_route": "zone_02"}, PermissionLevel.LEVEL_2
            else:
                return {"action": "transport", "target_zone": "zone_03"}, PermissionLevel.LEVEL_3
        
        elif role == "medical":
            if random.random() < 0.2:
                return {"action": "evacuate", "target_zone": "zone_03"}, PermissionLevel.LEVEL_1
            else:
                return {"action": "treat", "target_zone": "zone_03"}, PermissionLevel.LEVEL_3
        
        elif role == "fire":
            if random.random() < 0.2:
                return {"action": "evacuate", "target_zone": "zone_05"}, PermissionLevel.LEVEL_1
            else:
                return {"action": "move_to", "target_zone": "zone_04"}, PermissionLevel.LEVEL_3
        
        else:
            return {"action": "status_report", "summary": "all normal"}, PermissionLevel.LEVEL_3
    
    def _generate_reasoning(self, role: str, action_payload: dict):
        """生成智能体推理"""
        action = action_payload.get("action", "")
        reasonings = {
            "police": [
                "检测到人群聚集，建议疏散确保安全",
                "交通拥堵，需要管制以确保救援通道",
                "区域治安状况正常，继续巡逻"
            ],
            "utility": [
                "为防止触电，建议切断该区域电力",
                "基础设施损坏，需要立即修复",
                "水电煤气状况稳定"
            ],
            "warehouse": [
                "灾区需要更多物资，建议调配",
                "库存盘点完成，物资充足",
                "准备向医疗中心提供补给"
            ],
            "transport": [
                "运输任务紧急，需要额外车辆",
                "道路不通，需要变更路线",
                "准备执行常规运输任务"
            ],
            "medical": ["伤员太多，建议扩大疏散范围", "可以继续在现场救治"],
            "fire": ["火灾扩散快，需要撤离周边居民", "火势可控，继续灭火作业"],
            "eoc": ["分析全局态势，提供建议"]
        }
        
        return random.choice(reasonings.get(role, ["分析当前情况"]))
    
    async def register_client(self, websocket):
        """注册新客户端"""
        self.clients.add(websocket)
        logger.info(f"新客户端连接，当前连接数: {len(self.clients)}")
        await websocket.send(json.dumps({
            "type": "state",
            "data": self.current_state
        }))
    
    async def unregister_client(self, websocket):
        """注销客户端"""
        self.clients.discard(websocket)
        logger.info(f"客户端断开，当前连接数: {len(self.clients)}")
    
    async def broadcast_state(self):
        """向所有客户端广播当前状态"""
        if not self.clients:
            return
        
        message = json.dumps({
            "type": "state",
            "data": self.current_state
        })
        
        disconnected_clients = set()
        for client in self.clients:
            try:
                await client.send(message)
            except Exception as e:
                logger.error(f"发送消息失败: {e}")
                disconnected_clients.add(client)
        
        for client in disconnected_clients:
            await self.unregister_client(client)
    
    async def handle_client(self, websocket, path):
        """处理客户端连接"""
        await self.register_client(websocket)
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    await self._process_message(data)
                except json.JSONDecodeError:
                    logger.error(f"无效的 JSON 消息: {message}")
                except Exception as e:
                    logger.error(f"处理消息出错: {e}")
        finally:
            await self.unregister_client(websocket)
    
    async def _process_message(self, data: Dict[str, Any]):
        """处理来自前端的消息"""
        msg_type = data.get("type")
        
        if msg_type == "command":
            command = data.get("command")
            logger.info(f"收到命令: {command}")
            
            if command == "play":
                self.is_running = True
            elif command == "pause":
                self.is_running = False
            elif command == "reset":
                self.tick = 0
                self.current_state = self._get_initial_state()
                self.negotiation_sessions = {}
                self.action_tracker = ActionTracker()
                await self.broadcast_state()
        
        elif msg_type == "human_decision":
            card_id = data.get("card_id")
            decision_str = data.get("decision")
            feedback = data.get("feedback")
            
            try:
                decision = DecisionStatus(decision_str)
                await self.hitl_gateway.human_decision(card_id, decision, feedback)
                logger.info(f"人类决策: {card_id} - {decision_str}")
                await self.broadcast_state()
            except Exception as e:
                logger.error(f"处理人类决策错误: {e}")
        
        elif msg_type == "cancel_action":
            # 取消待执行的动作
            action_id = data.get("action_id")
            reason = data.get("reason", "No reason provided")
            cancelled = self.action_tracker.cancel_action(action_id, reason)
            
            if cancelled:
                logger.info(f"动作已取消: {action_id}")
                self.current_state["events"].insert(0, {
                    "id": len(self.current_state["events"]) + 1,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "action_cancelled",
                    "message": f"动作 {action_id} 已取消: {reason}",
                    "tick": self.tick
                })
                await self.broadcast_state()
        
        elif msg_type == "modify_action":
            # 修改待执行的动作
            action_id = data.get("action_id")
            new_payload = data.get("new_payload")
            reason = data.get("reason", "No reason provided")
            
            modified = self.action_tracker.modify_action(action_id, new_payload, reason)
            
            if modified:
                logger.info(f"动作已修改: {action_id}")
                self.current_state["events"].insert(0, {
                    "id": len(self.current_state["events"]) + 1,
                    "time": datetime.now().strftime("%H:%M:%S"),
                    "type": "action_modified",
                    "message": f"动作 {action_id} 已修改",
                    "tick": self.tick
                })
                await self.broadcast_state()
        
        elif msg_type == "resolve_conflict":
            # 解决冲突
            session_id = data.get("session_id")
            resolution = data.get("resolution")
            
            if session_id in self.negotiation_sessions:
                session = self.negotiation_sessions[session_id]
                if session.status == NegotiationStatus.ESCALATED:
                    session.status = NegotiationStatus.SUCCESS
                    session.escalation_note = f"Resolved by human: {resolution}"
                    logger.info(f"冲突已解决: {session_id}")
                    self._update_negotiations_state()
                    await self.broadcast_state()
    
    async def simulation_loop(self):
        """仿真循环"""
        while True:
            await asyncio.sleep(0.5)
            
            await self.hitl_gateway.check_timeouts()
            
            if self.is_running:
                self._update_state()
                await self.broadcast_state()
    
    async def run(self):
        """运行服务器"""
        logger.info(f"启动 CrisisNet WebSocket 服务器: ws://{self.host}:{self.port}")
        logger.info(f"✓ 可信校验层已初始化")
        logger.info(f"✓ 人机协同网关已初始化")
        logger.info(f"✓ 协商协议系统已初始化")
        logger.info(f"✓ 动作追踪与回滚系统已初始化")
        logger.info(f"✓ 智能体配置: Police, Utility, Warehouse, Transport, Fire, Medical, EOC, PublicInfo")
        
        asyncio.create_task(self.simulation_loop())
        
        server = await websockets.serve(self.handle_client, self.host, self.port)
        await server.wait_closed()


def main():
    config = Config()
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    logger.add("logs/web_server.log", rotation="500 MB", level="INFO")
    server = CrisisNetWebSocketServer(config)
    
    try:
        asyncio.run(server.run())
    except KeyboardInterrupt:
        logger.info("服务器已停止")


if __name__ == "__main__":
    main()
