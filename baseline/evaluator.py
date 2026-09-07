"""FontBench-1 Baseline VLM Evaluator.

Evaluates multimodal models on multi-attribute typographic identification tasks:
- Font Family
- Typographic Category (serif, non-serif, mono, handwriting, other)
- Weight (thin, regular, bold, black)
- Modifiers (regular, italic, underline, strikethrough, small-caps)
- Spacing: Kerning (tight, normal, loose) & Line Height (tight, normal, loose)
"""

from __future__ import annotations

import base64
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import json
import os
import re
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from PIL import Image
from pydantic import BaseModel, Field


class TypographicPrediction(BaseModel):
    font: str = Field(default="", description="The canonical font family name")
    category: str = Field(default="other", description="serif, non-serif, mono, handwriting, other")
    weight: str = Field(default="regular", description="thin, regular, bold, black")
    modifier: str = Field(default="regular", description="regular, italic, underline, strikethrough, small-caps")
    kerning: str = Field(default="normal", description="tight, normal, loose")
    line_height: str = Field(default="normal", description="tight, normal, loose")


def normalize_font_name(text: str) -> str:
    """Normalize font name for fuzzy comparison (lowercase, alphanumeric only)."""
    return re.sub(r"[^a-z0-9]", "", text.lower())


def normalize_category(cat: str) -> str:
    c = cat.lower().strip()
    if any(k in c for k in ["sans", "non-serif", "nonserif"]):
        return "non-serif"
    if "serif" in c:
        return "serif"
    if any(k in c for k in ["mono", "fixed", "code", "typewriter"]):
        return "mono"
    if any(k in c for k in ["hand", "script", "cursive", "calligraph", "marker", "casual"]):
        return "handwriting"
    return "other"


def normalize_weight(w: str) -> str:
    w = w.lower().strip()
    if any(k in w for k in ["thin", "light", "hairline", "100", "200", "300"]):
        return "thin"
    if any(k in w for k in ["black", "heavy", "extra-bold", "extrabold", "ultra", "900", "800"]):
        return "black"
    if any(k in w for k in ["bold", "semi", "demi", "600", "700"]):
        return "bold"
    return "regular"


def normalize_modifier(m: str) -> str:
    m = m.lower().strip()
    if any(k in m for k in ["small-caps", "smallcaps", "small caps", "smcp"]):
        return "small-caps"
    if any(k in m for k in ["italic", "oblique", "slanted", "italics"]):
        return "italic"
    if any(k in m for k in ["strike", "line-through", "linethrough"]):
        return "strikethrough"
    if any(k in m for k in ["under", "underlined"]):
        return "underline"
    return "regular"


def normalize_kerning(k: str) -> str:
    k = k.lower().strip()
    if any(x in k for x in ["tight", "condensed", "narrow", "negative", "close", "compressed"]):
        return "tight"
    if any(x in k for x in ["loose", "wide", "expanded", "open", "spaced", "tracked", "relaxed"]):
        return "loose"
    return "normal"


def normalize_line_height(lh: str) -> str:
    lh = lh.lower().strip()
    if any(x in lh for x in ["tight", "compact", "narrow", "condensed", "single", "close"]):
        return "tight"
    if any(x in lh for x in ["loose", "wide", "relaxed", "double", "large", "tall"]):
        return "loose"
    return "normal"


def grade_font_prediction(prediction: str, canonical: str, aliases: List[str]) -> bool:
    """Check if model prediction matches canonical font name or acceptable aliases."""
    pred_norm = normalize_font_name(prediction)
    if not pred_norm:
        return False
    
    accepted = [canonical] + (aliases or [])
    accepted_norms = [normalize_font_name(a) for a in accepted if a]
    
    return any(a in pred_norm or pred_norm in a for a in accepted_norms)


@dataclass
class TaskEvaluationResult:
    task_id: str
    font_id: str
    target_canonical: str
    target_aliases: List[str]
    category: str
    weight: str
    modifier: str
    kerning: str
    line_height: str
    width_id: str
    width_px: int
    image_path: str
    raw_prediction: str
    predicted_font: str
    predicted_category: str
    predicted_weight: str
    predicted_modifier: str
    predicted_kerning: str
    predicted_line_height: str
    font_correct: bool
    category_correct: bool
    weight_correct: bool
    modifier_correct: bool
    kerning_correct: bool
    line_height_correct: bool
    all_correct: bool
    composite_score: float
    latency_sec: float
    model_name: str
    error: Optional[str] = None


