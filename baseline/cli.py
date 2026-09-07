"""Command-line interface for running the FontBench baseline harness."""

import argparse
import json
import os
import sys
from pathlib import Path

from baseline.evaluator import BaselineEvaluator, TaskEvaluationResult


def main():
    parser = argparse.ArgumentParser(
        description="FontBench-1 Baseline Zero-Shot VLM Evaluator",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gemini-3.5-flash-lite",
        help="VLM model identifier (e.g. gemini-3.5-flash-lite, gemini-3.5-flash, gemini-2.5-flash, gemini-2.5-pro)",
    )
    parser.add_argument(
        "--manifest",
        type=str,
        default="dataset/rendered/manifest.json",
        help="Path to rendered manifest.json",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit evaluation to first N tasks",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=10,
        help="Number of concurrent API evaluation workers",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="results",
        help="Directory to save scorecard.json and scorecard.md",
    )
    parser.add_argument(
        "--mock",
        action="store_true",
        help="Run in mock mode without calling remote APIs",
    )

    args = parser.parse_args()

    print("=" * 60)
    print(f"  FontBench-1 Multi-Attribute Baseline Evaluation Rig")
    print(f"  Model:       {args.model} {'(MOCK MODE)' if args.mock else ''}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Manifest:    {args.manifest}")
    print("=" * 60)

    evaluator = BaselineEvaluator(model_name=args.model, mock=args.mock)

    def progress_callback(result: TaskEvaluationResult, current: int, total: int):
        f_st = "✅" if result.font_correct else "❌"
        c_st = "✅" if result.category_correct else "❌"
        w_st = "✅" if result.weight_correct else "❌"
        m_st = "✅" if result.modifier_correct else "❌"
        k_st = "✅" if result.kerning_correct else "❌"
        l_st = "✅" if result.line_height_correct else "❌"
        print(f"[{current:04d}/{total:04d}] Comp:{result.composite_score*100:3.0f}% | "
              f"F:{f_st} C:{c_st} W:{w_st} M:{m_st} K:{k_st} L:{l_st} | "
              f"{result.target_canonical} -> '{result.predicted_font}' ({result.latency_sec:.2f}s)")

    scorecard = evaluator.evaluate_manifest(
        manifest_path=args.manifest,
        limit=args.limit,
        concurrency=args.concurrency,
        progress_cb=progress_callback,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    slug = args.model.replace("/", "_").replace(":", "_")
    json_path = os.path.join(args.output_dir, f"scorecard_{slug}.json")
    md_path = os.path.join(args.output_dir, f"scorecard_{slug}.md")

    scorecard_dict = {
        "model_name": scorecard.model_name,
        "timestamp": scorecard.timestamp,
        "total_tasks": scorecard.total_tasks,
        "overall_composite_score": scorecard.overall_composite_score,
        "overall_exact_match": scorecard.overall_exact_match,
        "font_accuracy": scorecard.font_accuracy,
        "category_accuracy": scorecard.category_accuracy,
        "weight_accuracy": scorecard.weight_accuracy,
        "modifier_accuracy": scorecard.modifier_accuracy,
        "kerning_accuracy": scorecard.kerning_accuracy,
        "line_height_accuracy": scorecard.line_height_accuracy,
        "accuracy_by_category": scorecard.accuracy_by_category,
        "accuracy_by_weight": scorecard.accuracy_by_weight,
        "accuracy_by_modifier": scorecard.accuracy_by_modifier,
        "accuracy_by_kerning": scorecard.accuracy_by_kerning,
        "accuracy_by_line_height": scorecard.accuracy_by_line_height,
        "accuracy_by_width": scorecard.accuracy_by_width,
        "per_font_accuracy": scorecard.per_font_accuracy,
        "avg_latency_sec": scorecard.avg_latency_sec,
        "tasks": [
            {
                "task_id": r.task_id,
                "target_canonical": r.target_canonical,
                "predicted_font": r.predicted_font,
                "font_correct": r.font_correct,
                "category": r.category,
                "predicted_category": r.predicted_category,
                "category_correct": r.category_correct,
                "weight": r.weight,
                "predicted_weight": r.predicted_weight,
                "weight_correct": r.weight_correct,
                "modifier": r.modifier,
                "predicted_modifier": r.predicted_modifier,
                "modifier_correct": r.modifier_correct,
                "kerning": r.kerning,
                "predicted_kerning": r.predicted_kerning,
                "kerning_correct": r.kerning_correct,
                "line_height": r.line_height,
                "predicted_line_height": r.predicted_line_height,
                "line_height_correct": r.line_height_correct,
                "all_correct": r.all_correct,
                "composite_score": r.composite_score,
                "width_id": r.width_id,
                "width_px": r.width_px,
                "latency_sec": r.latency_sec,
            }
            for r in scorecard.task_results
        ],
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(scorecard_dict, f, indent=2)

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(scorecard.to_markdown())

    print("\n" + "=" * 60)
    print(f"  Evaluation Finished: {args.model}")
    print(f"  Composite Typographic Score: {scorecard.overall_composite_score * 100:.1f}%")
    print(f"  Font Family Accuracy:       {scorecard.font_accuracy * 100:.1f}%")
    print(f"  Category Accuracy:          {scorecard.category_accuracy * 100:.1f}%")
    print(f"  Weight Accuracy:            {scorecard.weight_accuracy * 100:.1f}%")
    print(f"  Modifier Accuracy:          {scorecard.modifier_accuracy * 100:.1f}%")
    print(f"  Kerning Accuracy:           {scorecard.kerning_accuracy * 100:.1f}%")
    print(f"  Line Height Accuracy:       {scorecard.line_height_accuracy * 100:.1f}%")
    print(f"  Scorecard JSON: {json_path}")
    print(f"  Scorecard MD:   {md_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
