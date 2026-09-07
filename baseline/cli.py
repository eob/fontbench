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
        default="gemini-2.5-flash",
        help="VLM model identifier (e.g. gemini-2.5-flash, gemini-2.5-pro)",
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
    print(f"  FontBench-1 Baseline Evaluation Rig")
    print(f"  Model:    {args.model} {'(MOCK MODE)' if args.mock else ''}")
    print(f"  Manifest: {args.manifest}")
    print("=" * 60)

    evaluator = BaselineEvaluator(model_name=args.model, mock=args.mock)

    def progress_callback(result: TaskEvaluationResult, current: int, total: int):
        status = "✅ PASS" if result.is_correct else "❌ FAIL"
        print(f"[{current:02d}/{total:02d}] {status} | Task: {result.task_id} "
              f"| Target: {result.target_canonical} | Pred: '{result.raw_prediction}' "
              f"({result.latency_sec:.2f}s)")

    scorecard = evaluator.evaluate_manifest(
        manifest_path=args.manifest,
        limit=args.limit,
        progress_cb=progress_callback,
    )

    os.makedirs(args.output_dir, exist_ok=True)
    slug = args.model.replace("/", "_").replace(":", "_")
    json_path = os.path.join(args.output_dir, f"scorecard_{slug}.json")
    md_path = os.path.join(args.output_dir, f"scorecard_{slug}.md")

    # Serialize results
    scorecard_dict = {
        "model_name": scorecard.model_name,
        "timestamp": scorecard.timestamp,
        "total_tasks": scorecard.total_tasks,
        "correct_tasks": scorecard.correct_tasks,
        "overall_accuracy": scorecard.overall_accuracy,
        "accuracy_by_width": scorecard.accuracy_by_width,
        "accuracy_by_category": scorecard.accuracy_by_category,
        "per_font_accuracy": scorecard.per_font_accuracy,
        "avg_latency_sec": scorecard.avg_latency_sec,
        "tasks": [
            {
                "task_id": r.task_id,
                "target_canonical": r.target_canonical,
                "raw_prediction": r.raw_prediction,
                "is_correct": r.is_correct,
                "category": r.category,
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
    print(f"  Evaluation Finished!")
    print(f"  Accuracy: {scorecard.correct_tasks}/{scorecard.total_tasks} ({scorecard.overall_accuracy * 100:.1f}%)")
    print(f"  Scorecard JSON: {json_path}")
    print(f"  Scorecard MD:   {md_path}")
    print("=" * 60)


if __name__ == "__main__":
    main()