@dataclass
class FontBenchScorecard:
    total_tasks: int
    overall_composite_score: float
    overall_exact_match: float
    font_accuracy: float
    category_accuracy: float
    weight_accuracy: float
    modifier_accuracy: float
    kerning_accuracy: float
    line_height_accuracy: float
    accuracy_by_category: Dict[str, Dict[str, float]]
    accuracy_by_weight: Dict[str, float]
    accuracy_by_modifier: Dict[str, float]
    accuracy_by_kerning: Dict[str, float]
    accuracy_by_line_height: Dict[str, float]
    accuracy_by_width: Dict[str, float]
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
            f"- **Total Tasks**: {self.total_tasks}",
            f"- **Composite Typographic Score**: **{self.overall_composite_score * 100:.1f}%**",
            f"- **All-Correct Exact Match**: **{self.overall_exact_match * 100:.1f}%**",
            f"- **Average Latency**: {self.avg_latency_sec:.2f}s / task",
            "",
            "## 1. Multi-Attribute Accuracy Breakdown",
            "",
            "| Typographic Dimension | Accuracy | Description |",
            "|---|---|---|",
            f"| **Font Family** | **{self.font_accuracy * 100:.1f}%** | Identification of exact font name across 50 top fonts |",
            f"| **Category** | **{self.category_accuracy * 100:.1f}%** | serif, non-serif, mono, handwriting, other |",
            f"| **Weight** | **{self.weight_accuracy * 100:.1f}%** | thin, regular, bold, black |",
            f"| **Modifiers** | **{self.modifier_accuracy * 100:.1f}%** | regular, italic, underline, strikethrough, small-caps |",
            f"| **Kerning** | **{self.kerning_accuracy * 100:.1f}%** | tight, normal, loose |",
            f"| **Line Height** | **{self.line_height_accuracy * 100:.1f}%** | tight, normal, loose |",
            "",
            "## 2. Accuracy by Typographic Category",
            "",
            "| Category | Tasks | Font Acc | Cat Acc | Composite Score |",
            "|---|---|---|---|---|",
        ]
        for cat, stats in sorted(self.accuracy_by_category.items()):
            lines.append(f"| `{cat}` | {stats.get('count', 0)} | {stats.get('font_acc', 0) * 100:.1f}% | {stats.get('cat_acc', 0) * 100:.1f}% | {stats.get('composite', 0) * 100:.1f}% |")

        lines.extend([
            "",
            "## 3. Font Accuracy Across Weights & Modifiers",
            "",
            "| Weight | Font Acc | Modifier | Font Acc |",
            "|---|---|---|---|",
        ])
        weights_sorted = sorted(self.accuracy_by_weight.items())
        mods_sorted = sorted(self.accuracy_by_modifier.items())
        max_rows = max(len(weights_sorted), len(mods_sorted))
        for i in range(max_rows):
            w_str = f"`{weights_sorted[i][0]}`: {weights_sorted[i][1] * 100:.1f}%" if i < len(weights_sorted) else ""
            m_str = f"`{mods_sorted[i][0]}`: {mods_sorted[i][1] * 100:.1f}%" if i < len(mods_sorted) else ""
            lines.append(f"| {w_str} | | {m_str} | |")

        lines.extend([
            "",
            "## 4. Per-Font Accuracy (Top 50 Fonts)",
            "",
            "| Font | Font Accuracy |",
            "|---|---|",
        ])
        for font, acc in sorted(self.per_font_accuracy.items(), key=lambda x: -x[1]):
            lines.append(f"| **{font}** | {acc * 100:.1f}% |")

        return "\n".join(lines)


