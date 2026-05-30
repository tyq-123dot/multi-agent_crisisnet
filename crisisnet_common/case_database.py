import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger
import chromadb
from chromadb.utils import embedding_functions
from pydantic import BaseModel, Field


class DisasterCase(BaseModel):
    case_id: str
    disaster_type: str
    location: str
    timestamp: datetime
    description: str
    actions_taken: List[Dict[str, Any]] = Field(default_factory=list)
    outcomes: Dict[str, Any] = Field(default_factory=dict)
    key_observations: List[str] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)


class CaseRetrievalResult(BaseModel):
    case: DisasterCase
    similarity_score: float
    relevance_explanation: str


class CaseDatabase:
    def __init__(self, persist_directory: str = "./case_db"):
        self.persist_directory = persist_directory
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="paraphrase-multilingual-MiniLM-L12-v2"
        )
        self.collection = self.client.get_or_create_collection(
            name="disaster_cases",
            embedding_function=self.ef,
            metadata={"description": "Historical disaster response cases"}
        )
        logger.info(f"CaseDatabase initialized at {persist_directory}")

    async def add_case(self, case: DisasterCase) -> str:
        """添加历史灾例到数据库"""
        case_dict = case.model_dump()
        case_dict["timestamp"] = case.timestamp.isoformat()
        
        document = self._build_case_document(case)
        metadata = {
            "case_id": case.case_id,
            "disaster_type": case.disaster_type,
            "location": case.location,
            "timestamp": case.timestamp.isoformat()
        }
        
        self.collection.add(
            ids=[case.case_id],
            documents=[document],
            metadatas=[metadata]
        )
        logger.info(f"Case added: {case.case_id}")
        return case.case_id

    async def retrieve_similar_cases(
        self,
        query: str,
        disaster_type: Optional[str] = None,
        top_k: int = 3
    ) -> List[CaseRetrievalResult]:
        """检索相似案例"""
        filter_dict = {}
        if disaster_type:
            filter_dict["disaster_type"] = disaster_type
        
        results = self.collection.query(
            query_texts=[query],
            n_results=top_k,
            where=filter_dict if filter_dict else None
        )
        
        retrieved_cases = []
        for i, doc_id in enumerate(results["ids"][0]):
            metadata = results["metadatas"][0][i]
            document = results["documents"][0][i]
            distance = results["distances"][0][i]
            
            similarity_score = 1.0 - distance
            case = await self._get_case_by_id(metadata["case_id"])
            
            if case:
                retrieved_cases.append(CaseRetrievalResult(
                    case=case,
                    similarity_score=similarity_score,
                    relevance_explanation=f"与当前场景相似度: {similarity_score:.2f}"
                ))
        
        return retrieved_cases

    async def _get_case_by_id(self, case_id: str) -> Optional[DisasterCase]:
        """根据ID获取完整案例"""
        try:
            result = self.collection.get(ids=[case_id])
            if result["metadatas"]:
                metadata = result["metadatas"][0]
                return DisasterCase(
                    case_id=metadata["case_id"],
                    disaster_type=metadata["disaster_type"],
                    location=metadata["location"],
                    timestamp=datetime.fromisoformat(metadata["timestamp"]),
                    description=result["documents"][0].split("=== Key Observations ===")[0].strip(),
                    actions_taken=[],
                    outcomes={},
                    key_observations=[],
                    lessons_learned=[]
                )
        except Exception as e:
            logger.error(f"Failed to get case {case_id}: {e}")
        return None

    def _build_case_document(self, case: DisasterCase) -> str:
        """构建用于嵌入的文档"""
        doc_parts = [
            f"灾害类型: {case.disaster_type}",
            f"地点: {case.location}",
            f"描述: {case.description}",
            "",
            "=== Key Observations ===",
            *case.key_observations,
            "",
            "=== Actions Taken ===",
            *[json.dumps(action, ensure_ascii=False) for action in case.actions_taken],
            "",
            "=== Outcomes ===",
            json.dumps(case.outcomes, ensure_ascii=False),
            "",
            "=== Lessons Learned ===",
            *case.lessons_learned
        ]
        return "\n".join(doc_parts)

    def build_few_shot_prompt(self, cases: List[CaseRetrievalResult]) -> str:
        """构建 Few-shot 提示词"""
        if not cases:
            return ""
        
        prompt_parts = ["\n=== 历史案例参考 ==="]
        for i, result in enumerate(cases, 1):
            case = result.case
            prompt_parts.extend([
                f"\n案例 {i} (相似度: {result.similarity_score:.2f}):",
                f"灾害类型: {case.disaster_type}",
                f"地点: {case.location}",
                f"描述: {case.description}"
            ])
            if case.key_observations:
                prompt_parts.append("关键观察: " + "; ".join(case.key_observations))
            if case.actions_taken:
                prompt_parts.append("采取的行动:")
                for action in case.actions_taken[:3]:
                    prompt_parts.append(f"  - {json.dumps(action, ensure_ascii=False)}")
            if case.lessons_learned:
                prompt_parts.append("经验教训: " + "; ".join(case.lessons_learned))
        
        prompt_parts.append("\n请参考以上案例进行决策。")
        return "\n".join(prompt_parts)

    async def initialize_sample_cases(self):
        """初始化一些示例案例"""
        sample_cases = [
            DisasterCase(
                case_id="case_001",
                disaster_type="地震",
                location="zone_05",
                timestamp=datetime(2024, 1, 15),
                description="中等强度地震，zone_05 建筑受损，有人员被困",
                key_observations=["建筑结构受损严重", "道路中断", "通信不畅"],
                actions_taken=[
                    {"agent": "fire_rescue", "action": "deploy_team", "zone": "zone_05"},
                    {"agent": "medical", "action": "send_ambulance", "zone": "zone_05"},
                    {"agent": "logistics", "action": "deliver_supplies", "zone": "zone_05"}
                ],
                outcomes={"rescued": 15, "deaths": 2, "response_time": "45分钟"},
                lessons_learned=[
                    "优先确保道路畅通",
                    "需要协调多个部门同步行动",
                    "通讯保障至关重要"
                ]
            ),
            DisasterCase(
                case_id="case_002",
                disaster_type="洪水",
                location="zone_02",
                timestamp=datetime(2024, 3, 22),
                description="暴雨引发洪水，zone_02 受淹严重",
                key_observations=["水位快速上升", "低洼地区受困", "电力中断"],
                actions_taken=[
                    {"agent": "fire_rescue", "action": "water_rescue", "zone": "zone_02"},
                    {"agent": "logistics", "action": "send_boats", "zone": "zone_02"},
                    {"agent": "public_info", "action": "evacuation_warning", "zone": "zone_02"}
                ],
                outcomes={"rescued": 25, "safe_evacuation": 120},
                lessons_learned=[
                    "及早发布撤离警告",
                    "水上救援资源需要提前部署",
                    "沙袋等防洪物资储备很重要"
                ]
            ),
            DisasterCase(
                case_id="case_003",
                disaster_type="火灾",
                location="zone_08",
                timestamp=datetime(2024, 5, 10),
                description="工业区火灾，有化学品泄漏风险",
                key_observations=["火势蔓延快", "有有毒气体", "周边居民需要撤离"],
                actions_taken=[
                    {"agent": "fire_rescue", "action": "firefighting", "zone": "zone_08"},
                    {"agent": "eoc", "action": "establish_safety_perimeter", "zone": "zone_08"},
                    {"agent": "medical", "action": "setup_decontamination", "zone": "zone_08"}
                ],
                outcomes={"contained": "2小时后", "injuries": 8},
                lessons_learned=[
                    "建立安全隔离区是首要任务",
                    "需要专业的防化装备",
                    "与环保部门协调很重要"
                ]
            )
        ]
        
        for case in sample_cases:
            await self.add_case(case)
        
        logger.info(f"Initialized {len(sample_cases)} sample cases")
