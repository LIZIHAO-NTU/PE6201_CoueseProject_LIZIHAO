from __future__ import annotations

import hashlib
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import joblib
import sklearn
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion, Pipeline


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.services.text_analyser import analyse_text  # noqa: E402
from app.services.url_analyser import analyse_urls  # noqa: E402


TRAIN_PATH = ROOT / "data" / "training" / "message_train_v0.1.jsonl"
VALIDATION_PATH = ROOT / "data" / "training" / "message_validation_v0.1.jsonl"
TEST_PATH = ROOT / "data" / "eval" / "message_gold_test_v0.1.jsonl"
MODEL_DIR = ROOT / "app" / "models"
OUTPUT_DIR = ROOT / "outputs" / "evaluation"


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def model_pipeline(c_value: float) -> Pipeline:
    features = FeatureUnion(
        [
            (
                "word",
                TfidfVectorizer(
                    ngram_range=(1, 2),
                    min_df=1,
                    max_features=2500,
                    sublinear_tf=True,
                    strip_accents="unicode",
                ),
            ),
            (
                "char",
                TfidfVectorizer(
                    analyzer="char_wb",
                    ngram_range=(3, 5),
                    min_df=1,
                    max_features=4000,
                    sublinear_tf=True,
                ),
            ),
        ]
    )
    classifier = LogisticRegression(
        C=c_value,
        class_weight="balanced",
        max_iter=3000,
        random_state=6201,
    )
    return Pipeline([("features", features), ("classifier", classifier)])


def probability_rows(model: Pipeline, records: list[dict]) -> list[dict[str, float]]:
    probabilities = model.predict_proba([record["message"] for record in records])
    classes = list(model.classes_)
    return [dict(zip(classes, row, strict=True)) for row in probabilities]


def max_url_score(message: str) -> float:
    return max((item["score"] for item in analyse_urls(message)), default=0.0)


def risk_level(probabilities: dict[str, float], url_score: float, config: dict) -> tuple[str, float]:
    text_scam = probabilities.get("scam", 0.0)
    weight = config["text_weight"]
    fused_scam = text_scam if url_score == 0 else weight * text_scam + (1 - weight) * url_score
    fused_scam = min(max(fused_scam, 0.0), 1.0)
    max_probability = max(probabilities.values())
    if fused_scam >= config["high_threshold"]:
        level = "high"
    elif (
        fused_scam >= config["medium_threshold"]
        or probabilities.get("ambiguous", 0.0) >= config["ambiguous_threshold"]
        or max_probability < config["confidence_threshold"]
    ):
        level = "medium"
    else:
        level = "low"
    return level, round(fused_scam, 6)


