> **Invalid historical result.** This unversioned prototype scorecard is excluded from FontBench V1.0.0. See [historical classifications](historical.json).

# FontBench-1 Scorecard: `gemini-2.5-pro`

- **Evaluated At**: 2026-09-07 11:37:26 UTC
- **Overall Accuracy**: **4/30 (13.3%)**
- **Average Latency**: 22.70s / task

## 1. Accuracy by Container Width

| Width Slice | Tasks | Accuracy |
|---|---|---|
| `medium` | 10 | 10.0% |
| `narrow` | 10 | 10.0% |
| `wide` | 10 | 20.0% |

## 2. Accuracy by Font Category

| Category | Tasks | Accuracy |
|---|---|---|
| `handwriting` | 3 | 33.3% |
| `monospace` | 3 | 33.3% |
| `sans-serif` | 15 | 13.3% |
| `serif` | 9 | 0.0% |

## 3. Per-Font Accuracy

| Font | Category | Accuracy | Predictions |
|---|---|---|---|
| **Arial** | sans-serif | 0.0% | `Inter`, `Inter`, `Inter` |
| **Comic Sans MS** | handwriting | 33.3% | `Quicksand`, `Nunito`, `Comic Sans MS` |
| **Courier New** | monospace | 33.3% | `Courier`, `IBM Plex Mono`, `IBM Plex Mono` |
| **Georgia** | serif | 0.0% | `Lora`, `Lora`, `Lora` |
| **Helvetica** | sans-serif | 0.0% | `Inter`, `Inter`, `San Francisco` |
| **Inter** | sans-serif | 66.7% | `Poppins`, `Inter`, `Inter` |
| **Montserrat** | sans-serif | 0.0% | `Poppins`, `Poppins`, `Poppins` |
| **Playfair Display** | serif | 0.0% | `Lora`, `Lora`, `Garamond` |
| **Roboto** | sans-serif | 0.0% | `Inter`, `Montserrat`, `Circular` |
| **Times New Roman** | serif | 0.0% | `Garamond`, `Garamond`, `Minion` |

## 4. Full Task Log

| Task ID | Target Font | Prediction | Pass/Fail | Latency |
|---|---|---|---|---|
| `font-arial-narrow` | Arial | `Inter` | ❌ FAIL | 67.31s |
| `font-arial-medium` | Arial | `Inter` | ❌ FAIL | 15.32s |
| `font-arial-wide` | Arial | `Inter` | ❌ FAIL | 21.43s |
| `font-helvetica-narrow` | Helvetica | `Inter` | ❌ FAIL | 16.22s |
| `font-helvetica-medium` | Helvetica | `Inter` | ❌ FAIL | 19.15s |
| `font-helvetica-wide` | Helvetica | `San Francisco` | ❌ FAIL | 17.19s |
| `font-times-new-roman-narrow` | Times New Roman | `Garamond` | ❌ FAIL | 110.18s |
| `font-times-new-roman-medium` | Times New Roman | `Garamond` | ❌ FAIL | 16.66s |
| `font-times-new-roman-wide` | Times New Roman | `Minion` | ❌ FAIL | 14.68s |
| `font-georgia-narrow` | Georgia | `Lora` | ❌ FAIL | 26.87s |
| `font-georgia-medium` | Georgia | `Lora` | ❌ FAIL | 13.55s |
| `font-georgia-wide` | Georgia | `Lora` | ❌ FAIL | 19.88s |
| `font-courier-new-narrow` | Courier New | `Courier` | ✅ PASS | 34.55s |
| `font-courier-new-medium` | Courier New | `IBM Plex Mono` | ❌ FAIL | 13.41s |
| `font-courier-new-wide` | Courier New | `IBM Plex Mono` | ❌ FAIL | 14.81s |
| `font-comic-sans-ms-narrow` | Comic Sans MS | `Quicksand` | ❌ FAIL | 16.51s |
| `font-comic-sans-ms-medium` | Comic Sans MS | `Nunito` | ❌ FAIL | 16.06s |
| `font-comic-sans-ms-wide` | Comic Sans MS | `Comic Sans MS` | ✅ PASS | 10.99s |
| `font-roboto-narrow` | Roboto | `Inter` | ❌ FAIL | 21.18s |
| `font-roboto-medium` | Roboto | `Montserrat` | ❌ FAIL | 18.89s |
| `font-roboto-wide` | Roboto | `Circular` | ❌ FAIL | 23.72s |
| `font-inter-narrow` | Inter | `Poppins` | ❌ FAIL | 14.20s |
| `font-inter-medium` | Inter | `Inter` | ✅ PASS | 19.70s |
| `font-inter-wide` | Inter | `Inter` | ✅ PASS | 17.90s |
| `font-playfair-display-narrow` | Playfair Display | `Lora` | ❌ FAIL | 16.33s |
| `font-playfair-display-medium` | Playfair Display | `Lora` | ❌ FAIL | 14.79s |
| `font-playfair-display-wide` | Playfair Display | `Garamond` | ❌ FAIL | 15.30s |
| `font-montserrat-narrow` | Montserrat | `Poppins` | ❌ FAIL | 16.16s |
| `font-montserrat-medium` | Montserrat | `Poppins` | ❌ FAIL | 23.95s |
| `font-montserrat-wide` | Montserrat | `Poppins` | ❌ FAIL | 14.02s |