"""Build a local benchmark report and contact sheets from actual rendered inputs."""

from __future__ import annotations

import argparse
import base64
from collections import Counter
from html import escape
import json
import math
from pathlib import Path
import shutil

from PIL import Image

from baseline.evaluator import GRADING_VERSION, evaluation_protocol_fingerprint, load_manifest
from baseline.model_config import load_model_config
from baseline.runner import dataset_fingerprint
from baseline.reporting import finite_nonnegative, metrics as _metrics, read_report_json, scorecard_tasks
from baseline.validate_dataset import validate_dataset


METRICS = {"composite": "Composite score", "exact": "All six correct", "font": "Font family",
           "category": "Category", "weight": "Weight", "modifier": "Modifier",
           "kerning": "Letter spacing", "line_height": "Line height"}
AXES = [
    ("category", "category", "Category", "Serif, sans serif, monospaced, handwriting, and display forms."),
    ("weight", "weight", "Weight", "Thin through black: identify the weight that was actually rendered."),
    ("modifier", "modifier", "Modifier", "Regular, italic, underline, strikethrough, and small caps."),
    ("kerning", "kerning", "Letter spacing", "Tight, normal, and loose CSS letter spacing; the benchmark field is kerning."),
    ("line_height", "lineHeight", "Line height", "Tight, normal, and loose spacing between wrapped lines."),
    ("font_family", "fontName", "Font family", "Exact canonical family or a declared alias, with case and punctuation normalized."),
]
AXIS_ORDERS = {
    "category": ["serif", "non-serif", "mono", "handwriting", "other"],
    "weight": ["thin", "regular", "bold", "black"],
    "modifier": ["regular", "italic", "underline", "strikethrough", "small-caps"],
    "kerning": ["tight", "normal", "loose"],
    "lineHeight": ["tight", "normal", "loose"],
}


def _select_samples(items: list[dict], count: int) -> list[dict]:
    """Greedily balance visible attributes, preferring different font families."""
    remaining = sorted(items, key=lambda item: item["taskId"])
    selected = []
    counts = {key: Counter() for key in ["fontId", "category", "weight", "modifier", "kerning", "lineHeight"]}
    while remaining and len(selected) < count:
        sample = max(remaining, key=lambda item: sum(
            (3 if key == "fontId" else 1) / (1 + values[item[key]]) for key, values in counts.items()
        ))
        selected.append(sample)
        remaining.remove(sample)
        for key, values in counts.items():
            values[sample[key]] += 1
    return selected


def _montage(samples: list[dict], title: str, columns: int, axis: str | None = None) -> str:
    cell_w, cell_h, gap = 240, 220, 12
    columns = min(columns, len(samples))
    rows = math.ceil(len(samples) / columns)
    width = columns * cell_w + (columns + 1) * gap
    height = rows * cell_h + (rows + 1) * gap
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" role="img">',
             f'<title>{escape(title)}</title>', '<rect width="100%" height="100%" fill="#eeeae4"/>']
    for index, sample in enumerate(samples):
        x = gap + index % columns * (cell_w + gap)
        y = gap + index // columns * (cell_h + gap)
        image_path = Path(sample["imagePath"])
        with Image.open(image_path) as image:
            image.load()
            if image.format != "PNG":
                raise ValueError(f"Expected a PNG benchmark input: {image_path}")
        payload = base64.b64encode(image_path.read_bytes()).decode("ascii")
        label = sample[axis] if axis else sample["fontName"]
        detail = sample["fontName"] if axis else f'{sample["category"]} · {sample["weight"]} · {sample["modifier"]}'
        parts.extend([
            f'<g data-task-id="{escape(sample["taskId"], quote=True)}">',
            f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" rx="8" fill="#fff"/>',
            f'<image x="{x+8}" y="{y+8}" width="{cell_w-16}" height="150" preserveAspectRatio="xMidYMid meet" href="data:image/png;base64,{payload}"/>',
            f'<text x="{x+12}" y="{y+181}" font-family="Arial,sans-serif" font-size="15" font-weight="700" fill="#202126">{escape(label)}</text>',
            f'<text x="{x+12}" y="{y+202}" font-family="Arial,sans-serif" font-size="11" fill="#676b75">{escape(detail)}</text>',
            '</g>',
        ])
    return "\n".join(parts + ["</svg>"])