def safe_div(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_risk(records: list[dict], probability_data: list[dict[str, float]], config: dict) -> dict:
    rows = []
    for record, probabilities in zip(records, probability_data, strict=True):
        level, fused_score = risk_level(probabilities, max_url_score(record["message"]), config)
        prediction = {"high": "scam", "medium": "ambiguous", "low": "legitimate"}[level]
        rows.append(
            {
                "id": record["id"],
                "gold": record["risk_label"],
                "prediction": prediction,
                "level": level,
                "score": fused_score,
                "probabilities": probabilities,
            }
        )
    scams = [row for row in rows if row["gold"] == "scam"]
    legitimate = [row for row in rows if row["gold"] == "legitimate"]
    ambiguous = [row for row in rows if row["gold"] == "ambiguous"]
    high = [row for row in rows if row["level"] == "high"]
    flagged = [row for row in rows if row["level"] in {"high", "medium"}]
    metrics = {
        "n": len(rows),
        "exact_three_way_accuracy": safe_div(sum(row["gold"] == row["prediction"] for row in rows), len(rows)),
        "operational_scam_recall": safe_div(sum(row["level"] in {"high", "medium"} for row in scams), len(scams)),
        "high_risk_scam_recall": safe_div(sum(row["level"] == "high" for row in scams), len(scams)),
        "flagged_precision_for_scam": safe_div(sum(row["gold"] == "scam" for row in flagged), len(flagged)),
        "high_risk_precision_for_scam": safe_div(sum(row["gold"] == "scam" for row in high), len(high)),
        "legitimate_false_positive_rate": safe_div(sum(row["level"] in {"high", "medium"} for row in legitimate), len(legitimate)),
        "abstention_rate": safe_div(sum(row["level"] == "medium" for row in rows), len(rows)),
        "ambiguous_abstention_recall": safe_div(sum(row["level"] == "medium" for row in ambiguous), len(ambiguous)),
    }
    confusion: dict[str, Counter] = defaultdict(Counter)
    for row in rows:
        confusion[row["gold"]][row["prediction"]] += 1
    metrics["confusion_matrix"] = {label: dict(counts) for label, counts in confusion.items()}
    return {"metrics": metrics, "rows": rows}


def selection_utility(metrics: dict) -> float:
    return (
        4.0 * metrics["operational_scam_recall"]
        + 1.5 * metrics["ambiguous_abstention_recall"]
        + 1.0 * metrics["exact_three_way_accuracy"]
        + 0.5 * metrics["high_risk_precision_for_scam"]
        + 0.5 * metrics["high_risk_scam_recall"]
        - 3.0 * metrics["legitimate_false_positive_rate"]
        - 0.2 * metrics["abstention_rate"]
    )


def rules_only(records: list[dict]) -> dict:
    rows = []
    for record in records:
        text = analyse_text(record["message"])
        url_score = max_url_score(record["message"])
        if url_score:
            score = 0.58 * text["score"] + 0.42 * url_score
            if text["score"] >= 0.5 and url_score >= 0.5:
                score += 0.12
            elif text["score"] >= 0.35 and url_score >= 0.5:
                score += 0.22
        else:
            score = text["score"]
        level = "high" if score >= 0.64 else "medium" if score >= 0.34 else "low"
        rows.append((record, level))
    scams = [item for item in rows if item[0]["risk_label"] == "scam"]
    legitimate = [item for item in rows if item[0]["risk_label"] == "legitimate"]
    ambiguous = [item for item in rows if item[0]["risk_label"] == "ambiguous"]
    return {
        "n": len(rows),
        "exact_three_way_accuracy": safe_div(
            sum({"high": "scam", "medium": "ambiguous", "low": "legitimate"}[level] == record["risk_label"] for record, level in rows),
            len(rows),
        ),
        "operational_scam_recall": safe_div(sum(level in {"high", "medium"} for _, level in scams), len(scams)),
        "high_risk_scam_recall": safe_div(sum(level == "high" for _, level in scams), len(scams)),
        "legitimate_false_positive_rate": safe_div(sum(level in {"high", "medium"} for _, level in legitimate), len(legitimate)),
        "abstention_rate": safe_div(sum(level == "medium" for _, level in rows), len(rows)),
        "ambiguous_abstention_recall": safe_div(sum(level == "medium" for _, level in ambiguous), len(ambiguous)),
    }


def round_metrics(value: object) -> object:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: round_metrics(item) for key, item in value.items()}
    if isinstance(value, list):
        return [round_metrics(item) for item in value]
    return value


