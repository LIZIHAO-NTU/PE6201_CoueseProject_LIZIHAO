from __future__ import annotations

import json
import sys
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.retriever import RETRIEVER_VERSION, retrieve_evidence  # noqa: E402


DATA_PATH = ROOT / "data" / "eval" / "retrieval_eval_v0.2.jsonl"
OUTPUT_DIR = ROOT / "outputs" / "evaluation"
COUNTERFACTUAL_TYPE = {
    "government_impersonation": "e_commerce",
    "investment": "job",
    "job": "government_impersonation",
    "e_commerce": "investment",
    "uncertain": "job",
}


def _load_cases() -> list[dict]:
    return [json.loads(line) for line in DATA_PATH.read_text(encoding="utf-8").splitlines() if line.strip()]


def evaluate() -> dict:
    cases = _load_cases()
    rows = []
    for case in cases:
        results = retrieve_evidence(
            case["query"],
            case["primary_type"],
            limit=3,
            user_state=case.get("user_state"),
        )
        ids = [item["id"] for item in results]
        expected = set(case["expected_top1_ids"])
        reciprocal_rank = next((1 / (rank + 1) for rank, item_id in enumerate(ids) if item_id in expected), 0.0)
        category_covered = any(case["required_scam_type"] in item["scam_types"] for item in results)
        required_action_stage = case.get("required_action_stage")
        action_stage_covered = not required_action_stage or any(
            required_action_stage in item["action_stages"] for item in results
        )
        provenance_complete = all(
            item.get("last_verified_date")
            and item.get("source_domain")
            and item.get("match_reasons")
            and urlparse(item["url"]).scheme == "https"
            for item in results
        )
        rows.append(
            {
                "id": case["id"],
                "primary_type": case["primary_type"],
                "top_ids": ids,
                "top1_acceptable": ids[0] in expected,
                "top3_expected_coverage": bool(expected.intersection(ids)),
                "top3_category_coverage": category_covered,
                "top3_action_stage_coverage": action_stage_covered,
                "has_required_action_stage": bool(required_action_stage),
                "reciprocal_rank": reciprocal_rank,
                "provenance_complete": provenance_complete,
            }
        )

    count = len(rows)
    stage_rows = [row for row in rows if row["has_required_action_stage"]]
    metrics = {
        "case_count": count,
        "top1_acceptable_accuracy": sum(row["top1_acceptable"] for row in rows) / count,
        "top3_expected_coverage": sum(row["top3_expected_coverage"] for row in rows) / count,
        "top3_category_coverage": sum(row["top3_category_coverage"] for row in rows) / count,
        "top3_action_stage_coverage": (
            sum(row["top3_action_stage_coverage"] for row in stage_rows) / len(stage_rows)
            if stage_rows
            else None
        ),
        "mean_reciprocal_rank": sum(row["reciprocal_rank"] for row in rows) / count,
        "provenance_completeness": sum(row["provenance_complete"] for row in rows) / count,
    }

    def type_sensitivity(mode: str) -> dict:
        top1_hits = 0
        top3_hits = 0
        for case in cases:
            supplied_type = "" if mode == "without_type" else COUNTERFACTUAL_TYPE[case["primary_type"]]
            result_ids = [
                item["id"]
                for item in retrieve_evidence(
                    case["query"],
                    supplied_type,
                    limit=3,
                    user_state=case.get("user_state"),
                )
            ]
            expected = set(case["expected_top1_ids"])
            top1_hits += result_ids[0] in expected
            top3_hits += bool(expected.intersection(result_ids))
        return {"top1_accuracy": top1_hits / count, "top3_coverage": top3_hits / count}

    return {
        "benchmark": "retrieval_eval_v0.2",
        "retriever_version": RETRIEVER_VERSION,
        "scope": "Designer-authored regression benchmark with the assessed scam type supplied to the retriever.",
        "metrics": metrics,
        "type_sensitivity": {
            "without_assessed_type": type_sensitivity("without_type"),
            "counterfactual_wrong_type": type_sensitivity("wrong_type"),
        },
        "rows": rows,
    }


def _markdown(report: dict) -> str:
    metrics = report["metrics"]
    sensitivity = report["type_sensitivity"]
    failures = [row for row in report["rows"] if not row["top1_acceptable"]]
    lines = [
        "# Retrieval evaluation v0.2",
        "",
        f"Retriever: `{report['retriever_version']}`",
        "",
        report["scope"],
        "",
        "| Metric | Result |",
        "|---|---:|",
        f"| Cases | {metrics['case_count']} |",
        f"| Acceptable top-1 accuracy | {metrics['top1_acceptable_accuracy']:.1%} |",
        f"| Expected document in top 3 | {metrics['top3_expected_coverage']:.1%} |",
        f"| Required category in top 3 | {metrics['top3_category_coverage']:.1%} |",
        f"| Required action stage in top 3 | {metrics['top3_action_stage_coverage']:.1%} |",
        f"| Mean reciprocal rank | {metrics['mean_reciprocal_rank']:.3f} |",
        f"| Provenance completeness | {metrics['provenance_completeness']:.1%} |",
        "",
        "## Assessed-type sensitivity",
        "",
        "| Retrieval condition | Top-1 | Top-3 |",
        "|---|---:|---:|",
        f"| Assessed type omitted | {sensitivity['without_assessed_type']['top1_accuracy']:.1%} | {sensitivity['without_assessed_type']['top3_coverage']:.1%} |",
        f"| Counterfactual wrong type supplied | {sensitivity['counterfactual_wrong_type']['top1_accuracy']:.1%} | {sensitivity['counterfactual_wrong_type']['top3_coverage']:.1%} |",
        "",
        "This benchmark is for deterministic regression testing. Because its cases and acceptance rules were authored during development, it is not independent evidence of real-world retrieval quality.",
        "",
        "## Top-1 failures",
        "",
    ]
    if failures:
        lines.extend(f"- `{row['id']}` returned `{row['top_ids'][0]}`." for row in failures)
    else:
        lines.append("None.")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    report = evaluate()
    (OUTPUT_DIR / "retrieval_evaluation_v0.2.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "retrieval_evaluation_v0.2.md").write_text(_markdown(report), encoding="utf-8")
    print(json.dumps(report["metrics"], indent=2))
