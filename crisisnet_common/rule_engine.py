from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from loguru import logger
from crisisnet_common import AgentRole, WorldState, ResourceType


class DecisionMode(Enum):
    LLM = "llm"
    RULE = "rule"
    FALLBACK_LLM = "fallback_llm"
    HYBRID = "hybrid"


class RulePriority(Enum):
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3


class DecisionRule:
    def __init__(
        self,
        name: str,
        description: str,
        priority: RulePriority,
        condition: Callable[[Dict[str, Any]], bool],
        action: Callable[[Dict[str, Any]], Dict[str, Any]],
        applicable_roles: Optional[List[AgentRole]] = None
    ):
        self.name = name
        self.description = description
        self.priority = priority
        self.condition = condition
        self.action = action
        self.applicable_roles = applicable_roles

    def is_applicable(self, role: AgentRole, context: Dict[str, Any]) -> bool:
        if self.applicable_roles and role not in self.applicable_roles:
            return False
        return self.condition(context)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        return self.action(context)


class RuleEngine:
    def __init__(self):
        self.rules: List[DecisionRule] = []
        self._init_default_rules()

    def _init_default_rules(self):
        self._init_fire_rules()
        self._init_medical_rules()
        self._init_logistics_rules()
        self._init_eoc_rules()
        self._init_public_info_rules()

    def _init_fire_rules(self):
        self.add_rule(DecisionRule(
            name="fire_priority_high_intensity",
            description="当区域火灾强度>0.7时，优先灭火",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: self._check_zone_intensity(ctx, 0.7),
            action=lambda ctx: self._fire_fighting_action(ctx),
            applicable_roles=[AgentRole.FIRE_RESCUE]
        ))

        self.add_rule(DecisionRule(
            name="fire_trapped_persons",
            description="当有被困人员时，优先救援",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: self._check_trapped_persons(ctx, 1),
            action=lambda ctx: self._rescue_action(ctx),
            applicable_roles=[AgentRole.FIRE_RESCUE]
        ))

        self.add_rule(DecisionRule(
            name="fire_patrol_medium_intensity",
            description="中等强度区域巡逻",
            priority=RulePriority.MEDIUM,
            condition=lambda ctx: self._check_zone_intensity(ctx, 0.3),
            action=lambda ctx: self._patrol_action(ctx),
            applicable_roles=[AgentRole.FIRE_RESCUE]
        ))

    def _init_medical_rules(self):
        self.add_rule(DecisionRule(
            name="medical_high_casualties",
            description="伤亡>10时优先医疗响应",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: self._check_casualties(ctx, 10),
            action=lambda ctx: self._medical_response_action(ctx),
            applicable_roles=[AgentRole.MEDICAL]
        ))

        self.add_rule(DecisionRule(
            name="medical_ambulance_deploy",
            description="有伤亡时部署救护车",
            priority=RulePriority.HIGH,
            condition=lambda ctx: self._check_casualties(ctx, 1),
            action=lambda ctx: self._ambulance_action(ctx),
            applicable_roles=[AgentRole.MEDICAL]
        ))

    def _init_logistics_rules(self):
        self.add_rule(DecisionRule(
            name="logistics_priority_zones",
            description="按优先级配送物资",
            priority=RulePriority.HIGH,
            condition=lambda ctx: self._has_disaster_zones(ctx),
            action=lambda ctx: self._logistics_delivery_action(ctx),
            applicable_roles=[AgentRole.LOGISTICS]
        ))

    def _init_eoc_rules(self):
        self.add_rule(DecisionRule(
            name="eoc_set_priority_zones",
            description="设置区域优先级",
            priority=RulePriority.CRITICAL,
            condition=lambda ctx: self._has_multiple_zones(ctx),
            action=lambda ctx: self._eoc_priority_action(ctx),
            applicable_roles=[AgentRole.EOC]
        ))

    def _init_public_info_rules(self):
        self.add_rule(DecisionRule(
            name="public_info_high_intensity_warning",
            description="高风险区域发布警告",
            priority=RulePriority.HIGH,
            condition=lambda ctx: self._check_zone_intensity(ctx, 0.5),
            action=lambda ctx: self._public_warning_action(ctx),
            applicable_roles=[AgentRole.PUBLIC_INFO]
        ))

    def add_rule(self, rule: DecisionRule):
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority.value)

    def _check_zone_intensity(self, context: Dict[str, Any], threshold: float) -> bool:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        for zone_id, zone in zones.items():
            if zone.get("disaster_intensity", 0) > threshold:
                return True
        return False

    def _check_trapped_persons(self, context: Dict[str, Any], threshold: int) -> bool:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        for zone_id, zone in zones.items():
            if zone.get("trapped_people", 0) > threshold:
                return True
        return False

    def _check_casualties(self, context: Dict[str, Any], threshold: int) -> bool:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        total = 0
        for zone_id, zone in zones.items():
            total += zone.get("casualties", 0)
        return total > threshold

    def _has_disaster_zones(self, context: Dict[str, Any]) -> bool:
        return self._check_zone_intensity(context, 0.1)

    def _has_multiple_zones(self, context: Dict[str, Any]) -> bool:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        count = 0
        for zone_id, zone in zones.items():
            if zone.get("disaster_intensity", 0) > 0.3:
                count += 1
        return count >= 2

    def _fire_fighting_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_highest_intensity_zone(context)
        return {
            "action": "deploy_team",
            "target_zone": target_zone,
            "resource_type": "water_pump",
            "reasoning": "规则引擎：检测到高风险区域，立即部署消防队灭火。"
        }

    def _rescue_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_zone_with_trapped(context)
        return {
            "action": "rescue_operation",
            "target_zone": target_zone,
            "resource_type": "helicopter",
            "reasoning": "规则引擎：检测到被困人员，立即启动救援行动。"
        }

    def _patrol_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_highest_intensity_zone(context)
        return {
            "action": "patrol",
            "target_zone": target_zone,
            "reasoning": "规则引擎：中等风险区域巡逻监控。"
        }

    def _medical_response_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_zone_with_most_casualties(context)
        return {
            "action": "deploy_medical_team",
            "target_zone": target_zone,
            "resource_type": "medkit",
            "reasoning": "规则引擎：检测到大量伤亡，紧急部署医疗团队。"
        }

    def _ambulance_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_zone_with_most_casualties(context)
        return {
            "action": "send_ambulance",
            "target_zone": target_zone,
            "resource_type": "ambulance",
            "reasoning": "规则引擎：有伤员需要转送，派遣救护车。"
        }

    def _logistics_delivery_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_highest_intensity_zone(context)
        return {
            "action": "deliver_supplies",
            "target_zone": target_zone,
            "supplies": ["food_rations", "medkits", "water_pumps"],
            "reasoning": "规则引擎：按区域优先级配送物资。"
        }

    def _eoc_priority_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        priorities = {}
        for zone_id, zone in zones.items():
            intensity = zone.get("disaster_intensity", 0)
            if intensity > 0:
                priorities[zone_id] = round(intensity, 2)
        
        return {
            "action": "set_priorities",
            "priority_zones": priorities,
            "reasoning": "规则引擎：根据灾害强度自动设置区域优先级。"
        }

    def _public_warning_action(self, context: Dict[str, Any]) -> Dict[str, Any]:
        target_zone = self._get_highest_intensity_zone(context)
        return {
            "action": "announce",
            "announcement": f"紧急警告：{target_zone}区域发现险情，请立即撤离！",
            "reasoning": "规则引擎：高风险区域发布公共警告。"
        }

    def _get_highest_intensity_zone(self, context: Dict[str, Any]) -> str:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        max_intensity = -1
        target_zone = "zone_01"
        for zone_id, zone in zones.items():
            intensity = zone.get("disaster_intensity", 0)
            if intensity > max_intensity:
                max_intensity = intensity
                target_zone = zone_id
        return target_zone

    def _get_zone_with_trapped(self, context: Dict[str, Any]) -> str:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        max_trapped = -1
        target_zone = "zone_01"
        for zone_id, zone in zones.items():
            trapped = zone.get("trapped_people", 0)
            if trapped > max_trapped:
                max_trapped = trapped
                target_zone = zone_id
        return target_zone

    def _get_zone_with_most_casualties(self, context: Dict[str, Any]) -> str:
        world_state = context.get("world_state", {})
        zones = world_state.get("zones", {})
        max_casualties = -1
        target_zone = "zone_01"
        for zone_id, zone in zones.items():
            casualties = zone.get("casualties", 0)
            if casualties > max_casualties:
                max_casualties = casualties
                target_zone = zone_id
        return target_zone

    def decide(
        self,
        role: AgentRole,
        observation: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        full_context = {**observation, **context}
        
        for rule in self.rules:
            if rule.is_applicable(role, full_context):
                logger.info(f"Rule engine triggered: {rule.name} for {role.value}")
                return rule.execute(full_context)
        
        logger.warning(f"No rules matched for {role.value}, returning default action")
        return {
            "action": "wait",
            "reasoning": "规则引擎：无匹配规则，等待状态更新。"
        }
