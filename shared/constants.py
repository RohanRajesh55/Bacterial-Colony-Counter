"""
Shared constants for CFU-Counter project.

This module provides the single source of truth for class definitions
used across CNN and YOLO training/evaluation scripts.
"""

# Master class list - 7 bacterial species/conditions
CLASSES = [
    "B.subtilis",
    "C.albicans",
    "Contamination",
    "Defect",
    "E.coli",
    "P.aeruginosa",
    "S.aureus",
]

# Derived mappings
CLASS_MAP = {name: idx for idx, name in enumerate(CLASSES)}
NUM_CLASSES = len(CLASSES)
