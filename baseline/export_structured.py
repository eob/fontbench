"""FontBench Structured Output Aggregator.

Consolidates model scorecards into a structured, multi-dimensional
benchmark dataset for visualization, Pareto analysis, and typographic slicing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


FONT_METADATA: Dict[str, Dict[str, str]] = {
    "Arial": {"classification": "non-serif", "category": "sans-serif", "sub_category": "neo-grotesque", "origin": "Monotype (1982)"},
    "Helvetica": {"classification": "non-serif", "category": "sans-serif", "sub_category": "neo-grotesque", "origin": "Max Miedinger (1957)"},
    "Roboto": {"classification": "non-serif", "category": "sans-serif", "sub_category": "neo-grotesque", "origin": "Google / Christian Robertson (2011)"},
    "Inter": {"classification": "non-serif", "category": "sans-serif", "sub_category": "neo-grotesque", "origin": "Rasmus Andersson (2017)"},
    "Montserrat": {"classification": "non-serif", "category": "sans-serif", "sub_category": "geometric-sans", "origin": "Julieta Ulanovsky (2011)"},
    "Times New Roman": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "Stanley Morison (1931)"},
    "Georgia": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "Matthew Carter (1993)"},
    "Playfair Display": {"classification": "serif", "category": "serif", "sub_category": "didone-display", "origin": "Claus Eggers Sørensen (2011)"},
    "Courier New": {"classification": "non-serif", "category": "monospace", "sub_category": "monospaced-slab", "origin": "Howard Kettler / Adrian Frutiger (1955)"},
    "Comic Sans MS": {"classification": "non-serif", "category": "handwriting", "sub_category": "casual-script", "origin": "Vincent Connare (1994)"},
}

MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "gemini-3.5-flash-lite": {
        "display_name": "Gemini 3.5 Flash Lite",
        "provider": "Google",
        "family": "Gemini 3.5",
        "input_price_per_m": 0.075,
        "output_price_per_m": 0.30,
        "is_pareto_frontier": True,
        "notes": "Extreme inference speed (0.72s/task) with strong baseline accuracy (40.0%). 100% on script and monospace."
    },
    "gemini-3.5-flash": {
        "display_name": "Gemini 3.5 Flash",
        "provider": "Google",
        "family": "Gemini 3.5",
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "is_pareto_frontier": True,
        "notes": "Highest overall accuracy (60.0%). Perfect 100% on serif and monospace categories."
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "provider": "Google",
        "family": "Gemini 2.5",
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "is_pareto_frontier": False,
        "notes": "Dominated by 3.5 Flash Lite on latency and 3.5 Flash on accuracy. Exhibits strong Roboto mode-collapse."
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "provider": "Google",
        "family": "Gemini 2.5",
        "input_price_per_m": 1.25,
        "output_price_per_m": 5.00,
        "is_pareto_frontier": False,
        "notes": "Slowest and prone to severe overthinking on zero-shot font queries (predicts Inter for Arial/Helvetica, Didot/Minion for Times)."
    }
}


def build_structured_benchmark(results_dir: str = "results") -> Dict[str, Any]:
    res_path = Path(results_dir)
    scorecard_files = sorted(res_path.glob("scorecard_*.json"))
    
    models_output: List[Dict[str, Any]] = []

    for sc_file in [f for f in scorecard_files if "mock" not in f.name]:
        with open(sc_file, "r", encoding="utf-8") as f:
            sc_data = json.load(f)

        model_key = sc_data["model_name"]
        meta = MODEL_METADATA.get(model_key, {
            "display_name": model_key,
            "provider": "Google",
            "family": "Unknown",
            "input_price_per_m": 0.15,
            "output_price_per_m": 0.60,
            "is_pareto_frontier": False,
            "notes": ""
        })

        tasks = sc_data.get("tasks", [])
        
        # Calculate serif vs non-serif
        serif_tasks = [t for t in tasks if FONT_METADATA.get(t["target_canonical"], {}).get("classification") == "serif"]
        non_serif_tasks = [t for t in tasks if FONT_METADATA.get(t["target_canonical"], {}).get("classification") == "non-serif"]

        serif_acc = sum(1 for t in serif_tasks if t["is_correct"]) / len(serif_tasks) if serif_tasks else 0.0
        non_serif_acc = sum(1 for t in non_serif_tasks if t["is_correct"]) / len(non_serif_tasks) if non_serif_tasks else 0.0

        # Calculate sub-categories
        sub_cats = {}
        for sub_cat in ["neo-grotesque", "geometric-sans", "transitional-serif", "didone-display", "monospaced-slab", "casual-script"]:
            sub_tasks = [t for t in tasks if FONT_METADATA.get(t["target_canonical"], {}).get("sub_category") == sub_cat]
            if sub_tasks:
                sub_cats[sub_cat] = {
                    "accuracy": sum(1 for t in sub_tasks if t["is_correct"]) / len(sub_tasks),
                    "correct": sum(1 for t in sub_tasks if t["is_correct"]),
                    "total": len(sub_tasks)
                }

        # Per-font details
        per_font = []
        for font_name, f_meta in FONT_METADATA.items():
            f_tasks = [t for t in tasks if t["target_canonical"] == font_name]
            if f_tasks:
                correct = sum(1 for t in f_tasks if t["is_correct"])
                total = len(f_tasks)
                predictions = [t.get("raw_prediction", "") for t in f_tasks]
                per_font.append({
                    "font": font_name,
                    "classification": f_meta["classification"],
                    "category": f_meta["category"],
                    "sub_category": f_meta["sub_category"],
                    "accuracy": correct / total if total else 0.0,
                    "correct": correct,
                    "total": total,
                    "sample_predictions": predictions
                })

        # Cost estimation for benchmark run (approx 500 prompt tokens + image 258 tokens + 40 output tokens per task)
        # 30 tasks * (758 input tokens = 22.7k tokens) + (30 * 40 = 1.2k output tokens)
        est_run_cost = (
            (30 * 758 / 1_000_000) * meta["input_price_per_m"] +
            (30 * 50 / 1_000_000) * meta["output_price_per_m"]
        )

        model_entry = {
            "model_id": model_key,
            "display_name": meta["display_name"],
            "provider": meta["provider"],
            "family": meta["family"],
            "total_tasks": sc_data["total_tasks"],
            "correct_tasks": sc_data["correct_tasks"],
            "overall_accuracy": round(sc_data["overall_accuracy"] * 100, 1),
            "avg_latency_sec": round(sc_data["avg_latency_sec"], 2),
            "is_pareto_frontier": meta["is_pareto_frontier"],
            "pricing": {
                "input_per_m": meta["input_price_per_m"],
                "output_per_m": meta["output_price_per_m"],
                "estimated_run_cost_usd": round(est_run_cost, 5)
            },
            "by_classification": {
                "serif": {
                    "accuracy": round(serif_acc * 100, 1),
                    "correct": sum(1 for t in serif_tasks if t["is_correct"]),
                    "total": len(serif_tasks)
                },
                "non_serif": {
                    "accuracy": round(non_serif_acc * 100, 1),
                    "correct": sum(1 for t in non_serif_tasks if t["is_correct"]),
                    "total": len(non_serif_tasks)
                }
            },
            "by_category": {
                "serif": {
                    "accuracy": round(sc_data.get("accuracy_by_category", {}).get("serif", 0.0) * 100, 1),
                    "total": sum(1 for t in tasks if t["category"] == "serif")
                },
                "sans_serif": {
                    "accuracy": round(sc_data.get("accuracy_by_category", {}).get("sans-serif", 0.0) * 100, 1),
                    "total": sum(1 for t in tasks if t["category"] == "sans-serif")
                },
                "monospace": {
                    "accuracy": round(sc_data.get("accuracy_by_category", {}).get("monospace", 0.0) * 100, 1),
                    "total": sum(1 for t in tasks if t["category"] == "monospace")
                },
                "handwriting": {
                    "accuracy": round(sc_data.get("accuracy_by_category", {}).get("handwriting", 0.0) * 100, 1),
                    "total": sum(1 for t in tasks if t["category"] == "handwriting")
                }
            },
            "by_width": {
                "narrow": round(sc_data.get("accuracy_by_width", {}).get("narrow", 0.0) * 100, 1),
                "medium": round(sc_data.get("accuracy_by_width", {}).get("medium", 0.0) * 100, 1),
                "wide": round(sc_data.get("accuracy_by_width", {}).get("wide", 0.0) * 100, 1)
            },
            "by_sub_category": sub_cats,
            "per_font": per_font,
            "notes": meta["notes"],
            "tasks": tasks
        }
        models_output.append(model_entry)

    # Sort models by overall accuracy descending
    models_output.sort(key=lambda m: m["overall_accuracy"], reverse=True)

    summary = {
        "benchmark_id": "fontbench-1",
        "name": "FontBench-1",
        "version": "1.0.0",
        "description": "Visual font identification benchmark evaluating multimodal LLMs on typographic discernment across 10 canonical typefaces at 3 container wrapping widths.",
        "eval_date": "2026-09-07",
        "sentence": "The quick brown fox jumps over the lazy dog",
        "total_fonts": len(FONT_METADATA),
        "total_widths": 3,
        "total_tasks_per_model": 30,
        "taxonomies": {
            "classifications": ["serif", "non-serif"],
            "categories": ["serif", "sans-serif", "monospace", "handwriting"],
            "widths": [
                {"id": "narrow", "width_px": 220, "label": "Narrow (~4 lines)"},
                {"id": "medium", "width_px": 320, "label": "Medium (~3 lines)"},
                {"id": "wide", "width_px": 440, "label": "Wide (~2 lines)"}
            ],
            "fonts": [
                {"name": name, **meta} for name, meta in FONT_METADATA.items()
            ]
        },
        "models": models_output,
        "pareto_frontier": [m["model_id"] for m in models_output if m["is_pareto_frontier"]]
    }

    return summary


if __name__ == "__main__":
    benchmark_data = build_structured_benchmark("results")
    out_file = Path("results/fontbench_summary.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(benchmark_data, f, indent=2)
    print(f"Generated structured benchmark summary at {out_file} ({len(benchmark_data['models'])} models)")
