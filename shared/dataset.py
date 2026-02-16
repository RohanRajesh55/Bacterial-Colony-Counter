"""
Shared dataset utilities for CFU-Counter project.

This module provides reusable dataset loading and processing utilities
used by CNN training and evaluation scripts.
"""
import json
from pathlib import Path
from typing import List, Dict, Optional
from collections import OrderedDict

import cv2
import torch
from torch.utils.data import Dataset
from albumentations.pytorch import ToTensorV2

from shared.constants import CLASS_MAP


def read_id_list(path: str) -> List[str]:
    """
    Reads a list of image IDs from a text file.

    Args:
        path: Path to text file with one image ID per line

    Returns:
        List of image ID strings (whitespace stripped, empty lines filtered)
    """
    with open(path, 'r') as f:
        return [line.strip() for line in f if line.strip()]


def collate_filter_none(batch: List[Optional[Dict]]) -> Optional[Dict]:
    """
    Custom collate function that filters out None values from failed samples.

    Use this with DataLoader when the Dataset may return None for corrupt/missing samples.

    Args:
        batch: List of sample dicts, some may be None

    Returns:
        Dict with stacked tensors, or None if all samples failed
    """
    batch = [item for item in batch if item is not None]
    if not batch:
        return None
    result = {
        "images": torch.stack([b['image'] for b in batch]),
        "counts": torch.stack([b['count'] for b in batch]),
        "classes": torch.stack([b['class'] for b in batch]),
    }
    if "path" in batch[0]:
        result["paths"] = [b['path'] for b in batch]
    return result


class AgarMultiTaskDataset(Dataset):
    """
    PyTorch Dataset for loading agar plate images with colony count and species labels.

    Handles missing files and JSON errors gracefully by returning None,
    which should be filtered using collate_filter_none.

    Args:
        txt_files: List of paths to text files containing image IDs
        root_dir: Root directory containing 'images/' and 'annotations/' subdirs
        class_map: Dict mapping class names to integer indices
        transform: Optional albumentations transform pipeline
        include_path: If True, include image path in returned dict (for visualization)
    """

    def __init__(
        self,
        txt_files: List[str],
        root_dir: str,
        class_map: Dict[str, int] = None,
        transform=None,
        include_path: bool = False
    ):
        self.root = Path(root_dir)
        self.transform = transform
        self.class_map = class_map if class_map is not None else CLASS_MAP
        self.include_path = include_path

        # Aggregate unique image IDs from all provided list files
        all_ids = []
        for file_path in txt_files:
            all_ids.extend(read_id_list(file_path))
        # Remove duplicates while preserving order
        self.ids = list(OrderedDict.fromkeys(all_ids))

        # Pre-generate paths for faster access
        self.image_paths = [self.root / "images" / f"{i}.jpg" for i in self.ids]
        self.ann_paths = [self.root / "annotations" / f"{i}.json" for i in self.ids]

    def __len__(self) -> int:
        return len(self.ids)

    def __getitem__(self, idx: int) -> Optional[Dict[str, torch.Tensor]]:
        """
        Load a single sample.

        Returns None if sample is invalid (missing file, corrupt JSON, unknown class).
        """
        try:
            # Load image
            img_path = str(self.image_paths[idx])
            img = cv2.imread(img_path)
            if img is None:
                raise FileNotFoundError(f"Image not found at {img_path}")

            # Load and parse annotation JSON
            with open(self.ann_paths[idx], 'r') as f:
                ann = json.load(f)

            # Extract regression target (colony count)
            count = float(ann.get("colonies_number", 0.0))

            # Extract classification target (species type)
            ctype = "Defect"  # Default for empty or unlabeled plates
            if ann.get("labels") and len(ann["labels"]) > 0:
                ctype = ann['labels'][0]['class']

            class_idx = self.class_map.get(ctype)
            if class_idx is None:
                # Skip if class is not in our master list
                return None

            # Apply augmentations/transforms
            if self.transform:
                img = self.transform(image=img)['image']
            else:
                img = ToTensorV2()(image=img)['image']

            result = {
                "image": img,
                "count": torch.tensor([count], dtype=torch.float32),
                "class": torch.tensor(class_idx, dtype=torch.long),
            }

            if self.include_path:
                result["path"] = img_path

            return result

        except (FileNotFoundError, json.JSONDecodeError, KeyError):
            return None