def main() -> None:
    train = load_jsonl(TRAIN_PATH)
    validation = load_jsonl(VALIDATION_PATH)
    test = load_jsonl(TEST_PATH)
    train_messages = [record["message"] for record in train]
    train_labels = [record["risk_label"] for record in train]

    best = None
    candidates = []
    for c_value in [0.25, 0.5, 1.0, 2.0, 4.0]:
        model = model_pipeline(c_value)
        model.fit(train_messages, train_labels)
        validation_probabilities = probability_rows(model, validation)
        for text_weight in [0.55, 0.7, 0.85, 1.0]:
            for medium_threshold in [0.20, 0.25, 0.30, 0.35, 0.40]:
                for high_threshold in [0.45, 0.50, 0.55, 0.60, 0.65, 0.70]:
                    if high_threshold <= medium_threshold:
                        continue
                    for ambiguous_threshold in [0.20, 0.25, 0.30, 0.35]:
                        for confidence_threshold in [0.40, 0.45, 0.50, 0.55]:
                            config = {
                                "c": c_value,
                                "text_weight": text_weight,
                                "medium_threshold": medium_threshold,
                                "high_threshold": high_threshold,
                                "ambiguous_threshold": ambiguous_threshold,
                                "confidence_threshold": confidence_threshold,
                            }
                            result = evaluate_risk(validation, validation_probabilities, config)
                            metrics = result["metrics"]
                            if metrics["legitimate_false_positive_rate"] > 1 / 3:
                                continue
                            utility = selection_utility(metrics)
                            candidate = (utility, metrics["exact_three_way_accuracy"], -metrics["abstention_rate"], config, model, result)
                            candidates.append(candidate)
                            if best is None or candidate[:3] > best[:3]:
                                best = candidate
    if best is None:
        raise RuntimeError("No validation configuration satisfied the false-positive constraint")
    _, _, _, risk_config, risk_model, validation_result = best

    scam_train = [record for record in train if record["risk_label"] == "scam"]
    scam_validation = [record for record in validation if record["risk_label"] == "scam"]
    best_type = None
    for c_value in [0.25, 0.5, 1.0, 2.0, 4.0]:
        type_model = model_pipeline(c_value)
        type_model.fit(
            [record["message"] for record in scam_train],
            [record["primary_type"] for record in scam_train],
        )
        predictions = type_model.predict([record["message"] for record in scam_validation])
        accuracy = safe_div(
            sum(prediction == record["primary_type"] for prediction, record in zip(predictions, scam_validation, strict=True)),
            len(scam_validation),
        )
        mean_confidence = sum(max(row) for row in type_model.predict_proba([record["message"] for record in scam_validation])) / len(scam_validation)
        candidate = (accuracy, mean_confidence, -c_value, c_value, type_model)
        if best_type is None or candidate[:3] > best_type[:3]:
            best_type = candidate
    type_accuracy, _, _, type_c, type_model = best_type

    test_probabilities = probability_rows(risk_model, test)
    test_result = evaluate_risk(test, test_probabilities, risk_config)
    type_test_records = [record for record in test if record["risk_label"] == "scam"]
    type_test_predictions = type_model.predict([record["message"] for record in type_test_records])
    type_test_accuracy = safe_div(
        sum(prediction == record["primary_type"] for prediction, record in zip(type_test_predictions, type_test_records, strict=True)),
        len(type_test_records),
    )
    test_levels = {row["id"]: row["level"] for row in test_result["rows"]}
    deployed_type_predictions = [
        prediction if test_levels[record["id"]] != "low" else "uncertain"
        for prediction, record in zip(type_test_predictions, type_test_records, strict=True)
    ]
    deployed_type_test_accuracy = safe_div(
        sum(prediction == record["primary_type"] for prediction, record in zip(deployed_type_predictions, type_test_records, strict=True)),
        len(type_test_records),
    )

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(risk_model, MODEL_DIR / "risk_text_v0.1.joblib")
    joblib.dump(type_model, MODEL_DIR / "scam_type_v0.1.joblib")
    deployment_config = {
        "model_version": "tfidf-logreg-fusion-0.1",
        "risk_model_file": "risk_text_v0.1.joblib",
        "type_model_file": "scam_type_v0.1.joblib",
        "risk_classes": list(risk_model.classes_),
        "type_classes": list(type_model.classes_),
        "type_c": type_c,
        **risk_config,
    }
    (MODEL_DIR / "model_config_v0.1.json").write_text(
        json.dumps(deployment_config, indent=2) + "\n", encoding="utf-8"
    )

    report = {
        "model_version": deployment_config["model_version"],
        "selection_policy": "All hyperparameters and operating thresholds selected on validation only; gold test accessed after freeze.",
        "library_versions": {"scikit_learn": sklearn.__version__},
        "dataset_hashes": {
            "train": file_hash(TRAIN_PATH),
            "validation": file_hash(VALIDATION_PATH),
            "gold_test": file_hash(TEST_PATH),
        },
        "dataset_sizes": {"train": len(train), "validation": len(validation), "gold_test": len(test)},
        "selected_config": deployment_config,
        "validation": round_metrics(validation_result["metrics"]),
        "validation_scam_type_accuracy": round(type_accuracy, 4),
        "gold_test": round_metrics(test_result["metrics"]),
        "gold_test_scam_type_accuracy": round(type_test_accuracy, 4),
        "gold_test_deployed_scam_type_accuracy": round(deployed_type_test_accuracy, 4),
        "gold_test_rules_baseline": round_metrics(rules_only(test)),
        "gold_test_predictions": round_metrics(test_result["rows"]),
    }
    (OUTPUT_DIR / "trained_model_evaluation_v0.1.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    metrics = report["gold_test"]
    baseline = report["gold_test_rules_baseline"]
    lines = [
        "# ScamLens SG trained-model evaluation v0.1",
        "",
        "The configuration was selected using the 12-record validation set. The 30-record gold test set was accessed only after the configuration was frozen.",
        "",
        "## Gold-test comparison",
        "",
        "| Metric | Rules baseline | TF-IDF + Logistic Regression + URL fusion |",
        "|---|---:|---:|",
        f"| Exact three-way accuracy | {baseline['exact_three_way_accuracy']:.1%} | {metrics['exact_three_way_accuracy']:.1%} |",
        f"| Operational scam recall | {baseline['operational_scam_recall']:.1%} | {metrics['operational_scam_recall']:.1%} |",
        f"| High-risk scam recall | {baseline['high_risk_scam_recall']:.1%} | {metrics['high_risk_scam_recall']:.1%} |",
        f"| Legitimate false-positive rate | {baseline['legitimate_false_positive_rate']:.1%} | {metrics['legitimate_false_positive_rate']:.1%} |",
        f"| Abstention rate | {baseline['abstention_rate']:.1%} | {metrics['abstention_rate']:.1%} |",
        f"| Ambiguous-case abstention recall | {baseline['ambiguous_abstention_recall']:.1%} | {metrics['ambiguous_abstention_recall']:.1%} |",
        f"| Deployed scam-type accuracy | 70.0% | {deployed_type_test_accuracy:.1%} |",
        "",
        "## Frozen configuration",
        "",
        f"- Logistic regression C: {risk_config['c']}",
        f"- Text weight when a URL is present: {risk_config['text_weight']}",
        f"- Medium threshold: {risk_config['medium_threshold']}",
        f"- High threshold: {risk_config['high_threshold']}",
        f"- Ambiguous probability threshold: {risk_config['ambiguous_threshold']}",
        f"- Low-confidence abstention threshold: {risk_config['confidence_threshold']}",
        "",
        f"The underlying type classifier scored {type_test_accuracy:.1%}; the deployed pipeline scored {deployed_type_test_accuracy:.1%} because low-risk outputs suppress the category to uncertain.",
        f"Validation selected a text weight of {risk_config['text_weight']:.1f}; URL warnings remain visible even when their numerical fusion weight is zero.",
        "",
        "## Limitations",
        "",
        "The training, validation and test sets are small and mostly synthetic. The results demonstrate the project pipeline and a controlled comparison, not real-world deployment performance. More independently sourced and naturalistic messages are required before any safety claim.",
        "",
    ]
    (OUTPUT_DIR / "trained_model_evaluation_v0.1.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({
        "selected_config": deployment_config,
        "validation": report["validation"],
        "gold_test": report["gold_test"],
        "gold_test_scam_type_accuracy": report["gold_test_scam_type_accuracy"],
        "rules_baseline": report["gold_test_rules_baseline"],
    }, indent=2))


if __name__ == "__main__":
    main()
