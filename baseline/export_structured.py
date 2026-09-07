"""FontBench Structured Output Aggregator.

Consolidates model scorecards into a structured, multi-dimensional
benchmark dataset for visualization, Pareto analysis, and typographic slicing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional


FONT_METADATA: Dict[str, Dict[str, str]] = {
    # Non-serif (20)
    "Arial": {"classification": "non-serif", "category": "non-serif", "sub_category": "neo-grotesque", "origin": "Monotype (1982)"},
    "Helvetica": {"classification": "non-serif", "category": "non-serif", "sub_category": "neo-grotesque", "origin": "Max Miedinger (1957)"},
    "Roboto": {"classification": "non-serif", "category": "non-serif", "sub_category": "neo-grotesque", "origin": "Christian Robertson (2011)"},
    "Inter": {"classification": "non-serif", "category": "non-serif", "sub_category": "neo-grotesque", "origin": "Rasmus Andersson (2017)"},
    "Montserrat": {"classification": "non-serif", "category": "non-serif", "sub_category": "geometric-sans", "origin": "Julieta Ulanovsky (2011)"},
    "Open Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "Steve Matteson (2011)"},
    "Lato": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "Łukasz Dziedzic (2010)"},
    "Poppins": {"classification": "non-serif", "category": "non-serif", "sub_category": "geometric-sans", "origin": "Indian Type Foundry (2014)"},
    "Source Sans 3": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "Paul D. Hunt (2012)"},
    "Oswald": {"classification": "non-serif", "category": "non-serif", "sub_category": "condensed-sans", "origin": "Vernon Adams (2011)"},
    "Raleway": {"classification": "non-serif", "category": "non-serif", "sub_category": "geometric-sans", "origin": "Matt McInerney (2008)"},
    "Nunito": {"classification": "non-serif", "category": "non-serif", "sub_category": "rounded-sans", "origin": "Vernon Adams (2011)"},
    "Rubik": {"classification": "non-serif", "category": "non-serif", "sub_category": "rounded-sans", "origin": "Hubert & Fischer (2015)"},
    "Work Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "grotesque-sans", "origin": "Wei Huang (2014)"},
    "Fira Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "Erik Spiekermann (2013)"},
    "PT Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "ParaType (2009)"},
    "DM Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "geometric-sans", "origin": "Colophon Foundry (2019)"},
    "Plus Jakarta Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "geometric-sans", "origin": "Tokotype (2020)"},
    "Noto Sans": {"classification": "non-serif", "category": "non-serif", "sub_category": "humanist-sans", "origin": "Monotype / Google (2012)"},
    "Verdana": {"classification": "non-serif", "category": "non-serif", "sub_category": "screen-humanist-sans", "origin": "Matthew Carter (1996)"},

    # Serif (15)
    "Times New Roman": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "Stanley Morison (1931)"},
    "Georgia": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "Matthew Carter (1993)"},
    "Playfair Display": {"classification": "serif", "category": "serif", "sub_category": "didone-modern-serif", "origin": "Claus Eggers Sørensen (2011)"},
    "Merriweather": {"classification": "serif", "category": "serif", "sub_category": "editorial-serif", "origin": "Eben Sorkin (2010)"},
    "EB Garamond": {"classification": "serif", "category": "serif", "sub_category": "old-style-serif", "origin": "Georg Duffner (2011)"},
    "Lora": {"classification": "serif", "category": "serif", "sub_category": "contemporary-serif", "origin": "Olga Karpushina (2011)"},
    "PT Serif": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "ParaType (2010)"},
    "Libre Baskerville": {"classification": "serif", "category": "serif", "sub_category": "transitional-serif", "origin": "Impallari Type (2012)"},
    "Cormorant Garamond": {"classification": "serif", "category": "serif", "sub_category": "classical-display-serif", "origin": "Christian Thalmann (2015)"},
    "Cinzel": {"classification": "serif", "category": "serif", "sub_category": "classical-roman-serif", "origin": "Natanael Gama (2012)"},
    "Bodoni Moda": {"classification": "serif", "category": "serif", "sub_category": "didone-modern-serif", "origin": "Owen Earl (2020)"},
    "Bitter": {"classification": "serif", "category": "serif", "sub_category": "slab-serif", "origin": "Sol Matas (2011)"},
    "Arvo": {"classification": "serif", "category": "serif", "sub_category": "geometric-slab-serif", "origin": "Anton Koovit (2010)"},
    "Crimson Text": {"classification": "serif", "category": "serif", "sub_category": "old-style-serif", "origin": "Sebastian Kosch (2010)"},
    "Spectral": {"classification": "serif", "category": "serif", "sub_category": "screen-editorial-serif", "origin": "Production Type (2017)"},

    # Monospace (6)
    "Courier New": {"classification": "mono", "category": "mono", "sub_category": "slab-serif-mono", "origin": "Howard Kettler (1955)"},
    "Roboto Mono": {"classification": "mono", "category": "mono", "sub_category": "geometric-mono", "origin": "Christian Robertson (2015)"},
    "Fira Code": {"classification": "mono", "category": "mono", "sub_category": "coding-ligature-mono", "origin": "Nikita Prokopov (2014)"},
    "Source Code Pro": {"classification": "mono", "category": "mono", "sub_category": "humanist-mono", "origin": "Paul D. Hunt (2012)"},
    "Space Mono": {"classification": "mono", "category": "mono", "sub_category": "display-mono", "origin": "Colophon Foundry (2016)"},
    "JetBrains Mono": {"classification": "mono", "category": "mono", "sub_category": "developer-mono", "origin": "Philipp Nurullin (2020)"},

    # Handwriting (5)
    "Comic Sans MS": {"classification": "handwriting", "category": "handwriting", "sub_category": "casual-script", "origin": "Vincent Connare (1994)"},
    "Pacifico": {"classification": "handwriting", "category": "handwriting", "sub_category": "brush-script", "origin": "Vernon Adams (2011)"},
    "Dancing Script": {"classification": "handwriting", "category": "handwriting", "sub_category": "casual-cursive", "origin": "Pablo Impallari (2011)"},
    "Caveat": {"classification": "handwriting", "category": "handwriting", "sub_category": "handwritten-marker", "origin": "Pablo Impallari (2015)"},
    "Shadows Into Light": {"classification": "handwriting", "category": "handwriting", "sub_category": "neat-handwriting", "origin": "Kimberly Geswein (2010)"},

    # Other / Display (4)
    "Impact": {"classification": "other", "category": "other", "sub_category": "industrial-display", "origin": "Geoffrey Lee (1965)"},
    "Bebas Neue": {"classification": "other", "category": "other", "sub_category": "condensed-display", "origin": "Ryoichi Tsunekawa (2010)"},
    "Lobster": {"classification": "other", "category": "other", "sub_category": "retro-display", "origin": "Pablo Impallari (2010)"},
    "Bungee": {"classification": "other", "category": "other", "sub_category": "urban-sign-display", "origin": "David Jonathan Ross (2016)"},
}

MODEL_METADATA: Dict[str, Dict[str, Any]] = {
    "gemini-3.5-flash-lite": {
        "display_name": "Gemini 3.5 Flash Lite",
        "provider": "Google",
        "family": "Gemini 3.5",
        "input_price_per_m": 0.075,
        "output_price_per_m": 0.30,
        "is_pareto_frontier": True,
        "notes": "Fastest inference latency with strong typographic property extraction."
    },
    "gemini-3.5-flash": {
        "display_name": "Gemini 3.5 Flash",
        "provider": "Google",
        "family": "Gemini 3.5",
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "is_pareto_frontier": True,
        "notes": "Highest overall composite typographic discernment and font identification accuracy."
    },
    "gemini-2.5-flash": {
        "display_name": "Gemini 2.5 Flash",
        "provider": "Google",
        "family": "Gemini 2.5",
        "input_price_per_m": 0.15,
        "output_price_per_m": 0.60,
        "is_pareto_frontier": False,
        "notes": "Solid baseline performance across categories, but higher error rate on subtle weight contrasts."
    },
    "gemini-2.5-pro": {
        "display_name": "Gemini 2.5 Pro",
        "provider": "Google",
        "family": "Gemini 2.5",
        "input_price_per_m": 1.25,
        "output_price_per_m": 5.00,
        "is_pareto_frontier": False,
        "notes": "Deep reasoning model with high font discernment but higher per-query latency."
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
        total_tasks = sc_data.get("total_tasks", len(tasks))

        # Only include complete benchmark runs
        if total_tasks < 1000:
            continue

        # Check if new multi-attribute format
        has_multi_attr = "overall_composite_score" in sc_data or (tasks and "font_correct" in tasks[0])

        if has_multi_attr:
            composite_score = sc_data.get("overall_composite_score", 0.0) * 100.0
            exact_match = sc_data.get("overall_exact_match", 0.0) * 100.0
            font_acc = sc_data.get("font_accuracy", 0.0) * 100.0
            cat_acc = sc_data.get("category_accuracy", 0.0) * 100.0
            weight_acc = sc_data.get("weight_accuracy", 0.0) * 100.0
            mod_acc = sc_data.get("modifier_accuracy", 0.0) * 100.0
            kerning_acc = sc_data.get("kerning_accuracy", 0.0) * 100.0
            lh_acc = sc_data.get("line_height_accuracy", 0.0) * 100.0

            # By category
            acc_by_cat = {}
            for c, c_stats in sc_data.get("accuracy_by_category", {}).items():
                if isinstance(c_stats, dict):
                    acc_by_cat[c] = {
                        "accuracy": round(c_stats.get("cat_acc", 0.0) * 100, 1),
                        "font_accuracy": round(c_stats.get("font_acc", 0.0) * 100, 1),
                        "composite": round(c_stats.get("composite", 0.0) * 100, 1),
                        "total": c_stats.get("count", 0),
                    }
                else:
                    acc_by_cat[c] = {
                        "accuracy": round(c_stats * 100, 1),
                        "font_accuracy": round(c_stats * 100, 1),
                        "composite": round(c_stats * 100, 1),
                        "total": sum(1 for t in tasks if t.get("category") == c),
                    }

            # By weight
            acc_by_weight = {
                w: round(acc * 100, 1)
                for w, acc in sc_data.get("accuracy_by_weight", {}).items()
            }

            # By modifier
            acc_by_mod = {
                m: round(acc * 100, 1)
                for m, acc in sc_data.get("accuracy_by_modifier", {}).items()
            }

            # By spacing
            spacing_stats = {
                "kerning": {
                    k: round(acc * 100, 1)
                    for k, acc in sc_data.get("accuracy_by_kerning", {}).items()
                },
                "line_height": {
                    lh: round(acc * 100, 1)
                    for lh, acc in sc_data.get("accuracy_by_line_height", {}).items()
                }
            }

            # By width
            acc_by_width = {
                w: round(acc * 100, 1)
                for w, acc in sc_data.get("accuracy_by_width", {}).items()
            }

            # Per font
            per_font = []
            for font_name, f_meta in FONT_METADATA.items():
                f_tasks = [t for t in tasks if t["target_canonical"] == font_name]
                if f_tasks:
                    f_correct = sum(1 for t in f_tasks if t.get("font_correct", t.get("is_correct", False)))
                    f_tot = len(f_tasks)
                    per_font.append({
                        "font": font_name,
                        "classification": f_meta["classification"],
                        "category": f_meta["category"],
                        "sub_category": f_meta["sub_category"],
                        "accuracy": round(f_correct / f_tot * 100, 1) if f_tot else 0.0,
                        "correct": f_correct,
                        "total": f_tot,
                        "sample_predictions": [t.get("predicted_font", t.get("raw_prediction", "")) for t in f_tasks[:3]]
                    })

        else:
            # Fallback for legacy 1-attribute scorecards
            font_acc = sc_data["overall_accuracy"] * 100.0
            composite_score = font_acc
            exact_match = font_acc
            cat_acc = 0.0
            weight_acc = 0.0
            mod_acc = 0.0
            kerning_acc = 0.0
            lh_acc = 0.0
            acc_by_cat = {}
            acc_by_weight = {}
            acc_by_mod = {}
            spacing_stats = {"kerning": {}, "line_height": {}}
            acc_by_width = {w: round(a * 100, 1) for w, a in sc_data.get("accuracy_by_width", {}).items()}
            per_font = []

        # Cost estimation per task: ~750 input tokens, ~60 output tokens
        est_run_cost = (
            (total_tasks * 750 / 1_000_000) * meta["input_price_per_m"] +
            (total_tasks * 60 / 1_000_000) * meta["output_price_per_m"]
        )

        model_entry = {
            "model_id": model_key,
            "display_name": meta["display_name"],
            "provider": meta["provider"],
            "family": meta["family"],
            "total_tasks": total_tasks,
            "overall_composite_score": round(composite_score, 1),
            "overall_exact_match": round(exact_match, 1),
            "overall_accuracy": round(composite_score, 1),  # For backward-compatibility with Pareto chart
            "font_accuracy": round(font_acc, 1),
            "category_accuracy": round(cat_acc, 1),
            "weight_accuracy": round(weight_acc, 1),
            "modifier_accuracy": round(mod_acc, 1),
            "kerning_accuracy": round(kerning_acc, 1),
            "line_height_accuracy": round(lh_acc, 1),
            "avg_latency_sec": round(sc_data["avg_latency_sec"], 2),
            "is_pareto_frontier": meta["is_pareto_frontier"],
            "pricing": {
                "input_per_m": meta["input_price_per_m"],
                "output_per_m": meta["output_price_per_m"],
                "estimated_run_cost_usd": round(est_run_cost, 4)
            },
            "by_category": acc_by_cat,
            "by_weight": acc_by_weight,
            "by_modifier": acc_by_mod,
            "by_spacing": spacing_stats,
            "by_width": acc_by_width,
            "per_font": per_font,
            "notes": meta["notes"],
            "tasks": tasks
        }
        models_output.append(model_entry)

    # Sort models by composite score descending
    models_output.sort(key=lambda m: m["overall_composite_score"], reverse=True)

    summary = {
        "benchmark_id": "fontbench-1",
        "name": "FontBench-1",
        "version": "1.1.0",
        "description": "Multi-attribute visual typography benchmark evaluating multimodal LLMs across 50 canonical fonts and 5 typographic dimensions: font family, category, weight, modifiers, and spacing.",
        "eval_date": "2026-09-07",
        "sentence": "The quick brown fox jumps over the lazy dog.",
        "total_fonts": len(FONT_METADATA),
        "total_tasks_per_model": models_output[0]["total_tasks"] if models_output else 1000,
        "taxonomies": {
            "categories": ["serif", "non-serif", "mono", "handwriting", "other"],
            "weights": ["thin", "regular", "bold", "black"],
            "modifiers": ["regular", "italic", "underline", "strikethrough", "small-caps"],
            "kerning": ["tight", "normal", "loose"],
            "line_height": ["tight", "normal", "loose"],
            "widths": [
                {"id": "narrow", "width_px": 220, "label": "Narrow (220px, ~4 lines)"},
                {"id": "medium", "width_px": 320, "label": "Medium (320px, ~3 lines)"},
                {"id": "wide", "width_px": 440, "label": "Wide (440px, ~2 lines)"}
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