def _percent(value: float | None) -> str:
    return "—" if value is None else f"{value * 100:.1f}%"


def _breakdown_table(section: dict, models: list[dict]) -> str:
    headings = "".join(f'<th scope="col">{escape(model["display_name"])}</th>' for model in models)
    rows = []
    for group in section["groups"]:
        cells = []
        for model in models:
            value = group["models"][model["id"]]
            score = value["metrics"]["composite"]
            cells.append(f'<td>{_percent(score)}<small>n={value["count"]}</small></td>')
        rows.append(f'<tr><th scope="row">{escape(group["label"])}<small>{group["available"]} inputs</small></th>{"".join(cells)}</tr>')
    return f'<div class="table-scroll"><table><thead><tr><th scope="col">Input group</th>{headings}</tr></thead><tbody>{"".join(rows)}</tbody></table></div>'


def build_page(manifest_path: str | Path, results_dir: str | Path, output_dir: str | Path = "site",
               config_path: str | Path = "config/models.json") -> dict:
    validity = validate_dataset(manifest_path)
    items = load_manifest(str(manifest_path))
    if not items:
        raise ValueError("A benchmark page needs at least one rendered input")
    by_id = {item["taskId"]: item for item in items}
    fingerprint = dataset_fingerprint(items)
    models = load_model_config(config_path)
    directory, output = Path(results_dir), Path(output_dir)
    summary_path = directory / "summary.json"
    warnings = []
    summary = read_report_json(summary_path, warnings)
    if summary and (summary.get("dataset_fingerprint") != fingerprint
                    or summary.get("evaluation_protocol_fingerprint") != evaluation_protocol_fingerprint()
                    or not isinstance(summary.get("mock"), bool) or not isinstance(summary.get("models"), dict)):
        warnings.append("Excluded run summary with incompatible dataset or missing mock provenance.")
        summary = {}
    if not validity["valid"]:
        warnings.append("Dataset validity checks failed; these inputs are for inspection and cannot support benchmark claims.")
    tasks_by_model = {}
    for model in models:
        card_path = directory / f'scorecard_{model["id"]}.json'
        card = read_report_json(card_path, warnings)
        tasks = []
        rejected_card = card_path.exists() and not card
        if card:
            try:
                tasks = scorecard_tasks(card)
                if (card["dataset_fingerprint"] != fingerprint
                        or card.get("model_id") != model["id"] or card.get("model_name") != model["model"]
                        or card.get("provider") != model["provider"]
                        or card.get("max_output_tokens") != model["max_output_tokens"]
                        or card["expected_task_count"] != len(items)
                        or not {task["task_id"] for task in tasks} <= set(by_id)
                        or not validity["valid"]):
                    raise ValueError("Incompatible model or validated dataset")
            except ValueError as error:
                warnings.append(f'{model["display_name"]}: excluded scorecard: {error}.')
                tasks = []
                rejected_card = True
        state = summary.get("models", {}).get(model["id"], {})
        if not isinstance(state, dict) or (state and (rejected_card or state.get("model") != model["model"]
                      or state.get("provider") != model["provider"]
                      or state.get("max_output_tokens") != model["max_output_tokens"]
                      or (card and summary["mock"] != card.get("mock")))):
            warnings.append(f'{model["display_name"]}: excluded run state with incompatible model or scorecard provenance.')
            state = {}
        model.update(completed=len(tasks), expected=len(items), metrics=_metrics(tasks),
                     status="complete" if len(tasks) == len(items) else "partial" if tasks else "pending",
                     run_state=state.get("status") if isinstance(state.get("status"), str) else "pending",
                     reason=state.get("reason") if isinstance(state.get("reason"), str) else None,
                     cost_usd=state.get("cost_usd") if finite_nonnegative(state.get("cost_usd")) else None,
                     mock=bool(card.get("mock", False)) if card and not rejected_card else bool(summary.get("mock", False)) if state else False)
        tasks_by_model[model["id"]] = tasks
    if len({model["mock"] for model in models if model["completed"]}) > 1:
        raise ValueError("Do not combine mock and live measurements on one benchmark page")
    return _render_page(items, models, tasks_by_model, validity, output, warnings)


