Fine-Tuning Methodology for RT-DETR on AGAR Dataset
1. Overview

This project fine-tunes a pre-trained RT-DETR object detection model for bacterial colony detection and counting on the AGAR dataset.
Due to computational budget constraints and the domain characteristics of bacterial colonies, a head-only fine-tuning (linear probing) strategy is adopted.

All experiments are conducted for research use only, in compliance with the CC BY-NC 2.0 license of the AGAR dataset.

2. Dataset Split Strategy

A fixed deterministic split is used to ensure reproducibility:

Split	Images
Training	First 4000 images
Validation / Test	Remaining images (4000 →5000)

3. Model Initialization
Base Model

Model: RT-DETR

Pretrained Weights: COCO

Checkpoint: PekingU/rtdetr_r101vd

Number of Classes

7 bacterial colony classes, matching shared/constants.py and config.yaml.

4. Fine-Tuning Strategy Used
4.1 Type of Fine-Tuning

Head-Only Fine-Tuning (Linear Probing)

Only the detection heads are trained, while all feature extraction layers remain frozen.
5. Frozen vs Trainable Layers

5.1 Frozen Layers (NOT trained)

The following components are fully frozen:

Backbone (CNN feature extractor)

Transformer encoder

Transformer decoder

Feature pyramid / intermediate layers

These layers retain COCO-pretrained weights and are not updated during training.

5.2 Trainable Layers (Fine-Tuned)

Only the final prediction heads are trainable:

Layer	        Purpose
class_embed	 Colony classification
bbox_embed	 Bounding box regression

These layers learn:

Colony class distributions

Spatial localization specific to Petri-dish imagery


| Component           | Frozen | Trainable |
| ------------------- | ------ | --------- |
| Backbone            | Yes    | No        |
| Encoder             | Yes    | No        |
| Decoder             | Yes    | No        |
| Classification Head | No     | Yes       |
| Bounding Box Head   | No     | Yes       |



6. Training Configuration (from config.yaml)
6.1 Core Hyperparameters
Parameter	    Value	            Rationale
Batch size	      4	        Safe for 1024px images
Image size	     1024	    Small colony resolution
Epochs	          30	    Head convergence is fast
Learning rate	 1e-5	    Stable head-only learning
Weight decay	 1e-4	    Regularization


6.2 Optimization & Efficiency

Optimizer: AdamW

Scheduler: Warm-up + cosine decay

Mixed Precision: Enabled

Gradient Checkpointing: Disabled

Gradient Accumulation: 1

This setup minimizes GPU cost while ensuring stable convergence.


Why head only finetuning
| Aspect           | Benefit  |
| ---------------- | -------- |
| GPU memory       | Very low |
| Training speed   | Fast     |
| Overfitting risk | Reduced  |
| Compute cost     | Minimal  |
| Stability        | High     |


detection metrics
Computed using TorchMetrics:

Metric	Description
mAP@0.5	Detection accuracy at IoU 0.5
mAP@0.75	Strict localization accuracy
mAP@0.5:0.95	COCO-style mean AP
mAR@100	Recall with max 100 detections4


counting metrics

Colony count accuracy is evaluated separately:

Metric	Meaning
Exact match	Perfect count prediction
Within 5%	Practical counting tolerance
Within 10%	Relaxed tolerance
MAE	Mean absolute error
RMSE	Penalizes large errors