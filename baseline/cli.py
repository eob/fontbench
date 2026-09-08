"""Command-line interface for running the FontBench baseline harness."""

import argparse
import json
import os
from dataclasses import asdict

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
        default="dataset/fontbench-2-rendered/manifest.json",
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
    if args.limit is not None and args.limit < 0:
        parser.error("--limit must be non-negative")
    if args.concurrency < 1:
        parser.error("--concurrency must be positive")

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

    try:
        scorecard = evaluator.evaluate_manifest(
            manifest_path=args.manifest,
            limit=args.limit,
            concurrency=args.concurrency,
            progress_cb=progress_callback,
        )
    finally:
        evaluator.close()

    os.makedirs(args.output_dir, exist_ok=True)
    slug = args.model.replace("/", "_").replace(":", "_")
    if args.mock:
        slug = f"mock_{slug}"
    json_path = os.path.join(args.output_dir, f"scorecard_{slug}.json")
    md_path = os.path.join(args.output_dir, f"scorecard_{slug}.md")

    scorecard_dict = asdict(scorecard)
    scorecard_dict["tasks"] = scorecard_dict.pop("task_results")
    scorecard_dict["mock"] = args.mock

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
