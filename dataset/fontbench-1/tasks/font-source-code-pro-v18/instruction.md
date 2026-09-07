# FontBench-1 Task: Identify Rendered Typographic Properties

Examine the rendered text sample located at `./sample.png`.

The image displays the English pangram:
> *"The quick brown fox jumps over the lazy dog."*

### Your Objective
Identify the 6 typographic properties used to typeset this text:
1. **font**: The canonical font family name (e.g., Arial, Times New Roman, Roboto, Georgia, etc.)
2. **category**: Exactly one of [serif, non-serif, mono, handwriting, other]
3. **weight**: Exactly one of [thin, regular, bold, black]
4. **modifier**: Exactly one of [regular, italic, underline, strikethrough, small-caps]
5. **kerning**: Exactly one of [tight, normal, loose]
6. **line_height**: Exactly one of [tight, normal, loose]

### Required Output
Write **only** a valid JSON object into `/workspace/output.json` (or `./output.json`):

```json
{
  "font": "Source Code Pro",
  "category": "mono",
  "weight": "regular",
  "modifier": "underline",
  "kerning": "loose",
  "line_height": "tight"
}
```
