"""FontBench-1 Baseline VLM Evaluator.

Evaluates multimodal models on font identification tasks directly on
[(Image, Prompt), (Font Name)] pairs.
"""

from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PIL import Image


def normalize_font_name(text: str) -> str:
    """Normalize font name for fuzzy comparison (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def grade_prediction(prediction: str, canonical: str, aliases: List[str]) -> bool:
    """Check if model prediction matches canonical font name or acceptable aliases."""
    pred_norm = normalize_font_name(prediction)
    if not pred_norm:
        return False
    
    accepted = [canonical] + (aliases or [])
    accepted_norms = [normalize_font_name(a) for a in accepted if a]
    
    return any(a in pred_norm for a in accepted_norms)


@dataclass
class TaskEvaluationResult:
    task_id: str
    font_id: str
    target_canonical: str
    target_aliases: List[str]
    category: str
    width_id: str
    width_px: int
    image_path: str
    raw_prediction: str
    normalized_prediction: str
    is_correct: bool
    latency_sec: float
    model_name: str
    error: Optional[str] = None


@dataclass
class FontBenchScorecard:
    total_tasks: int
    correct_tasks: int
    overall_accuracy: float
    accuracy_by_width: Dict[str, float]
    accuracy_by_category: Dict[str, float]
    per_font_accuracy: Dict[str, float]
    avg_latency_sec: float
    model_name: str
    timestamp: str
    task_results: List[TaskEvaluationResult] = field(default_factory=list)

    def to_markdown(self) -> str:
        lines = [
            f"# FontBench-1 Scorecard: `{self.model_name}`",
            "",
            f"- **Evaluated At**: {self.timestamp}",
            f"- **Overall Accuracy**: **{self.correct_tasks}/{self.total_tasks} ({self.overall_accuracy * 100:.1f}%)**",
            f"- **Average Latency**: {self.avg_latency_sec:.2f}s / task",
            "",
            "## 1. Accuracy by Container Width",
            "",
            "| Width Slice | Tasks | Accuracy |",
            "|---|---|---|",
        ]
        for width, acc in sorted(self.accuracy_by_width.items()):
            lines.append(f"| `{width}` | - | {acc * 100:.1f}% |")

        lines.extend([
            "",
            "## 2. Accuracy by Font Category",
            "",
            "| Category | Accuracy |",
            "|---|---|",
        ])
        for cat, acc in sorted(self.accuracy_by_category.items()):
            lines.append(f"| `{cat}` | {acc * 100:.1f}% |")

        lines.extend([
            "",
            "## 3. Per-Font Accuracy",
            "",
            "| Font | Category | Accuracy | Predictions |",
            "|---|---|---|---|",
        ])
        for font, acc in sorted(self.per_font_accuracy.items()):
            font_tasks = [t for t in self.task_results if t.target_canonical == font]
            preds = ", ".join(f"`{t.raw_prediction or '<empty>'}`" for t in font_tasks)
            cat = font_tasks[0].category if font_tasks else "unknown"
            lines.append(f"| **{font}** | {cat} | {acc * 100:.1f}% | {preds} |")

        lines.extend([
            "",
            "## 4. Full Task Log",
            "",
            "| Task ID | Target Font | Prediction | Pass/Fail | Latency |",
            "|---|---|---|---|---|",
        ])
        for t in self.task_results:
            status = "✅ PASS" if t.is_correct else "❌ FAIL"
            lines.append(f"| `{t.task_id}` | {t.target_canonical} | `{t.raw_prediction}` | {status} | {t.latency_sec:.2f}s |")

        return "\n".join(lines)


class BaselineEvaluator:
    """Evaluates zero-shot multimodal models on FontBench tasks."""

    def __init__(self, model_name: str = "gemini-2.5-flash", mock: bool = False):
        self.model_name = model_name
        self.mock = mock
        self._client = None
        if not mock:
            self._init_client()

    def _init_client(self):
        from google import genai
        # Initialize Google GenAI client (picks up GEMINI_API_KEY from environment)
        self._client = genai.Client()

    def predict_image(self, image_path: str, prompt: str) -> str:
        """Query VLM with (Image, Prompt) and return raw predicted text."""
        if self.mock:
            # Deterministic mock response for offline testing
            return "Helvetica"

        img = Image.open(image_path)
        try:
            response = self._client.models.generate_content(
                model=self.model_name,
                contents=[img, prompt]
            )
            return response.text.strip() if response.text else ""
        except Exception as e:
            return f"ERROR: {str(e)}"

    def evaluate_manifest(
        self,
        manifest_path: str = "dataset/rendered/manifest.json",
        limit: Optional[int] = None,
        progress_cb: Optional[Callable[[TaskEvaluationResult, int, int], None]] = None
    ) -> FontBenchScorecard:
        """Run evaluation over all tasks defined in manifest."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_items = json.load(f)

        if limit is not None:
            manifest_items = manifest_items[:limit]

        total_tasks = len(manifest_items)
        results: List[TaskEvaluationResult] = []
        total_latency = 0.0

        for idx, item in enumerate(manifest_items, start=1):
            image_path = item["imagePath"]
            prompt = item.get(
                "prompt",
                "Examine the rendered text in the provided image. Identify the primary font family used to typeset this text. Output only the canonical font name."
            )

            start_t = time.perf_counter()
            raw_pred = self.predict_image(image_path, prompt)
            latency = time.perf_counter() - start_t
            total_latency += latency

            is_correct = grade_prediction(raw_pred, item["fontName"], item.get("aliases", []))
            
            res = TaskEvaluationResult(
                task_id=item["taskId"],
                font_id=item["fontId"],
                target_canonical=item["fontName"],
                target_aliases=item.get("aliases", []),
                category=item["category"],
                width_id=item["widthId"],
                width_px=item["widthPx"],
                image_path=image_path,
                raw_prediction=raw_pred,
                normalized_prediction=normalize_font_name(raw_pred),
                is_correct=is_correct,
                latency_sec=latency,
                model_name=self.model_name,
                error=raw_pred if raw_pred.startswith("ERROR:") else None
            )
            results.append(res)

            if progress_cb:
                progress_cb(res, idx, total_tasks)

        # Aggregate metrics
        correct_count = sum(1 for r in results if r.is_correct)
        overall_acc = correct_count / total_tasks if total_tasks else 0.0

        # By width
        widths = set(r.width_id for r in results)
        acc_by_width = {}
        for w in widths:
            sub = [r for r in results if r.width_id == w]
            acc_by_width[w] = sum(1 for r in sub if r.is_correct) / len(sub) if sub else 0.0

        # By category
        cats = set(r.category for r in results)
        acc_by_category = {}
        for c in cats:
            sub = [r for r in results if r.category == c]
            acc_by_category[c] = sum(1 for r in sub if r.is_correct) / len(sub) if sub else 0.0

        # By font
        fonts = set(r.target_canonical for r in results)
        per_font_acc = {}
        for f_name in fonts:
            sub = [r for r in results if r.target_canonical == f_name]
            per_font_acc[f_name] = sum(1 for r in sub if r.is_correct) / len(sub) if sub else 0.0

        scorecard = FontBenchScorecard(
            total_tasks=total_tasks,
            correct_tasks=correct_count,
            overall_accuracy=overall_acc,
            accuracy_by_width=acc_by_width,
            accuracy_by_category=acc_by_category,
            per_font_accuracy=per_font_acc,
            avg_latency_sec=total_latency / total_tasks if total_tasks else 0.0,
            model_name=self.model_name,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            task_results=results
        )

        return scorecard
