# Understanding RT-DETR v4: A Guide for Undergraduates

## Table of Contents
1. [Introduction: What is Object Detection?](#1-introduction-what-is-object-detection)
2. [The Evolution: From CNNs to Transformers](#2-the-evolution-from-cnns-to-transformers)
3. [RT-DETR v4 Overview](#3-rt-detr-v4-overview)
4. [Component 1: The Backbone (HGNetv2)](#4-component-1-the-backbone-hgnetv2)
5. [Component 2: The Hybrid Encoder](#5-component-2-the-hybrid-encoder)
6. [Component 3: The Transformer Decoder](#6-component-3-the-transformer-decoder)
7. [Component 4: Knowledge Distillation](#7-component-4-knowledge-distillation)
8. [Training: How the Model Learns](#8-training-how-the-model-learns)
9. [Putting It All Together](#9-putting-it-all-together)
10. [Glossary](#10-glossary)

---

## 1. Introduction: What is Object Detection?

Object detection is one of the fundamental tasks in computer vision. Given an image, the goal is to:
1. **Localize** objects (draw bounding boxes around them)
2. **Classify** objects (identify what each object is)

```
Input Image                          Output
┌────────────────────┐              ┌────────────────────┐
│                    │              │   ┌─────┐          │
│     🐕   🐈        │    ────▶     │   │ dog │  ┌───┐   │
│                    │              │   └─────┘  │cat│   │
│                    │              │            └───┘   │
└────────────────────┘              └────────────────────┘
```

For our bacterial colony counting project, we're detecting and counting colonies on petri dishes, classifying them into 7 species.

### Why is this hard?

- Objects can be **any size** (a colony could be 10 or 1000 pixels)
- Objects can **overlap** or be **partially hidden**
- Images have **varying lighting** and **backgrounds**
- We need to be **fast** (real-time) AND **accurate**

---

## 2. The Evolution: From CNNs to Transformers

### 2.1 Traditional CNNs (What You Probably Know)

A Convolutional Neural Network processes images using **convolutional filters** that slide across the image:

```
Input Image        Filter (3x3)       Feature Map
┌─────────────┐    ┌───────┐         ┌─────────┐
│ 1 2 3 4 5 6 │    │ 1 0 1 │         │ ? ? ? ? │
│ 7 8 9 1 2 3 │  * │ 0 1 0 │    =    │ ? ? ? ? │
│ 4 5 6 7 8 9 │    │ 1 0 1 │         │ ? ? ? ? │
└─────────────┘    └───────┘         └─────────┘
```

The convolution operation at position (i,j):

$$\text{Output}_{i,j} = \sum_{m}\sum_{n} \text{Input}_{i+m, j+n} \cdot \text{Filter}_{m,n}$$

**Key limitation**: CNNs have a **limited receptive field**. A 3x3 filter only "sees" 9 pixels at a time. To understand the whole image, you need many stacked layers.

### 2.2 The Attention Mechanism (The Transformer's Secret Weapon)

**Attention** allows the model to look at ALL parts of the image at once and decide what's important.

Think of it like reading a sentence: "The **cat** sat on the **mat** because **it** was tired."

What does "it" refer to? You need to look back at the whole sentence. That's attention!

#### The Math of Attention

Given:
- **Query (Q)**: "What am I looking for?"
- **Key (K)**: "What information do I have?"
- **Value (V)**: "What's the actual content?"

$$\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right) V$$

Where:
- $QK^T$ computes similarity scores between query and all keys
- $\sqrt{d_k}$ is a scaling factor to prevent exploding gradients
- softmax converts scores to probabilities (sum to 1)
- Multiply by V to get weighted combination of values

**Visual intuition**:
```
Query: "Where are the bacterial colonies?"

         Image Positions
         ┌───┬───┬───┬───┐
         │0.1│0.1│0.7│0.1│  ← Attention weights (sum to 1.0)
         └───┴───┴───┴───┘
              ↑
         "High weight here =
          probably a colony!"
```

### 2.3 Why Transformers for Detection?

| Aspect | CNN-based (YOLO, etc.) | Transformer-based (DETR, RT-DETR) |
|--------|----------------------|-----------------------------------|
| Global context | Limited (needs many layers) | Immediate (attention sees everything) |
| Post-processing | Needs NMS (non-maximum suppression) | End-to-end, no NMS needed |
| Small objects | Struggles | Better with multi-scale features |
| Speed | Very fast | Was slow, now competitive |

**RT-DETR** = "Real-Time Detection Transformer" - designed to be as fast as YOLO while leveraging transformer benefits.

---

## 3. RT-DETR v4 Overview

RT-DETR v4 is the 4th generation, published in late 2025. Its key innovation is using **knowledge distillation** from a large Vision Foundation Model (DINOv3).

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            RT-DETR v4                                   │
│                                                                         │
│  ┌──────────┐     ┌─────────────────┐     ┌──────────────────────┐     │
│  │          │     │                 │     │                      │     │
│  │ HGNetv2  │────▶│  Hybrid Encoder │────▶│  Transformer Decoder │────▶ Detections
│  │(Backbone)│     │  (AIFI + Neck)  │     │     (D-FINE)         │     │
│  │          │     │                 │     │                      │     │
│  └──────────┘     └────────┬────────┘     └──────────────────────┘     │
│                            │                                            │
│                            │ During Training Only                       │
│                            ▼                                            │
│                   ┌─────────────────┐                                   │
│                   │   Distillation  │◀─── DINOv3 Teacher                │
│                   │      Loss       │     (Frozen, not updated)         │
│                   └─────────────────┘                                   │
└─────────────────────────────────────────────────────────────────────────┘
```

The model has **three main components**:
1. **Backbone**: Extracts visual features from the image
2. **Encoder**: Enhances and combines features at multiple scales
3. **Decoder**: Predicts bounding boxes and class labels

Plus a **knowledge distillation** mechanism during training.

---

## 4. Component 1: The Backbone (HGNetv2)

### What is a Backbone?

The backbone is the "feature extractor" - it converts raw pixels into meaningful feature representations.

Think of it like this:
- **Input**: 640x640x3 image (RGB pixels)
- **Output**: Multiple feature maps at different resolutions

```
Input Image (640x640x3)
        │
        ▼
┌───────────────────┐
│      Stem         │  Reduces resolution, increases channels
│   (640→160)       │
└───────────────────┘
        │
        ▼
┌───────────────────┐
│     Stage 1       │  Output: 160x160, 64 channels
│  (Low-level)      │  Detects: edges, textures
└───────────────────┘
        │
        ▼
┌───────────────────┐
│     Stage 2       │  Output: 80x80, 256 channels    ──▶ S3 (to encoder)
│  (Mid-level)      │  Detects: shapes, patterns
└───────────────────┘
        │
        ▼
┌───────────────────┐
│     Stage 3       │  Output: 40x40, 512 channels    ──▶ S4 (to encoder)
│  (High-level)     │  Detects: parts of objects
└───────────────────┘
        │
        ▼
┌───────────────────┐
│     Stage 4       │  Output: 20x20, 1024 channels   ──▶ S5 (to encoder)
│  (Semantic)       │  Detects: whole objects, context
└───────────────────┘
```

### Why Multiple Scales Matter

Different sized objects are best detected at different feature map resolutions:

| Feature Map | Resolution | Best For |
|-------------|------------|----------|
| S3 (Stage 2) | 80x80 | Small objects (tiny colonies) |
| S4 (Stage 3) | 40x40 | Medium objects |
| S5 (Stage 4) | 20x20 | Large objects (big colonies, petri dish) |

### HGNetv2's Special Blocks

#### The HG Block (Hierarchical Gradient Block)

```python
# Simplified concept:
class HG_Block:
    def forward(self, x):
        outputs = [x]  # Keep original

        for layer in self.layers:
            x = layer(x)
            outputs.append(x)  # Keep each intermediate result

        # Concatenate ALL outputs (dense connections)
        x = torch.cat(outputs, dim=1)

        # Aggregate with squeeze-excitation attention
        x = self.aggregation(x)
        return x
```

**Why this design?**
- **Dense connections**: Like DenseNet, gradients flow easily during backpropagation
- **Feature reuse**: Earlier features aren't lost
- **ESE (Effective Squeeze-Excitation)**: Channel attention to emphasize important features

#### The Math Behind Channel Attention (ESE)

Given feature map $X \in \mathbb{R}^{C \times H \times W}$:

1. **Global Average Pooling**: Compress spatial dimensions
   $$z_c = \frac{1}{H \times W} \sum_{i=1}^{H} \sum_{j=1}^{W} X_c(i, j)$$

2. **Learn channel importance** via 1x1 convolution:
   $$s = \sigma(W \cdot z)$$
   where $\sigma$ is sigmoid, $W$ is learnable weights

3. **Recalibrate channels**:
   $$\hat{X}_c = s_c \cdot X_c$$

This lets the network learn "this channel detecting edges is more important than this channel detecting color."

---

## 5. Component 2: The Hybrid Encoder

The encoder takes multi-scale features from the backbone and:
1. Enhances them with **attention** (AIFI)
2. Fuses them across scales (FPN + PAN)

### 5.1 AIFI: Attention-based Intra-scale Feature Interaction

AIFI applies a transformer encoder to the **highest-level features** (S5, 20x20).

```
S5 Features (20x20x256)
        │
        ▼ Flatten to sequence
[Batch, 400, 256]  (400 = 20x20 spatial positions)
        │
        ▼ Add positional encoding
        │
        ▼ Transformer Encoder
        │
        ▼ Reshape back
S5' Features (20x20x256) - now with global context!
```

#### Why Only on S5?

Attention has **quadratic complexity**: $O(n^2)$ where n = sequence length.

| Feature Map | Positions | Attention Cost |
|-------------|-----------|----------------|
| S3 (80x80) | 6,400 | 40,960,000 operations |
| S4 (40x40) | 1,600 | 2,560,000 operations |
| S5 (20x20) | 400 | 160,000 operations |

Running attention on S3 would be **256x more expensive** than S5!

#### Positional Encoding

Since attention treats input as a **set** (no inherent order), we add positional information:

$$PE_{(pos, 2i)} = \sin\left(\frac{pos}{10000^{2i/d}}\right)$$
$$PE_{(pos, 2i+1)} = \cos\left(\frac{pos}{10000^{2i/d}}\right)$$

This creates unique patterns for each position that the model can learn to use.

### 5.2 FPN: Feature Pyramid Network (Top-Down)

FPN propagates **semantic information** from high-level to low-level features.

```
S5' (20x20) ─────────────────────────────────────▶ P5 (20x20)
     │
     ▼ Upsample (2x)
     │
S4 ──┼─▶ Concat ──▶ Conv ──────────────────────▶ P4 (40x40)
     │
     ▼ Upsample (2x)
     │
S3 ──┴─▶ Concat ──▶ Conv ──────────────────────▶ P3 (80x80)
```

**Intuition**: S3 has fine spatial details but doesn't know "what" things are. S5 knows "what" but not precise "where". FPN combines both!

### 5.3 PAN: Path Aggregation Network (Bottom-Up)

PAN does the reverse - propagates **fine-grained details** back up:

```
P3 (80x80) ─────────────────────────────────────▶ Output P3
     │
     ▼ Downsample (stride 2)
     │
P4 ──┼─▶ Concat ──▶ Conv ──────────────────────▶ Output P4
     │
     ▼ Downsample (stride 2)
     │
P5 ──┴─▶ Concat ──▶ Conv ──────────────────────▶ Output P5
```

### 5.4 CSP (Cross-Stage Partial) Connections

Instead of processing all features through all layers, CSP splits the features:

```python
def forward(self, x):
    # Split into two parts
    x1 = self.conv1(x)  # Part 1: goes through bottlenecks
    x2 = self.conv2(x)  # Part 2: skip connection

    x1 = self.bottlenecks(x1)

    # Combine
    return self.conv3(x1 + x2)
```

**Why?** Reduces computation by ~50% while maintaining accuracy. Not all information needs heavy processing.

---

## 6. Component 3: The Transformer Decoder

The decoder's job: Given enhanced features, predict bounding boxes and class labels.

### 6.1 Object Queries: The Key Innovation of DETR

Instead of sliding windows or anchor boxes, DETR uses **learned queries**.

Think of queries as "detectives" looking for objects:

```
┌─────────────────────────────────────────────────────┐
│                    Feature Map                       │
│                                                      │
│   Query 1: "Is there an object at my position?"     │
│   Query 2: "Is there an object at my position?"     │
│   ...                                                │
│   Query 300: "Is there an object at my position?"   │
│                                                      │
└─────────────────────────────────────────────────────┘
```

Each query learns to specialize in certain types/locations of objects.

### 6.2 Decoder Layer Structure

Each decoder layer has three main operations:

```
┌────────────────────────────────────────────────────────────┐
│                    Decoder Layer                            │
├────────────────────────────────────────────────────────────┤
│                                                             │
│  Query Embeddings                                           │
│        │                                                    │
│        ▼                                                    │
│  ┌─────────────────┐                                       │
│  │ Self-Attention  │  Queries attend to each other         │
│  │                 │  "What are other queries finding?"    │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │ Cross-Attention │  Queries attend to image features     │
│  │ (Deformable)    │  "What's in the image at my spot?"   │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│  ┌─────────────────┐                                       │
│  │      FFN        │  Process gathered information         │
│  │ (Feed-Forward)  │                                       │
│  └────────┬────────┘                                       │
│           │                                                 │
│           ▼                                                 │
│     Updated Queries                                         │
│                                                             │
└────────────────────────────────────────────────────────────┘
```

### 6.3 Deformable Attention: The Speed Trick

Standard attention looks at ALL positions (expensive!). Deformable attention only samples a few **learned** positions:

```
Standard Attention:          Deformable Attention:
┌───┬───┬───┬───┬───┐       ┌───┬───┬───┬───┬───┐
│ * │ * │ * │ * │ * │       │   │   │ * │   │   │
├───┼───┼───┼───┼───┤       ├───┼───┼───┼───┼───┤
│ * │ * │ * │ * │ * │       │   │ * │   │ * │   │
├───┼───┼───┼───┼───┤       ├───┼───┼───┼───┼───┤
│ * │ * │ Q │ * │ * │       │   │   │ Q │   │   │
├───┼───┼───┼───┼───┤       ├───┼───┼───┼───┼───┤
│ * │ * │ * │ * │ * │       │   │ * │   │ * │   │
├───┼───┼───┼───┼───┤       ├───┼───┼───┼───┼───┤
│ * │ * │ * │ * │ * │       │   │   │ * │   │   │
└───┴───┴───┴───┴───┘       └───┴───┴───┴───┴───┘
  All 25 positions           Only 8 learned positions
  (Q = query position)
```

The sampling offsets are **learned** - the model figures out where to look!

$$\text{DeformAttn}(q, p, x) = \sum_{m=1}^{M} W_m \sum_{k=1}^{K} A_{mk} \cdot x(p + \Delta p_{mk})$$

Where:
- $q$: query
- $p$: reference point
- $\Delta p_{mk}$: learned offset for head m, point k
- $A_{mk}$: attention weight
- $W_m$: projection matrix for head m

### 6.4 D-FINE: Distribution-based Box Prediction

Traditional detectors predict 4 numbers directly: $(x, y, w, h)$.

D-FINE predicts a **probability distribution** over discrete bins:

```
Traditional:                 D-FINE:

predict(query) → [x, y, w, h]    predict(query) → Distribution over 33 bins
                                                   for each of 4 sides

                                  Left edge distance:
                                  ┌─────────────────────────────┐
                                  │▁▂▃▅▇█▇▅▃▂▁                  │
                                  └─────────────────────────────┘
                                   0 ←───── reg_max=32 ──────▶
```

**Why distributions?**
1. **Uncertainty**: The model can express "I think the edge is here, but I'm not 100% sure"
2. **Better gradients**: Softmax gradients are smoother than direct regression
3. **Fine-grained refinement**: Can iteratively sharpen the distribution

#### The Integral Layer

Converts distribution to actual coordinates:

$$\text{coord} = \sum_{i=0}^{\text{reg\_max}} P(i) \cdot W(i)$$

Where:
- $P(i)$ = probability of bin $i$ (from softmax)
- $W(i)$ = weight function (learned, non-uniform spacing)

### 6.5 Iterative Refinement

The decoder refines predictions across 6 layers:

```
Layer 1: Coarse prediction    →  IoU ≈ 0.5
Layer 2: Refined              →  IoU ≈ 0.6
Layer 3: More refined         →  IoU ≈ 0.7
Layer 4: Even better          →  IoU ≈ 0.75
Layer 5: Nearly there         →  IoU ≈ 0.8
Layer 6: Final prediction     →  IoU ≈ 0.85
```

Each layer takes the previous prediction as a starting point and refines it.

---

## 7. Component 4: Knowledge Distillation

This is RT-DETR v4's **key innovation**.

### 7.1 What is Knowledge Distillation?

Imagine a **master chef** (teacher) teaching an **apprentice** (student):

- The master has years of experience (trained on billions of images)
- The apprentice is smaller and faster (our detection model)
- The apprentice learns not just "right answers" but "how the master thinks"

```
┌─────────────────────────────────────────────────────────────┐
│                    Training Time                             │
│                                                              │
│  ┌───────────────────┐        ┌───────────────────┐         │
│  │    DINOv3         │        │    RT-DETR v4     │         │
│  │   (Teacher)       │        │    (Student)      │         │
│  │                   │        │                   │         │
│  │  768-dim features │───────▶│  256-dim features │         │
│  │                   │  Match │  (projected to    │         │
│  │   (Frozen)        │ these! │   768-dim)        │         │
│  └───────────────────┘        └───────────────────┘         │
│                                                              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│                    Inference Time                            │
│                                                              │
│                        ┌───────────────────┐                │
│  Image ───────────────▶│    RT-DETR v4     │───▶ Detections │
│                        │   (Student only)  │                │
│                        └───────────────────┘                │
│                                                              │
│  Teacher is NOT used! No extra computation!                 │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 The Teacher: DINOv3

DINOv3 is a **Vision Foundation Model** trained on 1.68 billion images using self-supervised learning.

Key facts:
- Architecture: Vision Transformer (ViT-B/16)
- Trained WITHOUT labels (self-supervised)
- Produces rich, generalizable features
- 768-dimensional output per spatial position

### 7.3 The Distillation Loss

The student tries to match the teacher's feature representations:

```python
def distillation_loss(student_features, teacher_features):
    # Normalize both to unit length
    student_norm = F.normalize(student_features, dim=-1)
    teacher_norm = F.normalize(teacher_features, dim=-1)

    # Cosine similarity (1 = identical, 0 = orthogonal, -1 = opposite)
    similarity = F.cosine_similarity(student_norm, teacher_norm, dim=-1)

    # Loss: we want similarity to be 1
    loss = (1 - similarity).mean()

    return loss
```

**Mathematically**:

$$\mathcal{L}_{\text{distill}} = 1 - \frac{1}{N}\sum_{i=1}^{N} \frac{f_s^{(i)} \cdot f_t^{(i)}}{\|f_s^{(i)}\| \|f_t^{(i)}\|}$$

Where:
- $f_s^{(i)}$ = student feature at position $i$
- $f_t^{(i)}$ = teacher feature at position $i$
- $N$ = number of spatial positions

### 7.4 Why This Works

The teacher has learned:
- General visual concepts from billions of images
- Robust features that transfer across tasks
- "What matters" in an image

By matching teacher features, the student inherits this knowledge without needing to train on billions of images itself!

---

## 8. Training: How the Model Learns

### 8.1 The Total Loss Function

RT-DETR v4 optimizes multiple objectives simultaneously:

$$\mathcal{L}_{\text{total}} = \lambda_1 \mathcal{L}_{\text{cls}} + \lambda_2 \mathcal{L}_{\text{box}} + \lambda_3 \mathcal{L}_{\text{giou}} + \lambda_4 \mathcal{L}_{\text{distill}} + ...$$

| Loss | Weight | What it measures |
|------|--------|------------------|
| $\mathcal{L}_{\text{cls}}$ (MAL) | 1.0 | Classification accuracy |
| $\mathcal{L}_{\text{box}}$ (L1) | 5.0 | Box coordinate accuracy |
| $\mathcal{L}_{\text{giou}}$ | 2.0 | Box overlap quality |
| $\mathcal{L}_{\text{fgl}}$ | 0.15 | Distribution sharpness |
| $\mathcal{L}_{\text{distill}}$ | 10-15 | Teacher matching |

### 8.2 Hungarian Matching

**Problem**: We have 300 queries but maybe only 5 objects. How do we assign predictions to ground truth?

**Solution**: Hungarian algorithm finds the **optimal one-to-one assignment** that minimizes total cost.

```
Predictions (300)              Ground Truth (5)
    P1 ─────────────────────────── GT1
    P2 ─────────────────────────── GT2
    P3 (best match) ───────────── GT3
    P4 ─────────────────────────── GT4
    P5 ─────────────────────────── GT5
    P6 ──┐
    P7   │
    ...  ├── Assigned to "no object" class
    P300─┘
```

The cost for each assignment considers:
- Classification probability
- L1 distance between boxes
- IoU (Intersection over Union)

### 8.3 Denoising Training (CDN)

To help the model converge faster, we add **noised ground truth boxes** as additional queries:

```
Regular queries: Learn from scratch
                 ┌────────────────────────────────────┐
                 │ "Find objects, I won't tell you    │
                 │  where they are!"                  │
                 └────────────────────────────────────┘

Denoising queries: Learn to refine
                 ┌────────────────────────────────────┐
                 │ "Here's approximately where an     │
                 │  object is (with noise). Fix it!"  │
                 └────────────────────────────────────┘
```

This provides easier gradients early in training.

### 8.4 Data Augmentation

RT-DETR v4 uses aggressive augmentation:

| Augmentation | Description |
|--------------|-------------|
| Mosaic | Combine 4 images into one |
| MixUp | Blend two images with alpha |
| Random Crop | IoU-based cropping |
| Color Jitter | Random brightness/contrast/saturation |
| Horizontal Flip | Mirror image |

These augmentations are **reduced in later epochs** (curriculum learning).

---

## 9. Putting It All Together

### Complete Forward Pass

```
1. INPUT: RGB Image (640 x 640 x 3)
   │
   ▼
2. BACKBONE (HGNetv2)
   │  - Extract multi-scale features
   │  - Output: S3 (80x80), S4 (40x40), S5 (20x20)
   │
   ▼
3. HYBRID ENCODER
   │  a) AIFI: Transformer attention on S5
   │  b) FPN: Top-down semantic propagation
   │  c) PAN: Bottom-up detail propagation
   │  - Output: P3, P4, P5 (enhanced features)
   │
   │  [If training: extract features for distillation]
   │
   ▼
4. TRANSFORMER DECODER
   │  a) Generate 300 object queries
   │  b) 6 decoder layers:
   │     - Self-attention among queries
   │     - Cross-attention to image features
   │     - Predict box distributions
   │     - Refine predictions iteratively
   │  - Output: 300 predictions (box + class + confidence)
   │
   ▼
5. POST-PROCESSING
   │  - Filter by confidence threshold (e.g., > 0.5)
   │  - No NMS needed! (one-to-one matching)
   │
   ▼
6. OUTPUT: List of detections
   [
     {box: [x, y, w, h], class: "E.coli", confidence: 0.95},
     {box: [x, y, w, h], class: "S.aureus", confidence: 0.87},
     ...
   ]
```

### Model Variants

| Variant | Backbone | AP (COCO) | Latency | Parameters |
|---------|----------|-----------|---------|------------|
| RT-DETRv4-S | HGNetv2-S | 49.8 | 3.66 ms | ~20M |
| RT-DETRv4-M | HGNetv2-M | 53.7 | 5.91 ms | ~30M |
| RT-DETRv4-L | HGNetv2-L | 55.4 | 8.07 ms | ~45M |
| RT-DETRv4-X | HGNetv2-X | 57.0 | 12.90 ms | ~70M |

For bacterial colony counting, **RT-DETRv4-L** is recommended as a good balance.

---

## 10. Glossary

| Term | Definition |
|------|------------|
| **Attention** | Mechanism allowing model to focus on relevant parts of input |
| **Backbone** | Feature extraction network (first part of detector) |
| **Bounding Box** | Rectangle defined by (x, y, width, height) around an object |
| **COCO** | Common Objects in Context - standard object detection benchmark |
| **Deformable Attention** | Attention that only samples learned positions (faster) |
| **DETR** | DEtection TRansformer - first end-to-end transformer detector |
| **Distillation** | Training smaller model to mimic larger model's representations |
| **Encoder** | Network that processes/enhances features |
| **Decoder** | Network that produces final predictions from features |
| **FPN** | Feature Pyramid Network - top-down feature fusion |
| **GIoU** | Generalized Intersection over Union - box overlap metric |
| **Hungarian Algorithm** | Optimal assignment algorithm for matching predictions to GT |
| **IoU** | Intersection over Union - $\frac{\text{Area of Overlap}}{\text{Area of Union}}$ |
| **mAP** | Mean Average Precision - primary detection metric |
| **NMS** | Non-Maximum Suppression - removes duplicate detections |
| **PAN** | Path Aggregation Network - bottom-up feature fusion |
| **Query** | Learned embedding that "searches" for objects |
| **Softmax** | Function that converts logits to probabilities (sum to 1) |
| **Transformer** | Architecture using self-attention, originally for NLP |
| **ViT** | Vision Transformer - applies transformer to images |

---

## Further Reading

1. **Original DETR Paper**: "End-to-End Object Detection with Transformers" (Carion et al., 2020)
2. **RT-DETR Paper**: "DETRs Beat YOLOs on Real-time Object Detection" (Lv et al., 2023)
3. **RT-DETRv4 Paper**: "Painlessly Furthering Real-Time Object Detection with VFMs" (Liao et al., 2025)
4. **Attention Is All You Need**: Original transformer paper (Vaswani et al., 2017)
5. **DINOv2/v3**: Self-supervised vision foundation models (Oquab et al., 2023-2024)

---

*Document created for CFU-Counter project - bacterial colony detection using RT-DETR v4*
