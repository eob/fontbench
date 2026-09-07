# FontBench-1 Scorecard: `gemini-3.5-flash-lite`

- **Evaluated At**: 2026-09-07 11:26:25 UTC
- **Overall Accuracy**: **12/30 (40.0%)**
- **Average Latency**: 0.74s / task

## 1. Accuracy by Container Width

| Width Slice | Tasks | Accuracy |
|---|---|---|
| `medium` | 10 | 30.0% |
| `narrow` | 10 | 50.0% |
| `wide` | 10 | 40.0% |

## 2. Accuracy by Font Category

| Category | Tasks | Accuracy |
|---|---|---|
| `handwriting` | 3 | 100.0% |
| `monospace` | 3 | 100.0% |
| `sans-serif` | 15 | 13.3% |
| `serif` | 9 | 44.4% |

## 3. Per-Font Accuracy

| Font | Category | Accuracy | Predictions |
|---|---|---|---|
| **Arial** | sans-serif | 0.0% | `Roboto`, `Roboto`, `Roboto` |
| **Comic Sans MS** | handwriting | 100.0% | `Comic Sans MS`, `Comic Sans MS`, `Comic Sans` |
| **Courier New** | monospace | 100.0% | `Courier`, `Courier New`, `Courier` |
| **Georgia** | serif | 33.3% | `Georgia`, `Times New Roman`, `Times New Roman` |
| **Helvetica** | sans-serif | 0.0% | `Inter`, `Inter`, `Inter` |
| **Inter** | sans-serif | 0.0% | `Roboto`, `Roboto`, `Arial` |
| **Montserrat** | sans-serif | 33.3% | `Futura`, `Comfortaa`, `Montserrat` |
| **Playfair Display** | serif | 0.0% | `Merriweather`, `Georgia`, `Georgia` |
| **Roboto** | sans-serif | 33.3% | `Roboto`, `Inter`, `Inter` |
| **Times New Roman** | serif | 100.0% | `Times New Roman`, `Times New Roman`, `Times New Roman` |

## 4. Full Task Log

| Task ID | Target Font | Prediction | Pass/Fail | Latency |
|---|---|---|---|---|
| `font-arial-narrow` | Arial | `Roboto` | ❌ FAIL | 1.08s |
| `font-arial-medium` | Arial | `Roboto` | ❌ FAIL | 1.31s |
| `font-arial-wide` | Arial | `Roboto` | ❌ FAIL | 1.24s |
| `font-helvetica-narrow` | Helvetica | `Inter` | ❌ FAIL | 1.57s |
| `font-helvetica-medium` | Helvetica | `Inter` | ❌ FAIL | 1.17s |
| `font-helvetica-wide` | Helvetica | `Inter` | ❌ FAIL | 0.75s |
| `font-times-new-roman-narrow` | Times New Roman | `Times New Roman` | ✅ PASS | 0.64s |
| `font-times-new-roman-medium` | Times New Roman | `Times New Roman` | ✅ PASS | 0.57s |
| `font-times-new-roman-wide` | Times New Roman | `Times New Roman` | ✅ PASS | 0.65s |
| `font-georgia-narrow` | Georgia | `Georgia` | ✅ PASS | 0.59s |
| `font-georgia-medium` | Georgia | `Times New Roman` | ❌ FAIL | 0.70s |
| `font-georgia-wide` | Georgia | `Times New Roman` | ❌ FAIL | 0.63s |
| `font-courier-new-narrow` | Courier New | `Courier` | ✅ PASS | 0.67s |
| `font-courier-new-medium` | Courier New | `Courier New` | ✅ PASS | 0.57s |
| `font-courier-new-wide` | Courier New | `Courier` | ✅ PASS | 0.71s |
| `font-comic-sans-ms-narrow` | Comic Sans MS | `Comic Sans MS` | ✅ PASS | 0.44s |
| `font-comic-sans-ms-medium` | Comic Sans MS | `Comic Sans MS` | ✅ PASS | 0.77s |
| `font-comic-sans-ms-wide` | Comic Sans MS | `Comic Sans` | ✅ PASS | 0.51s |
| `font-roboto-narrow` | Roboto | `Roboto` | ✅ PASS | 0.67s |
| `font-roboto-medium` | Roboto | `Inter` | ❌ FAIL | 0.72s |
| `font-roboto-wide` | Roboto | `Inter` | ❌ FAIL | 0.58s |
| `font-inter-narrow` | Inter | `Roboto` | ❌ FAIL | 0.58s |
| `font-inter-medium` | Inter | `Roboto` | ❌ FAIL | 0.59s |
| `font-inter-wide` | Inter | `Arial` | ❌ FAIL | 0.54s |
| `font-playfair-display-narrow` | Playfair Display | `Merriweather` | ❌ FAIL | 0.70s |
| `font-playfair-display-medium` | Playfair Display | `Georgia` | ❌ FAIL | 0.68s |
| `font-playfair-display-wide` | Playfair Display | `Georgia` | ❌ FAIL | 0.70s |
| `font-montserrat-narrow` | Montserrat | `Futura` | ❌ FAIL | 0.53s |
| `font-montserrat-medium` | Montserrat | `Comfortaa` | ❌ FAIL | 0.74s |
| `font-montserrat-wide` | Montserrat | `Montserrat` | ✅ PASS | 0.59s |