class BaselineEvaluator:
    """Evaluates zero-shot multimodal models on FontBench multi-attribute tasks."""

    def __init__(self, model_name: str = "gemini-3.5-flash-lite", mock: bool = False):
        self.model_name = model_name
        self.mock = mock
        self._client = None
        if not mock:
            self._init_client()

    def _init_client(self):
        from google import genai
        from google.genai import types
        self._client = genai.Client(http_options=types.HttpOptions(timeout=60_000))

    def predict_image(self, image_path: str, prompt: str) -> tuple[str, dict]:
        """Query VLM with (Image, Prompt) and return structured typography prediction."""
        if self.mock:
            return '{"font": "Arial", "category": "non-serif", "weight": "regular", "modifier": "regular", "kerning": "normal", "line_height": "normal"}', {
                "font": "Arial",
                "category": "non-serif",
                "weight": "regular",
                "modifier": "regular",
                "kerning": "normal",
                "line_height": "normal"
            }

        from google.genai import types
        img = Image.open(image_path)
        last_error = ""
        for attempt in range(2):
            try:
                response = self._client.models.generate_content(
                    model=self.model_name,
                    contents=[img, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=TypographicPrediction,
                        temperature=0.0
                    )
                )
                raw_text = response.text.strip() if response.text else "{}"
                # Extract JSON
                try:
                    data = json.loads(raw_text)
                except Exception:
                    m = re.search(r"\{.*\}", raw_text, re.DOTALL)
                    data = json.loads(m.group(0)) if m else {}
                return raw_text, data
            except Exception as e:
                last_error = str(e)
                time.sleep(1.0)

        err_msg = f"ERROR: {last_error}"
        return err_msg, {}

    def _eval_single_task(self, item: dict, prompt_default: str) -> TaskEvaluationResult:
        image_path = item["imagePath"]
        prompt = item.get("prompt", prompt_default)

        start_t = time.perf_counter()
        raw_pred, parsed_pred = self.predict_image(image_path, prompt)
        latency = time.perf_counter() - start_t

        pred_font = str(parsed_pred.get("font", "")).strip()
        pred_cat = normalize_category(str(parsed_pred.get("category", "")))
        pred_weight = normalize_weight(str(parsed_pred.get("weight", "")))
        pred_modifier = normalize_modifier(str(parsed_pred.get("modifier", "")))
        pred_kerning = normalize_kerning(str(parsed_pred.get("kerning", "")))
        pred_lh = normalize_line_height(str(parsed_pred.get("line_height", "")))

        target_font = item["fontName"]
        target_aliases = item.get("aliases", [])
        target_cat = normalize_category(item["category"])
        target_weight = normalize_weight(item.get("weight", "regular"))
        target_modifier = normalize_modifier(item.get("modifier", "regular"))
        target_kerning = normalize_kerning(item.get("kerning", "normal"))
        target_lh = normalize_line_height(item.get("lineHeight", "normal"))

        font_correct = grade_font_prediction(pred_font, target_font, target_aliases)
        cat_correct = pred_cat == target_cat
        weight_correct = pred_weight == target_weight
        mod_correct = pred_modifier == target_modifier
        kerning_correct = pred_kerning == target_kerning
        lh_correct = pred_lh == target_lh

        all_correct = (font_correct and cat_correct and weight_correct and
                       mod_correct and kerning_correct and lh_correct)
        composite = sum([
            1.0 if font_correct else 0.0,
            1.0 if cat_correct else 0.0,
            1.0 if weight_correct else 0.0,
            1.0 if mod_correct else 0.0,
            1.0 if kerning_correct else 0.0,
            1.0 if lh_correct else 0.0
        ]) / 6.0

        return TaskEvaluationResult(
            task_id=item["taskId"],
            font_id=item["fontId"],
            target_canonical=target_font,
            target_aliases=target_aliases,
            category=target_cat,
            weight=target_weight,
            modifier=target_modifier,
            kerning=target_kerning,
            line_height=target_lh,
            width_id=item["widthId"],
            width_px=item["widthPx"],
            image_path=image_path,
            raw_prediction=raw_pred,
            predicted_font=pred_font,
            predicted_category=pred_cat,
            predicted_weight=pred_weight,
            predicted_modifier=pred_modifier,
            predicted_kerning=pred_kerning,
            predicted_line_height=pred_lh,
            font_correct=font_correct,
            category_correct=cat_correct,
            weight_correct=weight_correct,
            modifier_correct=mod_correct,
            kerning_correct=kerning_correct,
            line_height_correct=lh_correct,
            all_correct=all_correct,
            composite_score=composite,
            latency_sec=latency,
            model_name=self.model_name,
            error=raw_pred if raw_pred.startswith("ERROR:") else None
        )

    def evaluate_manifest(
        self,
        manifest_path: str = "dataset/rendered/manifest.json",
        limit: Optional[int] = None,
        concurrency: int = 5,
        progress_cb: Optional[Callable[[TaskEvaluationResult, int, int], None]] = None
    ) -> FontBenchScorecard:
        """Run evaluation over all tasks defined in manifest."""
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest_items = json.load(f)

        if limit is not None:
            manifest_items = manifest_items[:limit]

        total_tasks = len(manifest_items)
        results: List[TaskEvaluationResult] = []
        prompt_default = (
            "Examine the rendered text in the image. Identify its typographic properties:\n"
            "1. font: The canonical font family name\n"
            "2. category: Exactly one of [serif, non-serif, mono, handwriting, other]\n"
            "3. weight: Exactly one of [thin, regular, bold, black]\n"
            "4. modifier: Exactly one of [regular, italic, underline, strikethrough, small-caps]\n"
            "5. kerning: Exactly one of [tight, normal, loose]\n"
            "6. line_height: Exactly one of [tight, normal, loose]"
        )

        completed_count = 0
        if concurrency <= 1 or self.mock:
            for item in manifest_items:
                res = self._eval_single_task(item, prompt_default)
                results.append(res)
                completed_count += 1
                if progress_cb:
                    progress_cb(res, completed_count, total_tasks)
        else:
            indexed_results: List[tuple[int, TaskEvaluationResult]] = []
            with ThreadPoolExecutor(max_workers=concurrency) as executor:
                futures = {
                    executor.submit(self._eval_single_task, item, prompt_default): idx
                    for idx, item in enumerate(manifest_items)
                }
                for fut in as_completed(futures):
                    idx = futures[fut]
                    res = fut.result()
                    indexed_results.append((idx, res))
                    completed_count += 1
                    if progress_cb:
                        progress_cb(res, completed_count, total_tasks)

            indexed_results.sort(key=lambda pair: pair[0])
            results = [pair[1] for pair in indexed_results]

        # Aggregate metrics
        font_correct_count = sum(1 for r in results if r.font_correct)
        cat_correct_count = sum(1 for r in results if r.category_correct)
        weight_correct_count = sum(1 for r in results if r.weight_correct)
        mod_correct_count = sum(1 for r in results if r.modifier_correct)
        kerning_correct_count = sum(1 for r in results if r.kerning_correct)
        lh_correct_count = sum(1 for r in results if r.line_height_correct)
        all_correct_count = sum(1 for r in results if r.all_correct)
        total_composite = sum(r.composite_score for r in results)

        # By category stats
        cats = sorted(set(r.category for r in results))
        acc_by_category = {}
        for c in cats:
            sub = [r for r in results if r.category == c]
            c_cnt = len(sub)
            acc_by_category[c] = {
                "count": c_cnt,
                "font_acc": sum(1 for r in sub if r.font_correct) / c_cnt if c_cnt else 0.0,
                "cat_acc": sum(1 for r in sub if r.category_correct) / c_cnt if c_cnt else 0.0,
                "composite": sum(r.composite_score for r in sub) / c_cnt if c_cnt else 0.0,
            }

        # By weight stats
        weights = sorted(set(r.weight for r in results))
        acc_by_weight = {}
        for w in weights:
            sub = [r for r in results if r.weight == w]
            acc_by_weight[w] = sum(1 for r in sub if r.font_correct) / len(sub) if sub else 0.0

        # By modifier stats
        mods = sorted(set(r.modifier for r in results))
        acc_by_modifier = {}
        for m in mods:
            sub = [r for r in results if r.modifier == m]
            acc_by_modifier[m] = sum(1 for r in sub if r.font_correct) / len(sub) if sub else 0.0

        # By kerning stats
        kerns = sorted(set(r.kerning for r in results))
        acc_by_kerning = {}
        for k in kerns:
            sub = [r for r in results if r.kerning == k]
            acc_by_kerning[k] = sum(1 for r in sub if r.kerning_correct) / len(sub) if sub else 0.0

        # By line height stats
        lhs = sorted(set(r.line_height for r in results))
        acc_by_line_height = {}
        for lh in lhs:
            sub = [r for r in results if r.line_height == lh]
            acc_by_line_height[lh] = sum(1 for r in sub if r.line_height_correct) / len(sub) if sub else 0.0

        # By width stats
        widths = sorted(set(r.width_id for r in results))
        acc_by_width = {}
        for w in widths:
            sub = [r for r in results if r.width_id == w]
            acc_by_width[w] = sum(1 for r in sub if r.font_correct) / len(sub) if sub else 0.0

        # Per font accuracy
        fonts = sorted(set(r.target_canonical for r in results))
        per_font_acc = {}
        for f_name in fonts:
            sub = [r for r in results if r.target_canonical == f_name]
            per_font_acc[f_name] = sum(1 for r in sub if r.font_correct) / len(sub) if sub else 0.0

        total_latency = sum(r.latency_sec for r in results)
        scorecard = FontBenchScorecard(
            total_tasks=total_tasks,
            overall_composite_score=total_composite / total_tasks if total_tasks else 0.0,
            overall_exact_match=all_correct_count / total_tasks if total_tasks else 0.0,
            font_accuracy=font_correct_count / total_tasks if total_tasks else 0.0,
            category_accuracy=cat_correct_count / total_tasks if total_tasks else 0.0,
            weight_accuracy=weight_correct_count / total_tasks if total_tasks else 0.0,
            modifier_accuracy=mod_correct_count / total_tasks if total_tasks else 0.0,
            kerning_accuracy=kerning_correct_count / total_tasks if total_tasks else 0.0,
            line_height_accuracy=lh_correct_count / total_tasks if total_tasks else 0.0,
            accuracy_by_category=acc_by_category,
            accuracy_by_weight=acc_by_weight,
            accuracy_by_modifier=acc_by_modifier,
            accuracy_by_kerning=acc_by_kerning,
            accuracy_by_line_height=acc_by_line_height,
            accuracy_by_width=acc_by_width,
            per_font_accuracy=per_font_acc,
            avg_latency_sec=total_latency / total_tasks if total_tasks else 0.0,
            model_name=self.model_name,
            timestamp=time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            task_results=results
        )

        return scorecard