def build_release_page(version: str = "1.0.0", results_dir: str | Path = "results/runs",
                       output_dir: str | Path = "site", *, root: str | Path | None = None) -> dict:
    from baseline.releases import load_release, release_manifest_path, validate_release
    from baseline.reporting import aggregate_release_runs

    release = load_release(version, root=root)
    items = validate_release(release, root=root)
    validity = validate_dataset(release_manifest_path(release, root=root))
    if not validity["valid"]:
        raise ValueError("Frozen release failed dataset validity checks")
    history = aggregate_release_runs(release, items, results_dir, root=root)
    output = Path(output_dir)
    for run in history["runs"]:
        source = Path(results_dir) / run["path"]
        destination = output / "runs" / run["run_id"]
        destination.mkdir(parents=True, exist_ok=True)
        for filename in ["run.json", "summary.json", "attempts.jsonl", *[path.name for path in source.glob("scorecard_*.json")]]:
            if (source / filename).is_file():
                shutil.copyfile(source / filename, destination / filename)
    return _render_page(items, history["models"], history["tasks_by_model"], validity,
                        output, history["warnings"], release=release, history=history)


def _render_page(items: list[dict], models: list[dict], tasks_by_model: dict, validity: dict,
                 output: Path, warnings: list[str], *, release: dict | None = None,
                 history: dict | None = None) -> dict:
    by_id = {item["taskId"]: item for item in items}
    fingerprint = dataset_fingerprint(items)

    measured_ids = [model["id"] for model in models if model["completed"]]
    common_ids = set.intersection(*({task["task_id"] for task in tasks_by_model[model_id]} for model_id in measured_ids)) if measured_ids else set()
    comparison = {"task_ids": sorted(common_ids), "count": len(common_ids),
                  "models": {model_id: _metrics([task for task in tasks_by_model[model_id] if task["task_id"] in common_ids])
                             for model_id in measured_ids}}

    assets = output / "assets"
    assets.mkdir(parents=True, exist_ok=True)
    main_samples = _select_samples(items, 24)
    (assets / "overview.svg").write_text(_montage(main_samples, "Representative FontBench inputs", 8))
    sections = []
    for section_id, key, title, description in AXES:
        order = {value: index for index, value in enumerate(AXIS_ORDERS.get(key, []))}
        values = sorted({item[key] for item in items}, key=lambda value: (order.get(value, len(order)), value))
        samples = []
        grouped_samples = [_select_samples([item for item in items if item[key] == value], 1 if key == "fontName" else 2) for value in values]
        for row in range(max(map(len, grouped_samples))):
            samples.extend(group[row] for group in grouped_samples if len(group) > row)
        asset = f"assets/{section_id}.svg"
        (output / asset).write_text(_montage(samples, f"FontBench: {title}", 10 if key == "fontName" else len(values), key))
        groups = []
        for value in values:
            results = {}
            for model in models:
                subset = [task for task in tasks_by_model[model["id"]] if by_id[task["task_id"]][key] == value]
                results[model["id"]] = {"count": len(subset), "metrics": _metrics(subset)}
            groups.append({"label": value, "available": sum(item[key] == value for item in items), "models": results})
        sections.append({"id": section_id, "title": title, "description": description, "asset": asset,
                         "sample_ids": [sample["taskId"] for sample in samples], "groups": groups})
    report = {"dataset_fingerprint": fingerprint, "total_inputs": len(items),
              "validity": validity, "comparison": comparison, "grading_version": GRADING_VERSION,
              "font_count": len({item["fontId"] for item in items}), "models": models,
              "sections": sections, "warnings": warnings, "mock": any(model["mock"] for model in models),
              "overview_sample_ids": [sample["taskId"] for sample in main_samples]}
    if release is not None:
        report.update(benchmark_version=release["benchmark_version"], dataset_git_commit=release["dataset_git_commit"],
                      evaluation_protocol_fingerprint=release["evaluation_protocol_fingerprint"],
                      run_history=history["runs"], excluded_runs=history["excluded_runs"],
                      duplicate_policy=history["duplicate_policy"],
                      task_origins={model_id: [{key: task[key] for key in ("task_id", "source_run_id", "recorded_at")}
                                              for task in tasks] for model_id, tasks in tasks_by_model.items()})
    (output / "benchmark.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n")

    measured = [model for model in models if model["completed"]]
    coverage = sum(model["completed"] for model in models)
    complete = bool(models) and all(model["status"] == "complete" for model in models)
    status_text = ("Mock preview" if report["mock"] else "Measurements complete" if complete
                   else "Partial measurements" if measured else "Awaiting measured results")
    choices = "".join(f'<option value="{key}">{value}</option>' for key, value in METRICS.items())
    model_rows = []
    for model in models:
        score = model["metrics"]["composite"]
        cost = model["cost_usd"]
        cost_text = "—" if cost is None else f"${cost:.4f}"
        run_detail = ""
        if model["run_state"] not in {"pending", "running", "complete"}:
            run_detail = f'<small>{escape(model["run_state"].replace("_", " ").capitalize())}</small>'
        if model["reason"]:
            run_detail += f'<details><summary>Run details</summary><p>{escape(model["reason"])}</p></details>'
        if release is not None:
            origins = "".join(
                f'<li><a href="runs/{escape(origin["run_id"], quote=True)}/{escape(origin["scorecard"], quote=True)}">{escape(origin["run_id"])}</a>: '
                f'{escape(origin["created_at"][:10])} · {origin["accepted_task_count"]} selected · {origin["duplicate_count"]} repeats</li>'
                for origin in model["origins"])
            run_detail += f'<details><summary>{len(model["origins"])} run(s); {model["duplicate_count"]} repeated answer(s)</summary><ul>{origins}</ul><p>Configuration: {model["model_config_fingerprint"]}</p></details>'
            run_detail += f'<small>Output cap: {model["max_output_tokens"]:,} · config {model["model_config_fingerprint"][:8]}</small>'
        cost_label = "all run attempts, including repeats" if release is not None else "estimated run cost"
        model_rows.append(f'''<tr><th scope="row"><span class="provider {model['provider']}">{escape(model['provider'])}</span>{escape(model['display_name'])}<small>{escape(model['model'])}</small></th>
<td><span class="status {model['status']}">{model['status']}</span><small>{model['completed']} / {len(items)}</small>{run_detail}</td>
<td class="score" data-model="{model['id']}"><span>{_percent(score)}</span><div class="track"><i style="width:{0 if score is None else score*100}%"></i></div></td>
<td>{cost_text}<small>{cost_label}</small></td></tr>''')
    section_html = []
    for index, section in enumerate(sections, 1):
        section_html.append(f'''<section class="dimension" id="{section['id']}"><div class="section-heading"><div><p class="eyebrow">Dimension {index:02d}</p><h3>{section['title']}</h3><p>{section['description']}</p></div><a class="sheet-link" href="{section['asset']}" target="_blank">Open full contact sheet ↗</a></div>
<figure><img loading="lazy" src="{section['asset']}" alt="Actual benchmark images showing {escape(section['title'].lower())} variation"><figcaption>Original rendered inputs, with labels from the manifest. Other attributes can also vary.</figcaption></figure>
<div class="breakdown" data-section="{section['id']}">{_breakdown_table(section, models)}</div></section>''')
    config_cards = []
    for model in models:
        price = "Unrecorded pricing" if model["input_per_m"] is None or model["output_per_m"] is None else f'${model["input_per_m"]:g} input / ${model["output_per_m"]:g} output per MTok'
        config_cards.append(f'''<article class="model-card"><span class="provider {model['provider']}">{model['provider']}</span><h4>{escape(model['display_name'])}</h4><code>{escape(model['model'])}</code><p>{price}</p><p>{escape(model['notes'])}</p><details><summary>Pricing and configuration</summary><p>{escape(model['pricing_notes'])}</p><p>Output cap: {model['max_output_tokens']:,} tokens. Model-default reasoning settings.</p><a href="{escape(model['pricing_source_url'] or model['source_url'], quote=True)}" target="_blank" rel="noopener">Official pricing ↗</a></details></article>''')
    warning_html = "".join(f'<p>{escape(message)}</p>' for message in warnings)
    validity_html = ('<div class="notice">Dataset validity checks passed.</div>' if validity["valid"] else
                     '<div class="notice">Dataset validity checks failed. Inspect these inputs before running the benchmark.</div>')
    comparison_html = ''
    if len(measured_ids) > 1:
        comparison_html = f'<p class="method-note">Shared comparison: {len(common_ids)} input(s) completed by every measured model. ' + "; ".join(
            f'{escape(model["display_name"])}: {_percent(comparison["models"][model["id"]]["composite"])} composite'
            for model in models if model["id"] in measured_ids) + '</p>'
    mock_html = '<div class="notice">Mock preview: these are test outputs, not measured model performance.</div>' if report["mock"] else ""
    pending_html = '<p class="empty">Awaiting measured results. Model configurations are ready; no scores have been filled in.</p>' if not measured else ""
    release_html = ""
    history_html = ""
    if release is not None:
        commit = release["dataset_git_commit"]
        release_html = f'<div class="notice"><strong>FontBench {escape(release["benchmark_version"])}</strong> · Frozen dataset <a href="https://github.com/eob/fontbench/commit/{commit}">{commit[:12]}</a><details><summary>Release hashes and aggregation policy</summary><p>Dataset: <code>{fingerprint}</code></p><p>Protocol: <code>{release["evaluation_protocol_fingerprint"]}</code></p><p>{escape(history["duplicate_policy"])}</p><p>Historical, unversioned, mock, and incompatible runs are excluded.</p></details></div>'
        run_rows = []
        for run in history["runs"]:
            links = f'<a href="runs/{escape(run["run_id"], quote=True)}/run.json">Invocations</a> · <a href="runs/{escape(run["run_id"], quote=True)}/summary.json">Summary</a>'
            if run["has_attempt_ledger"]:
                links += f' · <a href="runs/{escape(run["run_id"], quote=True)}/attempts.jsonl">Attempt export</a>'
            else:
                links += '<small>Attempt history unavailable</small>'
            runner_commit = run.get("runner_git_commit")
            runner = escape(str(runner_commit or "Unrecorded"))
            if isinstance(runner_commit, str) and len(runner_commit) == 40 and all(c in "0123456789abcdef" for c in runner_commit):
                runner = f'<a href="https://github.com/eob/fontbench/commit/{runner_commit}">{runner_commit[:12]}</a>'
            if run.get("runner_git_dirty"):
                runner += " + local changes"
            run_rows.append(f'<tr><th scope="row">{escape(run["run_id"])}</th><td>{escape(run["created_at"])}<small>Updated {escape(run["updated_at"])}</small></td><td>{runner}</td><td>{links}</td></tr>')
        exclusions = "".join(f'<li>{escape(entry["path"])}: {escape(entry["reason"])}</li>' for entry in history["excluded_runs"])
        history_html = '<section id="run-history"><h2>Run history</h2><p>Scores use the first recorded final answer for each configuration and input. Run records retain attempt costs, including repeated inputs. Attempt exports may lag active runs; unavailable exports are marked below.</p><div class="table-scroll"><table><thead><tr><th>Run</th><th>Recorded dates (UTC)</th><th>Runner commit</th><th>Original records</th></tr></thead><tbody>' + "".join(run_rows) + '</tbody></table></div>'
        if exclusions:
            history_html += f'<details><summary>{len(history["excluded_runs"])} excluded record(s)</summary><ul>{exclusions}</ul></details>'
        history_html += '</section>'
        if not measured:
            pending_html = '<p class="empty">Awaiting measured results. No compatible live measurements have been recorded for this release.</p>'
    data_json = json.dumps(report, ensure_ascii=False).replace("<", "\\u003c")
    html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="description" content="FontBench: measured visual typography recognition across six attributes and leading multimodal models."><title>FontBench — Can a model read the type?</title><style>{_STYLE}</style></head>
