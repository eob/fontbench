# FontBench-1 Scorecard: `gemini-2.5-flash`

- **Evaluated At**: 2026-09-07 11:24:52 UTC
- **Overall Accuracy**: **6/30 (20.0%)**
- **Average Latency**: 7.27s / task

## 1. Accuracy by Container Width

| Width Slice | Tasks | Accuracy |
|---|---|---|
| `medium` | 10 | 20.0% |
| `narrow` | 10 | 30.0% |
| `wide` | 10 | 10.0% |

## 2. Accuracy by Font Category

| Category | Tasks | Accuracy |
|---|---|---|
| `handwriting` | 3 | 0.0% |
| `monospace` | 3 | 0.0% |
| `sans-serif` | 15 | 20.0% |
| `serif` | 9 | 33.3% |

## 3. Per-Font Accuracy

| Font | Category | Accuracy | Predictions |
|---|---|---|---|
| **Arial** | sans-serif | 0.0% | `Roboto`, `Roboto`, `Roboto` |
| **Comic Sans MS** | handwriting | 0.0% | `Indie Flower`, `Coming Soon`, `Architects Daughter` |
| **Courier New** | monospace | 0.0% | `Consolas`, `Consolas`, `Source Code Pro` |
| **Georgia** | serif | 0.0% | `Source Serif Pro`, `Lora`, `Playfair Display` |
| **Helvetica** | sans-serif | 0.0% | `Roboto`, `Montserrat`, `Roboto` |
| **Inter** | sans-serif | 33.3% | `Inter`, `Lato`, `Roboto` |
| **Montserrat** | sans-serif | 0.0% | `Poppins`, `Roboto`, `Open Sans` |
| **Playfair Display** | serif | 33.3% | `Playfair Display`, `Lora`, `Times New Roman` |
| **Roboto** | sans-serif | 66.7% | `Inter`, `Roboto`, `Roboto` |
| **Times New Roman** | serif | 66.7% | `Times New Roman`, `Times New Roman`, `Minion Pro` |

## 4. Full Task Log

| Task ID | Target Font | Prediction | Pass/Fail | Latency |
|---|---|---|---|---|
| `font-arial-narrow` | Arial | `Roboto` | ❌ FAIL | 5.64s |
| `font-arial-medium` | Arial | `Roboto` | ❌ FAIL | 10.45s |
| `font-arial-wide` | Arial | `Roboto` | ❌ FAIL | 5.77s |
| `font-helvetica-narrow` | Helvetica | `Roboto` | ❌ FAIL | 6.15s |
| `font-helvetica-medium` | Helvetica | `Montserrat` | ❌ FAIL | 11.67s |
| `font-helvetica-wide` | Helvetica | `Roboto` | ❌ FAIL | 6.83s |
| `font-times-new-roman-narrow` | Times New Roman | `Times New Roman` | ✅ PASS | 6.66s |
| `font-times-new-roman-medium` | Times New Roman | `Times New Roman` | ✅ PASS | 4.16s |
| `font-times-new-roman-wide` | Times New Roman | `Minion Pro` | ❌ FAIL | 6.10s |
| `font-georgia-narrow` | Georgia | `Source Serif Pro` | ❌ FAIL | 9.80s |
| `font-georgia-medium` | Georgia | `Lora` | ❌ FAIL | 7.62s |
| `font-georgia-wide` | Georgia | `Playfair Display` | ❌ FAIL | 11.00s |
| `font-courier-new-narrow` | Courier New | `Consolas` | ❌ FAIL | 5.12s |
| `font-courier-new-medium` | Courier New | `Consolas` | ❌ FAIL | 4.17s |
| `font-courier-new-wide` | Courier New | `Source Code Pro` | ❌ FAIL | 12.22s |
| `font-comic-sans-ms-narrow` | Comic Sans MS | `Indie Flower` | ❌ FAIL | 4.97s |
| `font-comic-sans-ms-medium` | Comic Sans MS | `Coming Soon` | ❌ FAIL | 4.71s |
| `font-comic-sans-ms-wide` | Comic Sans MS | `Architects Daughter` | ❌ FAIL | 6.73s |
| `font-roboto-narrow` | Roboto | `Inter` | ❌ FAIL | 11.13s |
| `font-roboto-medium` | Roboto | `Roboto` | ✅ PASS | 5.57s |
| `font-roboto-wide` | Roboto | `Roboto` | ✅ PASS | 8.06s |
| `font-inter-narrow` | Inter | `Inter` | ✅ PASS | 9.02s |
| `font-inter-medium` | Inter | `Lato` | ❌ FAIL | 6.98s |
| `font-inter-wide` | Inter | `Roboto` | ❌ FAIL | 5.85s |
| `font-playfair-display-narrow` | Playfair Display | `Playfair Display` | ✅ PASS | 7.63s |
| `font-playfair-display-medium` | Playfair Display | `Lora` | ❌ FAIL | 8.36s |
| `font-playfair-display-wide` | Playfair Display | `Times New Roman` | ❌ FAIL | 5.41s |
| `font-montserrat-narrow` | Montserrat | `Poppins` | ❌ FAIL | 9.42s |
| `font-montserrat-medium` | Montserrat | `Roboto` | ❌ FAIL | 5.43s |
| `font-montserrat-wide` | Montserrat | `Open Sans` | ❌ FAIL | 5.53s |