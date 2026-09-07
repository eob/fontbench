# FontBench-1 Scorecard: `gemini-3.5-flash`

- **Evaluated At**: 2026-09-07 11:26:13 UTC
- **Overall Accuracy**: **18/30 (60.0%)**
- **Average Latency**: 10.05s / task

## 1. Accuracy by Container Width

| Width Slice | Tasks | Accuracy |
|---|---|---|
| `medium` | 10 | 60.0% |
| `narrow` | 10 | 60.0% |
| `wide` | 10 | 60.0% |

## 2. Accuracy by Font Category

| Category | Tasks | Accuracy |
|---|---|---|
| `handwriting` | 3 | 66.7% |
| `monospace` | 3 | 100.0% |
| `sans-serif` | 15 | 26.7% |
| `serif` | 9 | 100.0% |

## 3. Per-Font Accuracy

| Font | Category | Accuracy | Predictions |
|---|---|---|---|
| **Arial** | sans-serif | 33.3% | `Based on the letter shapes (such as the double-story "a", single-story "g", horizontal terminals on "s", "e", and "c", and the distinct condensed proportions), the font family used is **Roboto** (specifically, **Roboto Condensed**).`, `Roboto`, `Arial` |
| **Comic Sans MS** | handwriting | 66.7% | `Comic Sans MS`, `Comic Sans MS`, `Based on the distinctive, cleaned-up casual handwriting style with uniform monoline strokes and rounded terminals, the primary font family used is:

**Comic Neue**` |
| **Courier New** | monospace | 100.0% | `Courier`, `Courier New`, `Courier New` |
| **Georgia** | serif | 100.0% | `Georgia`, `Georgia`, `Based on the letterforms—specifically the generous x-height, the prominent ball terminals on letters like **r**, **c**, and **a**, and the design of the lowercase **g** and **j**—the primary font family used in this image is **Georgia**.` |
| **Helvetica** | sans-serif | 0.0% | `Gilroy`, `Inter`, `Open Sans` |
| **Inter** | sans-serif | 66.7% | `Based on the specific letterforms (such as the square dots on the `i` and `j`, the square period, the single-story `g`, and the clean neo-grotesque design), the primary font family used to typeset this text is **Inter**.`, `Based on the clean, neo-grotesque geometric design (specifically the double-story lowercase "a", single-story "g", flat horizontal terminals on "c" and "e", and the shape of the "t" and "y"), the font used is:

**Inter**`, `Roboto` |
| **Montserrat** | sans-serif | 0.0% | `Poppins`, `Poppins`, `Poppins` |
| **Playfair Display** | serif | 100.0% | `Playfair Display`, `Based on the distinct typographic features—such as the high contrast between thick and thin strokes, the teardrop terminals on the lowercase **k**, **x**, and **y**, and the elegant double-story **g**—the primary font family used in the image is **Playfair Display**.`, `Playfair Display` |
| **Roboto** | sans-serif | 33.3% | `Based on the distinctive features of the letters (such as the square dots on the **i** and **j**, the two-story **a**, the single-story **g**, the specific leg-joint on the **k**, and the overall neutral neo-grotesque design), the font used is:

**Inter**`, `Inter`, `Roboto` |
| **Times New Roman** | serif | 100.0% | `Times New Roman`, `Times New Roman`, `Times New Roman` |

## 4. Full Task Log

