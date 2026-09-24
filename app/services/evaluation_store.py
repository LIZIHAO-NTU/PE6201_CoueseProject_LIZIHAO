from __future__ import annotations

import csv
import io
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


class EvaluationStore:
    """Persistent, privacy-minimised evaluation and observability storage."""

    def __init__(self, database_path: str | Path, export_dir: str | Path | None = None) -> None:
        self.database_path = Path(database_path)
        self.export_dir = Path(export_dir) if export_dir else None

    def _connect(self) -> sqlite3.Connection:
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(self.database_path, timeout=30)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        connection.execute("PRAGMA busy_timeout = 30000")
        return connection

    def initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS assessment_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message_hash TEXT NOT NULL,
                    requested_mode TEXT NOT NULL,
                    used_mode TEXT NOT NULL,
                    model TEXT,
                    risk_level TEXT NOT NULL,
                    primary_type TEXT NOT NULL,
                    total_latency_ms REAL,
                    llm_latency_ms REAL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    llm_status TEXT,
                    fallback_reason TEXT,
                    model_version TEXT NOT NULL,
                    safety_policy_version TEXT NOT NULL,
                    retriever_version TEXT NOT NULL,
                    prompt_version TEXT,
                    clicked_link INTEGER NOT NULL DEFAULT 0,
                    shared_credentials INTEGER NOT NULL DEFAULT 0,
                    transferred_money INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS benchmark_runs (
                    run_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    completed_at TEXT,
                    status TEXT NOT NULL,
                    dataset_id TEXT NOT NULL,
                    case_count INTEGER NOT NULL,
                    variants_json TEXT NOT NULL,
                    progress_completed INTEGER NOT NULL DEFAULT 0,
                    progress_total INTEGER NOT NULL,
                    budget_cap_usd REAL NOT NULL DEFAULT 0,
                    estimated_max_cost_usd REAL NOT NULL DEFAULT 0,
                    actual_cost_usd REAL NOT NULL DEFAULT 0,
                    is_frozen INTEGER NOT NULL DEFAULT 0,
                    summary_json TEXT,
                    error_message TEXT
                );

                CREATE TABLE IF NOT EXISTS benchmark_results (
                    result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT NOT NULL REFERENCES benchmark_runs(run_id) ON DELETE CASCADE,
                    created_at TEXT NOT NULL,
                    case_id TEXT NOT NULL,
                    message_hash TEXT NOT NULL,
                    system_variant TEXT NOT NULL,
                    model TEXT,
                    gold_risk_label TEXT NOT NULL,
                    gold_primary_type TEXT NOT NULL,
                    predicted_risk_level TEXT NOT NULL,
                    predicted_primary_type TEXT NOT NULL,
                    exact_correct INTEGER NOT NULL,
                    operationally_flagged INTEGER NOT NULL,
                    type_correct INTEGER NOT NULL,
                    total_latency_ms REAL,
                    llm_latency_ms REAL,
                    prompt_tokens INTEGER NOT NULL DEFAULT 0,
                    completion_tokens INTEGER NOT NULL DEFAULT 0,
                    estimated_cost_usd REAL NOT NULL DEFAULT 0,
                    llm_status TEXT,
                    fallback_reason TEXT,
                    evidence_ids_json TEXT NOT NULL,
                    model_version TEXT NOT NULL,
                    safety_policy_version TEXT NOT NULL,
                    retriever_version TEXT NOT NULL,
                    prompt_version TEXT,
                    UNIQUE(run_id, case_id, system_variant)
                );

                CREATE INDEX IF NOT EXISTS idx_assessment_events_created
                    ON assessment_events(created_at);
                CREATE INDEX IF NOT EXISTS idx_benchmark_results_run_variant
                    ON benchmark_results(run_id, system_variant);
                """
            )
            connection.execute(
                """
                UPDATE benchmark_runs
                SET status = 'interrupted', completed_at = ?,
                    error_message = COALESCE(error_message, 'Application restarted before the benchmark completed')
                WHERE status = 'running'
                """,
                (_utc_now(),),
            )

    def record_assessment(self, *, source: str, message_hash: str, result: dict) -> None:
        llm = result.get("llm_analysis") or {}
        state = result.get("user_state") or {}
        performance = result.get("performance") or {}
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO assessment_events (
                    created_at, source, message_hash, requested_mode, used_mode, model,
                    risk_level, primary_type, total_latency_ms, llm_latency_ms,
                    prompt_tokens, completion_tokens, estimated_cost_usd, llm_status,
                    fallback_reason, model_version, safety_policy_version, retriever_version,
                    prompt_version, clicked_link, shared_credentials, transferred_money
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    _utc_now(),
                    source,
                    message_hash,
                    result["analysis_mode"]["requested"],
                    result["analysis_mode"]["used"],
                    llm.get("model"),
                    result["risk_level"],
                    result["primary_type"],
                    performance.get("total_latency_ms"),
                    llm.get("latency_ms"),
                    int(llm.get("prompt_tokens") or 0),
                    int(llm.get("completion_tokens") or 0),
                    float(llm.get("estimated_cost_usd") or 0),
                    llm.get("status"),
                    llm.get("fallback_reason"),
                    result["model_version"],
                    result["safety_policy_version"],
                    result["retriever_version"],
                    result.get("prompt_version"),
                    int(bool(state.get("clicked_link"))),
                    int(bool(state.get("shared_credentials"))),
                    int(bool(state.get("transferred_money"))),
                ),
            )

    def persistent_overview(self) -> dict:
        with self._connect() as connection:
            total = connection.execute(
                """
                SELECT COUNT(*) AS assessments,
                       SUM(CASE WHEN requested_mode = 'llm_enhanced' THEN 1 ELSE 0 END) AS llm_attempts,
                       SUM(CASE WHEN llm_status = 'fallback' THEN 1 ELSE 0 END) AS fallbacks,
                       COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                       AVG(total_latency_ms) AS average_latency_ms
                FROM assessment_events
                """
            ).fetchone()
            by_model = connection.execute(
                """
                SELECT COALESCE(model, 'local') AS model, COUNT(*) AS assessments,
                       SUM(CASE WHEN llm_status = 'success' THEN 1 ELSE 0 END) AS successes,
                       SUM(CASE WHEN llm_status = 'fallback' THEN 1 ELSE 0 END) AS fallbacks,
                       COALESCE(SUM(prompt_tokens + completion_tokens), 0) AS total_tokens,
                       COALESCE(SUM(estimated_cost_usd), 0) AS estimated_cost_usd,
                       AVG(COALESCE(llm_latency_ms, total_latency_ms)) AS average_latency_ms
                FROM assessment_events
                GROUP BY COALESCE(model, 'local')
                ORDER BY assessments DESC
                """
            ).fetchall()
        return {
            "assessments": int(total["assessments"] or 0),
            "llm_attempts": int(total["llm_attempts"] or 0),
            "fallbacks": int(total["fallbacks"] or 0),
            "total_tokens": int(total["total_tokens"] or 0),
            "estimated_cost_usd": round(float(total["estimated_cost_usd"] or 0), 6),
            "average_latency_ms": (
                round(float(total["average_latency_ms"]), 1)
                if total["average_latency_ms"] is not None
                else None
            ),
            "by_model": [
                {
                    "model": row["model"],
                    "assessments": int(row["assessments"] or 0),
                    "successes": int(row["successes"] or 0),
                    "fallbacks": int(row["fallbacks"] or 0),
                    "total_tokens": int(row["total_tokens"] or 0),
                    "estimated_cost_usd": round(float(row["estimated_cost_usd"] or 0), 6),
                    "average_latency_ms": (
                        round(float(row["average_latency_ms"]), 1)
                        if row["average_latency_ms"] is not None
                        else None
                    ),
                }
                for row in by_model
            ],
        }

    def create_benchmark(
        self,
        *,
        dataset_id: str,
        case_count: int,
        variants: list[str],
        budget_cap_usd: float,
        estimated_max_cost_usd: float,
    ) -> str:
        run_id = uuid4().hex[:12]
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO benchmark_runs (
                    run_id, created_at, status, dataset_id, case_count, variants_json,
                    progress_total, budget_cap_usd, estimated_max_cost_usd
                ) VALUES (?, ?, 'running', ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    _utc_now(),
                    dataset_id,
                    case_count,
                    _json(variants),
                    case_count * len(variants),
                    budget_cap_usd,
                    estimated_max_cost_usd,
                ),
            )
        return run_id

    def record_benchmark_result(self, *, run_id: str, row: dict) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO benchmark_results (
                    run_id, created_at, case_id, message_hash, system_variant, model,
                    gold_risk_label, gold_primary_type, predicted_risk_level,
                    predicted_primary_type, exact_correct, operationally_flagged,
                    type_correct, total_latency_ms, llm_latency_ms, prompt_tokens,
                    completion_tokens, estimated_cost_usd, llm_status, fallback_reason,
                    evidence_ids_json, model_version, safety_policy_version,
                    retriever_version, prompt_version
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    run_id,
                    _utc_now(),
                    row["case_id"],
                    row["message_hash"],
                    row["system_variant"],
                    row.get("model"),
                    row["gold_risk_label"],
                    row["gold_primary_type"],
                    row["predicted_risk_level"],
                    row["predicted_primary_type"],
                    int(row["exact_correct"]),
                    int(row["operationally_flagged"]),
                    int(row["type_correct"]),
                    row.get("total_latency_ms"),
                    row.get("llm_latency_ms"),
                    int(row.get("prompt_tokens") or 0),
                    int(row.get("completion_tokens") or 0),
                    float(row.get("estimated_cost_usd") or 0),
                    row.get("llm_status"),
                    row.get("fallback_reason"),
                    _json(row.get("evidence_ids", [])),
                    row["model_version"],
                    row["safety_policy_version"],
                    row["retriever_version"],
                    row.get("prompt_version"),
                ),
            )
            connection.execute(
                """
                UPDATE benchmark_runs
                SET progress_completed = progress_completed + 1,
                    actual_cost_usd = actual_cost_usd + ?
                WHERE run_id = ?
                """,
                (float(row.get("estimated_cost_usd") or 0), run_id),
            )

    def benchmark_results(self, run_id: str) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                "SELECT * FROM benchmark_results WHERE run_id = ? ORDER BY result_id",
                (run_id,),
            ).fetchall()
        return [self._decode_result(row) for row in rows]

    def complete_benchmark(self, *, run_id: str, summary: dict, status: str = "completed") -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE benchmark_runs
                SET status = ?, completed_at = ?, summary_json = ?
                WHERE run_id = ?
                """,
                (status, _utc_now(), _json(summary), run_id),
            )
        self.write_exports(run_id)

    def fail_benchmark(self, *, run_id: str, message: str) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                UPDATE benchmark_runs
                SET status = 'failed', completed_at = ?, error_message = ?
                WHERE run_id = ?
                """,
                (_utc_now(), message[:500], run_id),
            )

    def freeze_benchmark(self, run_id: str) -> bool:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT status FROM benchmark_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
            if row is None or row["status"] not in {"completed", "budget_stopped"}:
                return False
            connection.execute("UPDATE benchmark_runs SET is_frozen = 0")
            connection.execute(
                "UPDATE benchmark_runs SET is_frozen = 1 WHERE run_id = ?", (run_id,)
            )
        self.write_exports(run_id, frozen=True)
        return True

    def list_benchmarks(self, limit: int = 10) -> list[dict]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT * FROM benchmark_runs
                ORDER BY created_at DESC, run_id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [self._decode_run(row) for row in rows]

    def get_benchmark(self, run_id: str) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM benchmark_runs WHERE run_id = ?", (run_id,)
            ).fetchone()
        return self._decode_run(row) if row else None

    def latest_frozen_benchmark(self) -> dict | None:
        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT * FROM benchmark_runs
                WHERE is_frozen = 1
                ORDER BY completed_at DESC LIMIT 1
                """
            ).fetchone()
        return self._decode_run(row) if row else None

    def export_json(self, run_id: str) -> str | None:
        run = self.get_benchmark(run_id)
        if run is None:
            return None
        run["results"] = self.benchmark_results(run_id)
        return json.dumps(run, ensure_ascii=False, indent=2)

    def export_csv(self, run_id: str) -> str | None:
        if self.get_benchmark(run_id) is None:
            return None
        rows = self.benchmark_results(run_id)
        output = io.StringIO()
        fields = [
            "case_id", "message_hash", "system_variant", "model", "gold_risk_label",
            "gold_primary_type", "predicted_risk_level", "predicted_primary_type",
            "exact_correct", "operationally_flagged", "type_correct", "total_latency_ms",
            "llm_latency_ms", "prompt_tokens", "completion_tokens", "estimated_cost_usd",
            "llm_status", "fallback_reason", "evidence_ids", "model_version",
            "safety_policy_version", "retriever_version", "prompt_version",
        ]
        writer = csv.DictWriter(output, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "evidence_ids": "|".join(row["evidence_ids"])})
        return output.getvalue()

    def write_exports(self, run_id: str, *, frozen: bool = False) -> list[Path]:
        if self.export_dir is None:
            return []
        json_content = self.export_json(run_id)
        csv_content = self.export_csv(run_id)
        if json_content is None or csv_content is None:
            return []
        self.export_dir.mkdir(parents=True, exist_ok=True)
        paths = [
            self.export_dir / f"benchmark_{run_id}.json",
            self.export_dir / f"benchmark_{run_id}.csv",
        ]
        paths[0].write_text(json_content + "\n", encoding="utf-8")
        paths[1].write_text(csv_content, encoding="utf-8-sig")
        if frozen:
            frozen_json = self.export_dir / "frozen_benchmark.json"
            frozen_csv = self.export_dir / "frozen_benchmark.csv"
            frozen_json.write_text(json_content + "\n", encoding="utf-8")
            frozen_csv.write_text(csv_content, encoding="utf-8-sig")
            paths.extend([frozen_json, frozen_csv])
        return paths

    @staticmethod
    def _decode_run(row: sqlite3.Row) -> dict:
        value = dict(row)
        value["variants"] = json.loads(value.pop("variants_json"))
        summary_json = value.pop("summary_json")
        value["summary"] = json.loads(summary_json) if summary_json else None
        value["is_frozen"] = bool(value["is_frozen"])
        return value

    @staticmethod
    def _decode_result(row: sqlite3.Row) -> dict:
        value = dict(row)
        value.pop("result_id", None)
        value.pop("run_id", None)
        value.pop("created_at", None)
        value["evidence_ids"] = json.loads(value.pop("evidence_ids_json"))
        for key in ("exact_correct", "operationally_flagged", "type_correct"):
            value[key] = bool(value[key])
        return value


def message_digest(message: str, secret: str = "") -> str:
    from hashlib import sha256
    from hmac import new as hmac_new

    if secret:
        return hmac_new(secret.encode("utf-8"), message.encode("utf-8"), sha256).hexdigest()[:16]
    return sha256(message.encode("utf-8")).hexdigest()[:16]
