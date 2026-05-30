import json
import sqlite3
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path
from loguru import logger
from crisisnet_common import AgentRole


class DecisionRecord:
    def __init__(
        self,
        decision_id: str,
        agent_role: str,
        tick: int,
        decision: Dict[str, Any],
        reasoning: str,
        observation: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        mode: str = "llm",
        approved: bool = False,
        approved_by: Optional[str] = None,
        approved_at: Optional[datetime] = None,
        created_at: Optional[datetime] = None
    ):
        self.decision_id = decision_id
        self.agent_role = agent_role
        self.tick = tick
        self.decision = decision
        self.reasoning = reasoning
        self.observation = observation or {}
        self.context = context or {}
        self.mode = mode
        self.approved = approved
        self.approved_by = approved_by
        self.approved_at = approved_at
        self.created_at = created_at or datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "agent_role": self.agent_role,
            "tick": self.tick,
            "decision": json.dumps(self.decision, ensure_ascii=False),
            "reasoning": self.reasoning,
            "observation": json.dumps(self.observation, ensure_ascii=False),
            "context": json.dumps(self.context, ensure_ascii=False),
            "mode": self.mode,
            "approved": 1 if self.approved else 0,
            "approved_by": self.approved_by,
            "approved_at": self.approved_at.isoformat() if self.approved_at else None,
            "created_at": self.created_at.isoformat()
        }

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> "DecisionRecord":
        return cls(
            decision_id=row["decision_id"],
            agent_role=row["agent_role"],
            tick=row["tick"],
            decision=json.loads(row["decision"]) if row["decision"] else {},
            reasoning=row["reasoning"],
            observation=json.loads(row["observation"]) if row["observation"] else {},
            context=json.loads(row["context"]) if row["context"] else {},
            mode=row["mode"],
            approved=bool(row["approved"]),
            approved_by=row["approved_by"],
            approved_at=datetime.fromisoformat(row["approved_at"]) if row["approved_at"] else None,
            created_at=datetime.fromisoformat(row["created_at"])
        )


class DecisionAuditStore:
    def __init__(self, db_path: str = "data/decisions.db"):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS decisions (
                decision_id TEXT PRIMARY KEY,
                agent_role TEXT NOT NULL,
                tick INTEGER NOT NULL,
                decision TEXT NOT NULL,
                reasoning TEXT NOT NULL,
                observation TEXT,
                context TEXT,
                mode TEXT NOT NULL,
                approved INTEGER DEFAULT 0,
                approved_by TEXT,
                approved_at TEXT,
                created_at TEXT NOT NULL
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_agent_role ON decisions(agent_role)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_tick ON decisions(tick)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_created_at ON decisions(created_at)
        ''')
        
        conn.commit()
        conn.close()
        logger.info(f"Decision audit store initialized at {self.db_path}")

    def record_decision(
        self,
        agent_role: str,
        tick: int,
        decision: Dict[str, Any],
        reasoning: str,
        observation: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        mode: str = "llm"
    ) -> str:
        decision_id = f"DEC_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        record = DecisionRecord(
            decision_id=decision_id,
            agent_role=agent_role,
            tick=tick,
            decision=decision,
            reasoning=reasoning,
            observation=observation,
            context=context,
            mode=mode
        )
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO decisions (
                decision_id, agent_role, tick, decision, reasoning, observation, context, mode,
                approved, approved_by, approved_at, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            record.decision_id,
            record.agent_role,
            record.tick,
            record.decision,
            record.reasoning,
            json.dumps(record.observation, ensure_ascii=False),
            json.dumps(record.context, ensure_ascii=False),
            record.mode,
            0,
            None,
            None,
            record.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        logger.debug(f"Recorded decision: {decision_id} for {agent_role}")
        return decision_id

    def approve_decision(
        self,
        decision_id: str,
        approved_by: str = "human"
    ) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE decisions
            SET approved = 1, approved_by = ?, approved_at = ?
            WHERE decision_id = ?
        ''', (approved_by, datetime.now().isoformat(), decision_id))
        
        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        logger.info(f"Decision {decision_id} approved by {approved_by}")
        return updated

    def reject_decision(self, decision_id: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            DELETE FROM decisions WHERE decision_id = ?
        ''', (decision_id,))
        
        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        logger.info(f"Decision {decision_id} rejected")
        return deleted

    def get_decision(self, decision_id: str) -> Optional[DecisionRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT * FROM decisions WHERE decision_id = ?
        ''', (decision_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return DecisionRecord.from_row(dict(row))
        return None

    def search_decisions(
        self,
        agent_role: Optional[str] = None,
        tick_min: Optional[int] = None,
        tick_max: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        keyword: Optional[str] = None,
        mode: Optional[str] = None,
        approved: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[DecisionRecord]:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        query = "SELECT * FROM decisions WHERE 1=1"
        params = []
        
        if agent_role:
            query += " AND agent_role = ?"
            params.append(agent_role)
        
        if tick_min is not None:
            query += " AND tick >= ?"
            params.append(tick_min)
        
        if tick_max is not None:
            query += " AND tick <= ?"
            params.append(tick_max)
        
        if start_date:
            query += " AND created_at >= ?"
            params.append(start_date.isoformat())
        
        if end_date:
            query += " AND created_at <= ?"
            params.append(end_date.isoformat())
        
        if mode:
            query += " AND mode = ?"
            params.append(mode)
        
        if approved is not None:
            query += " AND approved = ?"
            params.append(1 if approved else 0)
        
        if keyword:
            query += " AND (reasoning LIKE ? OR decision LIKE ?)"
            keyword_pattern = f"%{keyword}%"
            params.extend([keyword_pattern, keyword_pattern])
        
        query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        return [DecisionRecord.from_row(dict(row)) for row in rows]

    def get_pending_approvals(self) -> List[DecisionRecord]:
        return self.search_decisions(approved=False)

    def get_stats(self) -> Dict[str, Any]:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM decisions")
        total = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM decisions WHERE approved = 1")
        approved = cursor.fetchone()[0]
        
        cursor.execute("SELECT agent_role, COUNT(*) FROM decisions GROUP BY agent_role")
        by_role = dict(cursor.fetchall())
        
        cursor.execute("SELECT mode, COUNT(*) FROM decisions GROUP BY mode")
        by_mode = dict(cursor.fetchall())
        
        conn.close()
        
        return {
            "total_decisions": total,
            "approved_decisions": approved,
            "pending_decisions": total - approved,
            "by_agent_role": by_role,
            "by_mode": by_mode
        }
