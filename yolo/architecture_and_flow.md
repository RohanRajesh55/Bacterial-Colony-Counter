# YOLOv8 Architecture & Data Flow

This document details exactly how a **3000 x 3000 pixel** input image is processed by our **YOLOv8** model. Unlike the CNN, YOLO preserves spatial information to perform _localization_.

## 1. Input Processing (Smart Tiling)

YOLO cannot process 3000x3000px directly in real-time. We have two strategies:

### A. Letterbox Resize (Standard)

1.  **Scale:** Resize longest dimension (3000) to target (e.g., 640 or 1024).
    - Scale Factor: $640 / 3000 = 0.213$.
2.  **Pad:** Add gray pixels to shorter dimension to satisfy stride constraints (divisible by 32).
    - **Result:** A $640 \times 640 \times 3$ tensor.
    - _Trade-off:_ Tiny colonies (< 5px) may disappear.

### B. Patching (High Accuracy - _The "Paper" Method_)

As seen in the YOLOv8x analysis, we can chop the 3000x3000px image into overlapping **512x512 tiles**.

- **Grid:** $\approx 6 \times 6 = 36$ patches.
- Each patch is processed _independently_ as a mini-image.

---

## 2. Backbone (CSPDarknet Feature Pyramid)

The image passes through the **Backbone**, which creates a "Pyramid" of features at different scales (P3, P4, P5).

**Key Math: Stride (`S`)**
Stride is the ratio of Input Size to Feature Map Size. It determines the "receptive field".

| Stage    | Stride | Input Res (Example) | Feature Map Size           | What it sees              |
| :------- | :----- | :------------------ | :------------------------- | :------------------------ |
| **Stem** | -      | $640 \times 640$    | -                          | Raw Pixels                |
| **P3**   | 8      | $640 / 8$           | $80 \times 80 \times 256$  | **Small Colonies**        |
| **P4**   | 16     | $640 / 16$          | $40 \times 40 \times 512$  | **Medium Colonies**       |
| **P5**   | 32     | $640 / 32$          | $20 \times 20 \times 1024$ | **Large Blobs / Context** |

---

## 3. The Head (Anchor-Free Detection)

YOLOv8 uses a **Decoupled Head**. For _every single cell_ in the P3, P4, and P5 feature maps, it predicts:

$$ \text{Total Predictions} = (80 \times 80) + (40 \times 40) + (20 \times 20) = 8,400 \text{ predictions} $$

### A. Classification Branch (BCE Loss)

- **Input:** Feature vector for grid cell $(i, j)$.
- **Operation:** Conv2d $1 \times 1$.
- **Output:** 7 probabilities (one for each class).
- **Math:** Sigmoid activation $\sigma(x)$.

### B. Regression Branch (DFL Loss)

- **Input:** Feature vector for grid cell $(i, j)$.
- **Operation:** Predicts distance from cell center to box edges: $(l, t, r, b)$.
- **Distribution Focal Loss (DFL):** Instead of a single number, it predicts a probabilistic distribution of values to handle ambiguity at colony edges.

---

## 4. Post-Processing (NMS)

We now have 8,400 boxes. Most are garbage.

1.  **Confidence Threshold:** Discard all boxes with `conf < 0.25`.
2.  **NMS (Non-Maximum Suppression):**
    - **Problem:** One colony might be detected 5 times by adjacent grid cells.
    - **Math (IoU):** $\text{IoU} = \frac{\text{Area of Intersection}}{\text{Area of Union}}$.
    - **Algorithm:**
      1.  Pick box with highest score.
      2.  Compare IoU with all other overlapping boxes.
      3.  If $\text{IoU} > 0.45$ (they overlap heavily), discard the lower-score box.
    - **Result:** One clean box per colony.

## Summary of Flow (3000px Input)

1.  **Image:** 3000x3000px
2.  **Resize:** 640x640 Feature Map
3.  **Backbone:** P3(80x80), P4(40x40), P5(20x20)
4.  **Head:** 8,400 raw predictions.
5.  **NMS:** Filters down to ~300 final colonies.
