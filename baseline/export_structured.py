"""FontBench Structured Output Aggregator.

Consolidates model scorecards into a structured, multi-dimensional
benchmark dataset for visualization, Pareto analysis, and typographic slicing.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


def build_structured_benchmark(results_dir: str = "results") -> Dict[str, Any]:
    from baseline.reporting import DIMENSIONS, finite_nonnegative, metrics, read_report_json, scorecard_tasks

    models_output = []
    warnings = []
    for sc_file in sorted(Path(results_dir).glob("scorecard_*.json")):
        card = read_report_json(sc_file, warnings)
        if not card:
            continue
        try:
            tasks = scorecard_tasks(card, complete=True)
            if (not isinstance(card.get("model_name"), str) or not card["model_name"]
                    or any(not isinstance(task.get("target_canonical"), str) or not task["target_canonical"] for task in tasks)
                    or any(not finite_nonnegative(task.get("latency_sec")) for task in tasks)):
                raise ValueError("Missing model, font, or latency measurements")
        except ValueError as error:
            warnings.append(f"Excluded {sc_file.name}: {error}")
            continue
        model_key = card.get("model_id") or card["model_name"]
        scores = metrics(tasks)
        by_category = {}
        for category in sorted({task.get("category", "unknown") for task in tasks}):
            subset = [task for task in tasks if task.get("category", "unknown") == category]
            measured = metrics(subset)
            by_category[category] = {"accuracy": round(measured["category"] * 100, 1),
                                     "font_accuracy": round(measured["font"] * 100, 1),
                                     "composite": round(measured["composite"] * 100, 1), "total": len(subset)}
        breakdowns = {}
        for axis in ("weight", "modifier", "kerning", "line_height", "width_id"):
            breakdowns[axis] = {
                value: round(metrics([task for task in tasks if task.get(axis) == value])["composite"] * 100, 1)
                for value in sorted({task[axis] for task in tasks if isinstance(task.get(axis), str)})
            }
        per_font = []
        for font_name in sorted({task["target_canonical"] for task in tasks}):
            subset = [task for task in tasks if task["target_canonical"] == font_name]
            correct = sum(task["font_correct"] for task in subset)
            per_font.append({"font": font_name, "classification": subset[0].get("category"),
                             "category": subset[0].get("category"),
                             "accuracy": round(correct / len(subset) * 100, 1), "correct": correct, "total": len(subset),
                             "sample_predictions": [task.get("predicted_font", "") for task in subset[:3]]})
        pricing = card.get("pricing") if isinstance(card.get("pricing"), dict) else {}
        input_price, output_price = pricing.get("input_per_m"), pricing.get("output_per_m")
        input_price = input_price if finite_nonnegative(input_price) else None
        output_price = output_price if finite_nonnegative(output_price) else None
        cost = None
        if input_price is not None and output_price is not None and all(
                finite_nonnegative(task.get("input_tokens")) and finite_nonnegative(task.get("output_tokens"))
                and not task.get("unmetered_attempts", 0) for task in tasks):
            cost = round(sum(task["input_tokens"] * input_price + task["output_tokens"] * output_price for task in tasks) / 1_000_000, 4)
        models_output.append({
            "model_id": model_key, "model_name": card["model_name"],
            "display_name": card.get("display_name", model_key), "provider": card.get("provider"),
            "dataset_fingerprint": card["dataset_fingerprint"],
            "evaluation_protocol_fingerprint": card["evaluation_protocol_fingerprint"],
            "cohort_fingerprint": card["cohort_fingerprint"], "grading_version": card["grading_version"],
            "max_output_tokens": card.get("max_output_tokens"), "status": card["status"],
            "total_tasks": len(tasks), "expected_task_count": card["expected_task_count"],
            "evaluated_at": card.get("timestamp"), "overall_composite_score": scores["composite"] * 100,
            "overall_accuracy": round(scores["composite"] * 100, 1), "overall_exact_match": round(scores["exact"] * 100, 1),
            **{f"{key}_accuracy": round(scores[key] * 100, 1) for key in DIMENSIONS},
            "avg_latency_sec": sum(task["latency_sec"] for task in tasks) / len(tasks),
            "pricing": {"input_per_m": input_price, "output_per_m": output_price, "estimated_run_cost_usd": cost},
            "by_category": by_category, "by_weight": breakdowns["weight"], "by_modifier": breakdowns["modifier"],
            "by_spacing": {"kerning": breakdowns["kerning"], "line_height": breakdowns["line_height"]},
            "by_width": breakdowns["width_id"], "per_font": per_font, "notes": card.get("notes", ""), "tasks": tasks,
        })

    comparison_groups = {}
    for model in models_output:
        key = (model["dataset_fingerprint"], model["evaluation_protocol_fingerprint"], model["cohort_fingerprint"])
        comparison_groups.setdefault(key, []).append(model)
    for group in comparison_groups.values():
        for model in group:
            model["is_pareto_frontier"] = not any(
                other["overall_composite_score"] >= model["overall_composite_score"]
                and other["avg_latency_sec"] <= model["avg_latency_sec"]
                and (other["overall_composite_score"] > model["overall_composite_score"]
                     or other["avg_latency_sec"] < model["avg_latency_sec"])
                for other in group
            )
    models_output.sort(key=lambda model: (model["dataset_fingerprint"], model["cohort_fingerprint"], model["model_id"]))
    for model in models_output:
        model["overall_composite_score"] = round(model["overall_composite_score"], 1)
        model["avg_latency_sec"] = round(model["avg_latency_sec"], 2)
    font_names = sorted({task["target_canonical"] for model in models_output for task in model["tasks"]})
    dates = [model["evaluated_at"][:10] for model in models_output if isinstance(model["evaluated_at"], str)]
    return {
        "benchmark_id": "fontbench", "name": "FontBench", "version": "2.0.0",
        "description": "Measured visual typography identification across six attributes; comparisons require the same dataset, protocol, and completed inputs.",
        "eval_date": max(dates) if dates else None, "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_fonts": len(font_names),
        "total_tasks_per_model": models_output[0]["total_tasks"] if len(comparison_groups) == 1 else None,
        "taxonomies": {
            "categories": ["serif", "non-serif", "mono", "handwriting", "other"],
            "weights": ["thin", "regular", "bold", "black"],
            "modifiers": ["regular", "italic", "underline", "strikethrough", "small-caps"],
            "kerning": ["tight", "normal", "loose"], "line_height": ["tight", "normal", "loose"],
            "fonts": [{"name": name, "category": next(task.get("category") for model in models_output for task in model["tasks"] if task["target_canonical"] == name)} for name in font_names],
        },
        "models": models_output, "warnings": warnings,
        "comparison_groups": [{"dataset_fingerprint": key[0], "evaluation_protocol_fingerprint": key[1],
                               "cohort_fingerprint": key[2], "model_ids": [model["model_id"] for model in group]}
                              for key, group in comparison_groups.items()],
        "pareto_frontier": [model["model_id"] for model in models_output if model["is_pareto_frontier"]],
        "pareto_dimensions": {"maximize": "overall_composite_score", "minimize": "avg_latency_sec"},
    }


if __name__ == "__main__":
    benchmark_data = build_structured_benchmark("results")
    out_file = Path("results/fontbench_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"Generated structured benchmark summary at {out_file} ({len(benchmark_data['models'])} models)")