<body><header class="topbar"><a class="brand" href="#top"><span>Fb</span> FontBench</a><nav aria-label="Main navigation"><a href="#performance">Results</a><a href="#inputs">Inputs</a><a href="#dimensions">Dimensions</a><a href="#models">Models</a></nav></header>
<main id="top"><section class="hero"><p class="eyebrow"><span class="live-dot"></span> A visual typography benchmark</p><h1>Can a model<br><em>read the type?</em></h1><div class="hero-bottom"><p>One sentence. Six typographic decisions.<br>Measuring how multimodal models see the details that make a typeface.</p><span class="run-label">{status_text}</span></div>
<div class="stats"><div><strong>{report['font_count']}</strong><span>font families</span></div><div><strong>{len(items):,}</strong><span>rendered inputs</span></div><div><strong>6</strong><span>scored attributes</span></div><div><strong>{len(models)}</strong><span>model configurations</span></div></div></section>
{release_html}{validity_html}{mock_html}<section id="inputs" class="inputs"><div class="section-heading"><div><p class="eyebrow">The evidence</p><h2>What the models actually see</h2></div><a class="sheet-link" href="assets/overview.svg" target="_blank">Explore full contact sheet ↗</a></div><figure><img src="assets/overview.svg" alt="A landscape contact sheet of {len(main_samples)} actual FontBench input images spanning families and typographic attributes"><figcaption>{len(main_samples)} representative inputs, selected to balance families, categories, weights, modifiers, and spacing. Every tile is an original benchmark PNG.</figcaption></figure></section>
<section id="performance"><div class="section-heading"><div><p class="eyebrow">The measurements</p><h2>Model performance</h2><p>{coverage:,} completed model–input pairs. Each model's sample count is shown below.</p></div><label class="metric-label">Metric<select id="metric">{choices}</select></label></div>{pending_html}<div class="table-scroll overview"><table><thead><tr><th scope="col">Model</th><th scope="col">Coverage</th><th scope="col" id="metric-heading">Composite score</th><th scope="col">Run cost</th></tr></thead><tbody>{''.join(model_rows)}</tbody></table></div><p class="method-note">Composite score gives each of the six attributes equal weight. Percentages use completed samples; pending samples are not counted as wrong answers. Partial runs may cover different samples and should not be treated as final rankings.</p>{comparison_html}{warning_html}</section>
<section id="dimensions" class="dimensions-intro"><p class="eyebrow">A closer look</p><h2>Six ways to read a sentence.</h2><p>Explore the visual variation, then compare measured scores within each group. Every cell includes its sample count; a dash means no completed measurements.</p></section>{''.join(section_html)}
<section id="models"><div class="section-heading"><div><p class="eyebrow">The lineup</p><h2>Models &amp; configurations</h2><p>Explicit API models across Anthropic, OpenAI, and Google. Prices are recorded reference rates, not a performance estimate.</p></div></div><div class="model-grid">{''.join(config_cards)}</div></section>
{history_html}<footer><a class="brand" href="#top"><span>Fb</span> FontBench</a><p>Reproducible inputs. Explicit grading. Measured results.<br><a href="benchmark.json">Download the page data</a> · No external assets required.</p><details><summary>Dataset identity</summary><code>{fingerprint}</code><p>Input images and task metadata are hashed together. Only matching scorecards using grading version {GRADING_VERSION} and the current evaluation protocol contribute measurements.</p></details></footer></main>
<script id="benchmark-data" type="application/json">{data_json}</script><script>{_SCRIPT}</script></body></html>'''
    (output / "index.html").write_text(html, encoding="utf-8")
    return report


_STYLE = '''
:root{--ink:#20232a;--muted:#686b73;--paper:#f7f5f0;--line:#dedbd4;--blue:#3f50db}*{box-sizing:border-box}html{scroll-behavior:smooth;scroll-padding-top:90px}body{margin:0;background:var(--paper);color:var(--ink);font:15px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif}a{color:inherit}button,select{font:inherit}.topbar{height:80px;padding:0 max(5vw,24px);display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid var(--line);background:var(--paper)}.brand{display:flex;align-items:center;gap:10px;font-size:18px;font-weight:700;text-decoration:none;letter-spacing:-.6px}.brand span{background:var(--ink);color:white;font-family:Georgia,serif;font-size:24px;line-height:40px;width:40px;text-align:center;border-radius:5px}nav{display:flex;gap:30px}nav a{text-decoration:none;color:var(--muted);font-size:13px}nav a:hover{color:var(--blue)}main{max-width:1512px;padding:0 48px;margin:auto}.hero{padding:24px 0 0;margin-bottom:28px}.eyebrow{text-transform:uppercase;font-size:11px;letter-spacing:2.1px;font-weight:700;color:var(--muted);margin:0 0 16px}.live-dot{display:inline-block;background:var(--blue);width:7px;height:7px;border-radius:50%;margin-right:7px}h1{font-size:clamp(48px,4.8vw,64px);line-height:1.02;font-weight:500;letter-spacing:-3.5px;margin:12px 0 16px}h1 em{font-family:Georgia,"Times New Roman",serif;font-weight:400;color:var(--blue)}.hero-bottom{display:flex;justify-content:space-between;align-items:end;gap:30px}.hero-bottom>p{font-size:15px;color:var(--muted);margin:0;line-height:1.5}.run-label{border:1px solid #c8ccee;border-radius:40px;background:#eceefa;color:var(--blue);padding:8px 18px;font-size:12px;white-space:nowrap}.stats{display:grid;grid-template-columns:repeat(4,1fr);margin-top:20px;border-block:1px solid var(--line)}.stats div{padding:10px 0}.stats strong{display:block;line-height:1.2;font-size:26px;font-weight:500;letter-spacing:-1px}.stats span{font-size:12px;color:var(--muted)}section{margin-bottom:70px}h2{font-size:30px;font-weight:500;letter-spacing:-1px;line-height:1.2;margin:0 0 10px}h3{font-size:32px;font-weight:500;letter-spacing:-1px;margin:0 0 8px}.section-heading{display:flex;justify-content:space-between;align-items:center;gap:24px;margin-bottom:24px}.section-heading p:not(.eyebrow),.dimensions-intro>p:last-child{color:var(--muted);max-width:680px;margin:0}#inputs .section-heading{margin-bottom:16px}.sheet-link{font-size:12px;white-space:nowrap;text-underline-offset:5px}.sheet-link:hover{color:var(--blue)}figure{margin:0}figure img{display:block;width:100%;height:auto;border:1px solid var(--line);border-radius:9px;background:#eeeae4}figcaption{font-size:11px;color:var(--muted);margin-top:12px}.metric-label{font-size:11px;color:var(--muted);display:flex;align-items:center;gap:12px}select{border:1px solid var(--line);background:white;border-radius:5px;padding:9px 28px 9px 12px;color:var(--ink);font-size:12px}.table-scroll{overflow:auto;border:1px solid var(--line);border-radius:9px;background:#fff}table{border-collapse:collapse;width:100%;font-size:12px;text-align:left;white-space:nowrap}th,td{padding:16px;border-bottom:1px solid #eae8e3}thead th{background:#f0eee8;text-transform:uppercase;letter-spacing:.7px;font-size:10px;color:var(--muted);font-weight:600}tbody th{font-weight:600}tbody tr:last-child th,tbody tr:last-child td{border-bottom:0}td small,th small{display:block;font-size:10px;font-weight:400;color:var(--muted);margin-top:3px}.overview tbody th{font-size:14px;min-width:270px}.provider{display:inline-block;text-transform:uppercase;font-size:8px;letter-spacing:.8px;border-radius:3px;padding:2px 6px;background:#ececf0;color:#5f6270;margin-right:8px;vertical-align:2px}.provider.anthropic{background:#f8e4d8;color:#905836}.provider.google{background:#e4eefc;color:#3860a2}.provider.openai{background:#e0efe9;color:#357459}.status{font-size:10px;border-radius:30px;padding:4px 9px;background:#efefef;color:#70737b}.status.partial{background:#fff1d9;color:#a16914}.status.complete{background:#e2f3e8;color:#24794b}.score{min-width:210px}.score>span{font-size:20px;font-variant-numeric:tabular-nums}.track{height:5px;background:#efedf5;border-radius:3px;max-width:210px;margin-top:5px}.track i{display:block;height:5px;border-radius:3px;background:var(--blue);transition:width .25s}.method-note{font-size:12px;color:var(--muted);max-width:940px;margin-top:16px}.empty,.notice{border:1px dashed #c9c8d0;background:#f0eff6;padding:20px;color:var(--muted);font-size:13px;border-radius:8px}.notice{margin-bottom:32px}.dimensions-intro{border-top:1px solid var(--line);padding-top:52px;margin-bottom:44px}.dimensions-intro h2{font-family:Georgia,serif;font-size:42px;font-style:italic}.dimension{padding-bottom:44px;border-bottom:1px solid var(--line)}.breakdown{margin-top:24px}.breakdown table th:first-child{position:sticky;left:0;background:#fff;z-index:1}.breakdown thead th:first-child{background:#f0eee8}.breakdown td{text-align:right;min-width:140px}.model-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:16px}.model-card{border:1px solid var(--line);background:#fff;padding:24px;border-radius:8px}.model-card h4{font-size:18px;font-weight:600;margin:10px 0 3px}.model-card code{font-size:10px;color:var(--muted);overflow-wrap:anywhere}.model-card p{font-size:12px;color:var(--muted)}details{font-size:11px}summary{cursor:pointer;color:var(--ink)}details a{text-underline-offset:3px}footer{border-top:1px solid var(--line);padding:35px 0 45px;display:flex;align-items:start;gap:35px;justify-content:space-between}footer p{font-size:11px;color:var(--muted);margin:0}footer details{max-width:400px}footer code{font-size:9px;overflow-wrap:anywhere}@media(max-width:900px){main{padding:0 24px}.hero{padding-top:28px}h1{letter-spacing:-3px}.model-grid{grid-template-columns:repeat(2,1fr)}.section-heading{align-items:start}.sheet-link{white-space:normal;max-width:130px}.hero-bottom{align-items:start;flex-direction:column;gap:20px}footer{flex-wrap:wrap}}@media(max-width:560px){.topbar{padding:0 20px;height:68px}nav{gap:13px}nav a{font-size:10px}.brand{font-size:15px}.brand span{width:30px;line-height:30px;font-size:20px}main{padding:0 18px}.hero-bottom>p{font-size:15px}h1{font-size:54px;letter-spacing:-3px}.stats{grid-template-columns:repeat(2,1fr);margin-top:30px}.stats div{padding:16px 0}.stats strong{font-size:28px}h2{font-size:25px}h3{font-size:27px}.section-heading{flex-wrap:wrap;gap:12px}.model-grid{grid-template-columns:1fr}.dimensions-intro h2{font-size:34px}section{margin-bottom:44px}.sheet-link{max-width:none}.metric-label{width:100%;justify-content:space-between}footer{gap:22px}}
.notice code,.overview details p{overflow-wrap:anywhere;white-space:normal}
'''

_SCRIPT = '''
const report=JSON.parse(document.getElementById('benchmark-data').textContent);
const percent=value=>value===null?'—':(value*100).toFixed(1)+'%';
document.getElementById('metric').addEventListener('change',event=>{
  const key=event.target.value;
  document.getElementById('metric-heading').textContent=event.target.selectedOptions[0].textContent;
  document.querySelectorAll('.score[data-model]').forEach(cell=>{
    const model=report.models.find(model=>model.id===cell.dataset.model);
    cell.querySelector('span').textContent=percent(model.metrics[key]);
    cell.querySelector('i').style.width=(model.metrics[key]===null?0:model.metrics[key]*100)+'%';
  });
  document.querySelectorAll('.breakdown').forEach(container=>{
    const section=report.sections.find(section=>section.id===container.dataset.section);
    container.querySelectorAll('tbody tr').forEach((row,index)=>{
      const group=section.groups[index];
      row.querySelectorAll('td').forEach((cell,modelIndex)=>{
        const result=group.models[report.models[modelIndex].id];
        cell.firstChild.textContent=percent(result.metrics[key]);
      });
    });
  });
});
'''


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", default="1.0.0", help="Frozen version to aggregate across dated runs")
    parser.add_argument("--manifest", help="Inspect an explicit manifest and one results directory")
    parser.add_argument("--results-dir", default="results/runs")
    parser.add_argument("--output-dir", default="site")
    parser.add_argument("--config", default="config/models.json")
    args = parser.parse_args()
    report = (build_page(args.manifest, args.results_dir, args.output_dir, args.config) if args.manifest
              else build_release_page(args.release, args.results_dir, args.output_dir))
    print(f'Built {Path(args.output_dir) / "index.html"}: {report["total_inputs"]} inputs, {len(report["models"])} models')


if __name__ == "__main__":
    main()
