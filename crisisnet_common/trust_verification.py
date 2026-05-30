import json
import logging
from enum import Enum
from typing import Dict, Any, List, Tuple, Optional
from pydantic import BaseModel, Field
from datetime import datetime

logger = logging.getLogger(__name__)

class PermissionLevel(Enum):
    """智能体权限分级"""
    LEVEL_1 = 1  # 需人类批准：大规模疏散、征用私人车辆、切断电源
    LEVEL_2 = 2  # 自动执行但记录：物资调运、路线变更
    LEVEL_3 = 3  # 自动执行：一般预警、路况更新

class ActionType(Enum):
    """动作类型分类，用于区分关键/非关键动作"""
    CRITICAL = "critical"
    NON_CRITICAL = "non_critical"
    UNSAFE = "unsafe"

class VerificationStatus(Enum):
    """校验状态"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"

class VerificationResult(BaseModel):
    """校验结果"""
    status: VerificationStatus
    check_name: str
    message: str
    details: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)

class ActionSuggestion(BaseModel):
    """智能体提议的动作"""
    agent_role: str
    agent_id: str
    action_type: ActionType
    permission_level: PermissionLevel = PermissionLevel.LEVEL_3
    action_payload: Dict[str, Any]
    reasoning: str
    timestamp: datetime = Field(default_factory=datetime.now)

class AgentRole(Enum):
    """智能体角色定义"""
    EOC = "eoc"
    FIRE = "fire"
    MEDICAL = "medical"
    WAREHOUSE = "warehouse"  # 物资仓库管理
    TRANSPORT = "transport"  # 运输调度
    POLICE = "police"      # 新增：警察/交通管制
    UTILITY = "utility"    # 新增：公用设施抢修
    PUBLIC_INFO = "public_info"

class TrustVerificationLayer:
    """可信校验层"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.map_bounds = config.get("map_bounds", {
            "min_lat": 39.8, "max_lat": 40.0,
            "min_lng": 116.2, "max_lng": 116.6
        })
        self.safe_zones = set(config.get("safe_zones", ["zone_01", "zone_02", "zone_07", "zone_08", "zone_09"]))
        self.danger_zones = set(config.get("danger_zones", ["zone_04"]))
        self.verification_rules = self._init_rules()
        
        # 权限分级配置
        self.LEVEL_1_ACTIONS = {
            "mass_evacuate", "requisition_vehicle", "cut_power",
            "cut_gas", "cut_water", "emergency_declare"
        }
        self.LEVEL_2_ACTIONS = {
            "relocate_supplies", "reroute_ambulance",
            "reroute_truck", "restock_warehouse"
        }
        self.LEVEL_3_ACTIONS = {
            "announce", "update_traffic",
            "update_infrastructure",
            "status_report"
        }
    
    def _init_rules(self) -> List[Tuple[str, callable]]:
        """初始化校验规则"""
        return [
            ("permission_level", self._check_permission_level),
            ("coordinate_validity", self._check_coordinate),
            ("resource_boundary", self._check_resource_boundary),
            ("safety_constraint", self._check_safety_constraint),
            ("action_reasonability", self._check_action_reasonability)
        ]
    
    def determine_permission_level(self, suggestion: ActionSuggestion) -> PermissionLevel:
        """根据动作内容确定权限级别"""
        action = suggestion.action_payload.get("action", "")
        
        if action in self.LEVEL_1_ACTIONS:
            return PermissionLevel.LEVEL_1
        if "requisition" in action or "evacuate" in action:
            return PermissionLevel.LEVEL_1
        if action in self.LEVEL_2_ACTIONS:
            return PermissionLevel.LEVEL_2
        
        return PermissionLevel.LEVEL_3
    
    def _check_permission_level(
        self,
        suggestion: ActionSuggestion,
        world_state: Dict[str, Any],
        resource_pool: Dict[str, int]
    ) -> VerificationResult:
        """检查权限级别是否正确"""
        level = suggestion.permission_level
        
        level_descriptions = {
            PermissionLevel.LEVEL_1: "需人类批准（高风险）",
            PermissionLevel.LEVEL_2: "自动执行但记录（中风险）",
            PermissionLevel.LEVEL_3: "自动执行（低风险）"
        }
        
        return VerificationResult(
            status=VerificationStatus.PASSED,
            check_name="permission_level",
            message=f"权限级别: {level.name} - {level_descriptions[level]}",
            details={"level": level.value}
        )
    
    def verify_action(
        self, 
        suggestion: ActionSuggestion, 
        world_state: Dict[str, Any],
        resource_pool: Dict[str, int]
    ) -> Tuple[bool, List[VerificationResult], Optional[ActionSuggestion]]:
        """
        验证智能体提议的动作
        
        返回: (是否通过, 详细校验结果, 安全回退动作)
        """
        results = []
        all_passed = True
        
        for rule_name, rule_func in self.verification_rules:
            try:
                result = rule_func(suggestion, world_state, resource_pool)
                results.append(result)
                if result.status == VerificationStatus.FAILED:
                    all_passed = False
                elif result.status == VerificationStatus.WARNING:
                    logger.warning(f"警告: {result.message}")
            except Exception as e:
                logger.error(f"规则校验错误 {rule_name}: {e}")
                results.append(VerificationResult(
                    status=VerificationStatus.SKIPPED,
                    check_name=rule_name,
                    message=f"规则执行错误: {str(e)}"
                ))
        
        fallback = None
        if not all_passed:
            fallback = self._get_safe_fallback(suggestion)
        
        return all_passed, results, fallback
    
    def _check_coordinate(
        self, 
        suggestion: ActionSuggestion, 
        world_state: Dict[str, Any], 
        resource_pool: Dict[str, int]
    ) -> VerificationResult:
        """检查坐标是否在有效范围内"""
        payload = suggestion.action_payload
        if "target_zone" in payload:
            zone_id = payload["target_zone"]
            zones = world_state.get("zones", {})
            if zone_id not in zones:
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    check_name="coordinate_validity",
                    message=f"无效区域: {zone_id}",
                    details={"invalid_zone": zone_id}
                )
            return VerificationResult(
                status=VerificationStatus.PASSED,
                check_name="coordinate_validity",
                message=f"区域 {zone_id} 有效"
            )
        elif "position" in payload:
            pos = payload["position"]
            lat, lng = pos.get("lat"), pos.get("lng")
            if lat and lng:
                if (self.map_bounds["min_lat"] <= lat <= self.map_bounds["max_lat"] and
                    self.map_bounds["min_lng"] <= lng <= self.map_bounds["max_lng"]):
                    return VerificationResult(
                        status=VerificationStatus.PASSED,
                        check_name="coordinate_validity",
                        message=f"坐标有效: ({lat}, {lng})"
                    )
                return VerificationResult(
                    status=VerificationStatus.FAILED,
                    check_name="coordinate_validity",
                    message=f"坐标超出有效范围: ({lat}, {lng})",
                    details={"position": pos}
                )
        
        return VerificationResult(
            status=VerificationStatus.SKIPPED,
            check_name="coordinate_validity",
            message="不需要坐标校验"
        )
    
    def _check_resource_boundary(
        self, 
        suggestion: ActionSuggestion, 
        world_state: Dict[str, Any], 
        resource_pool: Dict[str, int]
    ) -> VerificationResult:
        """检查资源请求是否不超过全局库存"""
        payload = suggestion.action_payload
        if "resources" not in payload:
            return VerificationResult(
                status=VerificationStatus.SKIPPED,
                check_name="resource_boundary",
                message="无资源请求，跳过"
            )
        
        requested = payload["resources"]
        errors = []
        
        for res_type, amount in requested.items():
            available = resource_pool.get(res_type, 0)
            if amount > available:
                errors.append({
                    "resource": res_type,
                    "requested": amount,
                    "available": available
                })
        
        if errors:
            return VerificationResult(
                status=VerificationStatus.FAILED,
                check_name="resource_boundary",
                message=f"资源请求超界: {len(errors)} 个资源不足",
                details={"errors": errors}
            )
        
        return VerificationResult(
            status=VerificationStatus.PASSED,
            check_name="resource_boundary",
            message="资源请求在可用范围内"
        )
    
    def _check_safety_constraint(
        self, 
        suggestion: ActionSuggestion, 
        world_state: Dict[str, Any], 
        resource_pool: Dict[str, int]
    ) -> VerificationResult:
        """检查是否违反安全约束"""
        payload = suggestion.action_payload
        agent_role = suggestion.agent_role
        
        if agent_role in ["fire", "police", "utility"]:
            if "target_zone" in payload:
                target_zone = payload["target_zone"]
                if target_zone in self.danger_zones:
                    return VerificationResult(
                        status=VerificationStatus.FAILED,
                        check_name="safety_constraint",
                        message=f"需特殊授权才能进入危险区域: {target_zone}",
                        details={"zone": target_zone, "rule": "danger_zone"}
                    )
        
        return VerificationResult(
            status=VerificationStatus.PASSED,
            check_name="safety_constraint",
            message="符合安全约束"
        )
    
    def _check_action_reasonability(
        self, 
        suggestion: ActionSuggestion, 
        world_state: Dict[str, Any], 
        resource_pool: Dict[str, int]
    ) -> VerificationResult:
        """检查动作合理性"""
        action = suggestion.action_payload.get("action", "")
        
        valid_actions = [
            "move_to", "extinguish", "treat", 
            "deliver", "announce", "negotiate", 
            "request_support", "wait", "traffic_control", 
            "evacuate", "repair_utility", "manage_warehouse", 
            "transport", "report"
        ]
        
        if action and action not in valid_actions:
            return VerificationResult(
                status=VerificationStatus.WARNING,
                check_name="action_reasonability",
                message=f"未知动作类型: {action}",
                details={"action": action}
            )
        
        return VerificationResult(
            status=VerificationStatus.PASSED,
            check_name="action_reasonability",
            message="动作类型合理"
        )
    
    def _get_safe_fallback(self, suggestion: ActionSuggestion) -> ActionSuggestion:
        """获取安全回退动作"""
        return ActionSuggestion(
            agent_role=suggestion.agent_role,
            agent_id=suggestion.agent_id,
            action_type=ActionType.NON_CRITICAL,
            permission_level=PermissionLevel.LEVEL_3,
            action_payload={"action": "wait", "reason": "校验失败，执行安全回退动作"},
            reasoning="安全校验失败，执行原地待命"
        )
    
    def classify_action_criticality(self, suggestion: ActionSuggestion) -> ActionType:
        """
        分类动作是否为关键动作
        
        关键动作需要人工审核，非关键动作可以自动执行
        """
        if suggestion.permission_level == PermissionLevel.LEVEL_1:
            return ActionType.CRITICAL
        elif suggestion.permission_level == PermissionLevel.LEVEL_2:
            return ActionType.CRITICAL
        
        return ActionType.NON_CRITICAL
