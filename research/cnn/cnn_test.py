#!/usr/bin/env python3
"""
Loads and evaluates the final multi-task model trained by cnn_train.py.
It calculates both regression and classification metrics and saves visual results.
"""
import os
import sys
import json
from argparse import ArgumentParser
from pathlib import Path

# Add shared module to path
sys.path.insert(0, str(Path(__file__).parent.parent))
from shared.constants import CLASSES
from shared.dataset import AgarMultiTaskDataset, read_id_list, collate_filter_none

import numpy as np
from tqdm import tqdm
from sklearn.metrics import mean_absolute_error, r2_score, classification_report, accuracy_score

import torch
import torch.nn as nn
from torch.utils.data import DataLoader

import albumentations as A
from albumentations.pytorch import ToTensorV2
import cv2

# --- Configuration ---
# You can change the tolerance for counting accuracy here.
# A prediction is "correct" if |true_count - predicted_count| <= ACCURACY_TOLERANCE
ACCURACY_TOLERANCE = 10

# -------------------------
# Model Architecture
# -------------------------
class VanillaDeepCNN(nn.Module):
    """
    The definition of the multi-task CNN. This must be an exact copy of the
    model architecture used during training to load the weights correctly.
    """
    def __init__(self, in_channels=3, num_conv_blocks=8, base_filters=32, fc_size=512, dropout=0.4, num_classes=7):
        super().__init__()
        # --- Shared Feature Extractor ("Body") ---
        layers, c, f = [], in_channels, base_filters
        for i in range(num_conv_blocks):
            out_ch = min(f * (2**i), 512)
            layers += [nn.Conv2d(c, out_ch, 3, padding=1), nn.BatchNorm2d(out_ch), nn.ReLU(True), nn.MaxPool2d(2)]
            c = out_ch
        self.features = nn.Sequential(*layers)
        
        # --- Global Average Pooling and Shared Fully Connected Layer ---
        self.gap = nn.AdaptiveAvgPool2d(1)
        self.shared_fc = nn.Sequential(nn.Linear(c, fc_size), nn.ReLU(True), nn.Dropout(dropout))
        
        # --- Two Specialized "Heads" ---
        # Head 1: For the regression task (counting)
        self.head_count = nn.Sequential(nn.Linear(fc_size, fc_size//2), nn.ReLU(True), nn.Dropout(dropout/2), nn.Linear(fc_size//2, 1))
        # Head 2: For the classification task (identifying type)
        self.head_class = nn.Sequential(nn.Linear(fc_size, fc_size//2), nn.ReLU(True), nn.Dropout(dropout/2), nn.Linear(fc_size//2, num_classes))

    def forward(self, x):
        # Pass input through the shared body
        x = self.features(x)
        x = self.gap(x)
        x = x.view(x.size(0), -1) # Flatten the features
        shared = self.shared_fc(x)
        # Return the output from both heads
        return self.head_count(shared), self.head_class(shared)


def run_evaluation(results_dir):
    """Loads a trained model from a results directory and evaluates it on the test set."""
    print(f"--- Loading experiment from: {results_dir} ---")
    
    # Define paths to the model and its configuration file
    meta_path = os.path.join(results_dir, "training_metadata.json")
    model_path = os.path.join(results_dir, "final_best_model.pth")
    
    if not os.path.exists(meta_path) or not os.path.exists(model_path):
        raise FileNotFoundError(f"Could not find 'training_metadata.json' and/or 'final_best_model.pth' in '{results_dir}'.")
        
    # Load the metadata to get the configuration used during training
    with open(meta_path, 'r') as f:
        meta = json.load(f)
    cfg = meta['cfg']
    class_list = meta['class_list']
    class_map = {c: i for i, c in enumerate(class_list)}
    num_classes = len(class_list)

    print("\n--- Loaded Configuration ---")
    print(json.dumps(cfg, indent=2, default=str))
    print("----------------------------\n")
    
    # Set the device (GPU or CPU)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device: {device.upper()}")
    
    # Re-create the model with the exact same architecture as during training
    model = VanillaDeepCNN(
        in_channels=3,
        num_conv_blocks=cfg["num_conv_blocks"],
        base_filters=cfg["base_filters"],
        fc_size=cfg["fc_size"],
        dropout=cfg["dropout"],
        num_classes=num_classes
    )
    # Load the saved weights into the model
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.to(device)
    model.eval() # Set the model to evaluation mode

    # Find the test/validation files to evaluate on
    test_files = [os.path.join(cfg["training_lists_dir"], f) for f in os.listdir(cfg["training_lists_dir"]) if f.endswith(("_val.txt"))]
    if not test_files:
        raise FileNotFoundError("Could not find any _val.txt files.")

    # Create the dataset and dataloader for the test set
    test_tf = A.Compose([A.Resize(*cfg["image_size"]), A.Normalize(mean=(0.485,0.456,0.406), std=(0.229,0.224,0.225)), ToTensorV2()])
    test_ds = AgarMultiTaskDataset(test_files, cfg["dataset_dir"], class_map, transform=test_tf, include_path=True)
    test_loader = DataLoader(test_ds, batch_size=cfg["batch_size"]*2, shuffle=False, num_workers=cfg["num_workers"], pin_memory=True, collate_fn=collate_filter_none)
    
    # Initialize lists to store true values and predictions
    y_true_counts, y_pred_counts, y_true_cls, y_pred_cls = [], [], [], []
    
    # Create a folder to save the visual results
    output_folder = os.path.join(results_dir, 'evaluation_images')
    os.makedirs(output_folder, exist_ok=True)
    print(f"\nSaving visual results to: '{output_folder}'")
    
    # Run the model on the test data
    with torch.no_grad(): # Disable gradient calculation for efficiency
        for batch in tqdm(test_loader, desc="Running Evaluation"):
            if batch is None: continue
            imgs, counts, classes, paths = batch["images"].to(device), batch["counts"], batch["classes"], batch["paths"]
            
            # Get predictions from both heads of the model
            pred_counts, pred_class_logits = model(imgs)
            pred_cls_indices = pred_class_logits.argmax(dim=1)
            
            # Store the results
            y_true_counts.extend(counts.cpu().numpy().flatten())
            y_pred_counts.extend(pred_counts.cpu().numpy().flatten())
            y_true_cls.extend(classes.cpu().numpy().flatten())
            y_pred_cls.extend(pred_cls_indices.cpu().numpy().flatten())

            # Create and save a visual for each image in the batch
            for i in range(len(paths)):
                img = cv2.imread(paths[i])
                img = cv2.resize(img, (512, 512))
                true_text = f"True: {round(counts[i].item())} ({class_list[classes[i].item()]})"
                pred_text = f"Pred: {round(pred_counts[i].item())} ({class_list[pred_cls_indices[i].item()]})"
                # Make the prediction text green if correct, red if incorrect
                color = (0, 255, 0) if classes[i].item() == pred_cls_indices[i].item() else (0, 0, 255)
                
                cv2.putText(img, true_text, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.putText(img, pred_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)
                cv2.imwrite(os.path.join(output_folder, os.path.basename(paths[i])), img)
    
    # --- Final Report Generation ---
    print("\n" + "="*60)
    print(" " * 17 + "Final Evaluation Report")
    print("="*60)
    
    # --- Regression Metrics ---
    print("\n## Regression Metrics (Task: Counting)\n")
    mae = mean_absolute_error(y_true_counts, y_pred_counts)
    r2 = r2_score(y_true_counts, y_pred_counts)
    errors = np.abs(np.array(y_true_counts) - np.array(y_pred_counts))
    tolerance_accuracy = np.sum(errors <= ACCURACY_TOLERANCE) / len(errors) if len(errors) > 0 else 0
    
    print(f"Mean Absolute Error: {mae:.2f}")
    print(f"R-squared Score:     {r2:.2f}")
    print(f"Counting Accuracy (±{ACCURACY_TOLERANCE} colonies): {tolerance_accuracy:.2%}")

    print("\n" + "-"*60)
    
    # --- Classification Metrics ---
    print("\n## Classification Metrics (Task: Type Identification)\n")
    class_accuracy = accuracy_score(y_true_cls, y_pred_cls)
    print(f"Classification Accuracy: {class_accuracy:.2%}")
    print("...") # Placeholder for the detailed report
    # To print the full report, uncomment the following line:
    # print(classification_report(y_true_cls, y_pred_cls, labels=list(range(num_classes)), target_names=class_list, zero_division=0))
    
    print("\n" + "="*60)


if __name__ == "__main__":
    # Set up the command-line interface
    p = ArgumentParser(description="Evaluate a trained multi-task CNN.")
    p.add_argument("--results_dir", type=str, required=True, help="Path to the results directory of the trained model.")
    # The --image argument is not used in this version but could be added back
    args = p.parse_args()
    
    run_evaluation(args.results_dir)