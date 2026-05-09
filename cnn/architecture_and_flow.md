# CNN Architecture & Data Flow

This document details exactly how a **3000 x 3000 pixel** input image is processed by our `VanillaDeepCNN` model, including every mathematical transformation, shape change, and value calculation.

## 1. Input Processing (The "Destructive" Phase)

The model **does not** ingest 3000x3000px images directly. The computational cost would be astronomical ($3000^2$ pixels vs $224^2$ pixels is a ~180x difference).

### Step 1: Resizing & Normalization

**Input:** `Raw Image` ($3000 \times 3000 \times 3$, uint8, [0-255])

1.  **Resize (Bilinear Interpolation):**
    The image is squashed to the configured target size (default: $224 \times 224$).
    $$ \text{New Shape} = (224, 224, 3) $$
    - _Note:_ This step discards ~99.4% of the original pixel data. Fine details of tiny colonies might be lost here if they are smaller than $\approx 13 \times 13$ pixels in the original image ($3000/224 \approx 13.4$).

2.  **Normalization (Z-Score):**
    Pixel values are scaled to a standard distribution (ImageNet stats);
    $$ x\_{norm} = \frac{(x/255.0) - \mu}{\sigma} $$
    - $\mu = [0.485, 0.456, 0.406]$
    - $\sigma = [0.229, 0.224, 0.225]$
    - **Output Tensor:** `(3, 224, 224)`, float32.

---

## 2. Feature Extraction (The "Conv" Body)

The tensor passes through **8 Convolutional Blocks**. Each block performs feature compression.

**Block Formula:**

1.  **Conv2d:** $OutputSize = \lfloor\frac{W + 2P - K}{S} + 1\rfloor$
    - $K=3, P=1, S=1$ $\rightarrow$ Size Preserved ($224 \to 224$).
    - **Value Transform:** $y = \sum(w \cdot x) + b$. (Core feature detection).
2.  **ReLU:** $y = \max(0, x)$. (Adds non-linearity).
3.  **MaxPool:** $S=2, K=2$. Halves dimensions.
    - $224 \to 112$.

### Layer-by-Layer Tensor Flow

| Layer     | Input Size $(C \times H \times W)$ | Operation   | Output Size                | Calculations / Notes                     |
| :-------- | :--------------------------------- | :---------- | :------------------------- | :--------------------------------------- |
| **Input** | $3 \times 224 \times 224$          | **Block 1** | $32 \times 112 \times 112$ | 32 filters learn basic edges/colors.     |
| **B2**    | $32 \times 112 \times 112$         | **Block 2** | $64 \times 56 \times 56$   | Filters doubled. Detecting curves/blobs. |

### ❓ How did 32 become 64?

This increase is **intentional design**, defined by the code, not a mathematical side-effect.

- **Input:** 32 channels (from Block 1).
- **Layer:** `nn.Conv2d(in_channels=32, out_channels=64, ...)`
- **Mechanism:** The layer creates **64 separate 3D filters**.
  - Each filter has shape: $32 \times 3 \times 3$.
  - Each filter sweeps across the input and produces **1 feature map**.
  - $64 \text{ filters} \times 1 \text{ map each} = 64 \text{ output channels}$.

| **B3** | $64 \times 56 \times 56$ | **Block 3** | $128 \times 28 \times 28$ | Complex textures. |
| **B4** | $128 \times 28 \times 28$ | **Block 4** | $256 \times 14 \times 14$ | High-level parts. |
| **B5** | $256 \times 14 \times 14$ | **Block 5** | $512 \times 7 \times 7$ | Semantic "colony" features. |
| **B6** | $512 \times 7 \times 7$ | **Block 6** | $512 \times 3 \times 3$ | $7 \xrightarrow{\text{pool}} 3$. |
| **B7** | $512 \times 3 \times 3$ | **Block 7** | $512 \times 1 \times 1$ | $3 \xrightarrow{\text{pool}} 1$. **Spatial Info Gone.** |
| **GAP** | $512 \times 1 \times 1$ | **AdaptiveAvgPool** | $512 \times 1 \times 1$ | Ensures $1 \times 1$ size regardless of input. |
| **Flat** | $512 \times 1 \times 1$ | **Flatten** | $512$ (Vector) | Ready for Dense classification. |

---

## 3. The Heads (Decision Making)

The single 512-vector splits into two task-specific heads.

### A. Shared Fully Connected