| Task ID | Target Font | Prediction | Pass/Fail | Latency |
|---|---|---|---|---|
| `font-arial-narrow` | Arial | `Based on the letter shapes (such as the double-story "a", single-story "g", horizontal terminals on "s", "e", and "c", and the distinct condensed proportions), the font family used is **Roboto** (specifically, **Roboto Condensed**).` | ❌ FAIL | 9.41s |
| `font-arial-medium` | Arial | `Roboto` | ❌ FAIL | 6.68s |
| `font-arial-wide` | Arial | `Arial` | ✅ PASS | 6.95s |
| `font-helvetica-narrow` | Helvetica | `Gilroy` | ❌ FAIL | 22.77s |
| `font-helvetica-medium` | Helvetica | `Inter` | ❌ FAIL | 22.37s |
| `font-helvetica-wide` | Helvetica | `Open Sans` | ❌ FAIL | 7.83s |
| `font-times-new-roman-narrow` | Times New Roman | `Times New Roman` | ✅ PASS | 6.34s |
| `font-times-new-roman-medium` | Times New Roman | `Times New Roman` | ✅ PASS | 6.01s |
| `font-times-new-roman-wide` | Times New Roman | `Times New Roman` | ✅ PASS | 4.33s |
| `font-georgia-narrow` | Georgia | `Georgia` | ✅ PASS | 5.41s |
| `font-georgia-medium` | Georgia | `Georgia` | ✅ PASS | 8.59s |
| `font-georgia-wide` | Georgia | `Based on the letterforms—specifically the generous x-height, the prominent ball terminals on letters like **r**, **c**, and **a**, and the design of the lowercase **g** and **j**—the primary font family used in this image is **Georgia**.` | ✅ PASS | 5.20s |
| `font-courier-new-narrow` | Courier New | `Courier` | ✅ PASS | 4.78s |
| `font-courier-new-medium` | Courier New | `Courier New` | ✅ PASS | 3.23s |
| `font-courier-new-wide` | Courier New | `Courier New` | ✅ PASS | 5.07s |
| `font-comic-sans-ms-narrow` | Comic Sans MS | `Comic Sans MS` | ✅ PASS | 4.83s |
| `font-comic-sans-ms-medium` | Comic Sans MS | `Comic Sans MS` | ✅ PASS | 10.51s |
| `font-comic-sans-ms-wide` | Comic Sans MS | `Based on the distinctive, cleaned-up casual handwriting style with uniform monoline strokes and rounded terminals, the primary font family used is:

**Comic Neue**` | ❌ FAIL | 12.79s |
| `font-roboto-narrow` | Roboto | `Based on the distinctive features of the letters (such as the square dots on the **i** and **j**, the two-story **a**, the single-story **g**, the specific leg-joint on the **k**, and the overall neutral neo-grotesque design), the font used is:

**Inter**` | ❌ FAIL | 10.02s |
| `font-roboto-medium` | Roboto | `Inter` | ❌ FAIL | 9.01s |
| `font-roboto-wide` | Roboto | `Roboto` | ✅ PASS | 12.91s |
| `font-inter-narrow` | Inter | `Based on the specific letterforms (such as the square dots on the `i` and `j`, the square period, the single-story `g`, and the clean neo-grotesque design), the primary font family used to typeset this text is **Inter**.` | ✅ PASS | 22.76s |
| `font-inter-medium` | Inter | `Based on the clean, neo-grotesque geometric design (specifically the double-story lowercase "a", single-story "g", flat horizontal terminals on "c" and "e", and the shape of the "t" and "y"), the font used is:

**Inter**` | ✅ PASS | 8.39s |
| `font-inter-wide` | Inter | `Roboto` | ❌ FAIL | 10.81s |
| `font-playfair-display-narrow` | Playfair Display | `Playfair Display` | ✅ PASS | 7.58s |
| `font-playfair-display-medium` | Playfair Display | `Based on the distinct typographic features—such as the high contrast between thick and thin strokes, the teardrop terminals on the lowercase **k**, **x**, and **y**, and the elegant double-story **g**—the primary font family used in the image is **Playfair Display**.` | ✅ PASS | 8.98s |
| `font-playfair-display-wide` | Playfair Display | `Playfair Display` | ✅ PASS | 7.62s |
| `font-montserrat-narrow` | Montserrat | `Poppins` | ❌ FAIL | 13.71s |
| `font-montserrat-medium` | Montserrat | `Poppins` | ❌ FAIL | 26.61s |
| `font-montserrat-wide` | Montserrat | `Poppins` | ❌ FAIL | 10.04s |