$$ x = \text{ReLU}(\text{Linear}(512 \to 512)) $$
**Dropout (0.4):** Randomly zeros 40% of neurons during training to prevent overfitting.

### B. Regression Head (Counting)

1.  **Linear:** $512 \to 256$
2.  **ReLU + Dropout**
3.  **Linear:** $256 \to 1$ (Scalar Output)
    - **Value:** Predicting the raw count (e.g., "45.2").
    - **Final Calc:** The loss function (`SmoothL1Loss`) forces this value to match the ground truth.

### C. Classification Head (Species)

1.  **Linear:** $512 \to 256$
2.  **ReLU + Dropout**
3.  **Linear:** $256 \to 7$ (Num Classes)
    - **Output:** Logits (Raw scores) for each class (e.g., `[2.1, -0.5, 5.4, ...]`).
    - **Softmax:** $\sigma(z)_i = \frac{e^{z_i}}{\sum e^{z_j}}$ transforms logits into probabilities.
    - **Prediction:** `argmax` takes the highest probability.

---

## 4. Concrete Example: Tracing a 1000x1000 Image

Let's verify the math with detailed inputs.
**Scenario:** You upload a standard lab photo: `plate_001.jpg` ($1000 \text{px} \times 1000 \text{px}$).

### Step 1: Pre-Network Transform (Critical Data Loss)

The network **never sees** the 1000x1000 image.

- **Original Pixels:** $1,000,000$ pixels.
- **Operation:** `A.Resize(224, 224)`
- **New Pixels:** $224 \times 224 = 50,176$ pixels.
- **Data Lost:** $\approx 95\%$ of the original information is discarded immediately.
  - _Implication:_ A colony that was $4 \times 4$ pixels (16 px area) in the original image is now $0.8 \times 0.8$ pixels. It effectively vanishes or becomes a single gray sub-pixel.

### Step 2: The Tensor Journey

| Stage       | Input Shape      | Transformation Math                                                                                                            |
| :---------- | :--------------- | :----------------------------------------------------------------------------------------------------------------------------- |
| **Input**   | $(3, 224, 224)$  | Normalized RGB values.                                                                                                         |
| **Block 1** | $(32, 112, 112)$ | `Conv` (32 filters) $\to$ `MaxPool` (/2). <br>Size: $224/2 = 112$. Channels: $3 \to 32$.                                       |
| **Block 2** | $(64, 56, 56)$   | `Conv` (64 filters) $\to$ `MaxPool` (/2). <br>Size: $112/2 = 56$. Channels: $32 \to 64$.                                       |
| **Block 3** | $(128, 28, 28)$  | `Conv` (128 filters) $\to$ `MaxPool` (/2). <br>Size: $56/2 = 28$. Channels: $64 \to 128$.                                      |
| **Block 4** | $(256, 14, 14)$  | `Conv` (256 filters) $\to$ `MaxPool` (/2). <br>Size: $28/2 = 14$. Channels: $128 \to 256$.                                     |
| **Block 5** | $(512, 7, 7)$    | `Conv` (512 filters) $\to$ `MaxPool` (/2). <br>Size: $14/2 = 7$. Channels: $256 \to 512$.                                      |
| **Block 6** | $(512, 3, 3)$    | `MaxPool` (/2). $\lfloor 7/2 \rfloor + 1 = 4$? No, typically floor(7/2) = 3.                                                   |
| **Block 7** | $(512, 1, 1)$    | `MaxPool` (/2) on 3px. $\lfloor 3/2 \rfloor = 1$.                                                                              |
| **Flatten** | $(512)$          | The spatial "image" is now just a list of 512 numbers representing abstract features (e.g., "circularity", "color intensity"). |

### Step 3: The Prediction (Example Values)

The 512-vector enters the heads.

**1. Counting Head:**

- Input: `[0.45, -1.2, 3.3, ...]` (512 values)
- Calculation: $w_1(0.45) + w_2(-1.2) + ... + b$
- **Result:** `42.7`
- _Interpretation:_ "I see roughly 43 colonies."

**2. Classification Head:**

- Input: `[0.45, -1.2, 3.3, ...]`
- Logits Output: `[ -2.0,  5.1,   0.1,  -1.5,  2.2,   -3.0,  0.0 ]`
  (B.sub, C.alb, Cont, Defect, E.coli, P.aer, S.aur)
- Softmax Probabilities:
  - **C.albicans:** $94\%$ (Logit 5.1 is highest)
  - **E.coli:** $5\%$ (Logit 2.2 is second)
  - Others: $<1\%$
