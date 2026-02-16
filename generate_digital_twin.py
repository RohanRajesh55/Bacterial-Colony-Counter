import os
import cv2
import glob
import json
import random
import argparse
import numpy as np
from tqdm import tqdm
from pathlib import Path
from typing import List, Dict

# Import our simulation library
from lib_simulation import PlateModel, PlacementEngine, Blender, ArtifactInjector, ColonyAsset

def load_assets(assets_dir: str) -> Dict[str, List[ColonyAsset]]:
    """
    Load all colony assets from the assets directory.
    Returns a dict mapping species -> list of ColonyAsset objects.
    """
    assets = {}
    species_dirs = glob.glob(os.path.join(assets_dir, "*"))
    
    print(f"Loading assets from {assets_dir}...")
    
    for s_dir in species_dirs:
        if not os.path.isdir(s_dir): continue
        species = os.path.basename(s_dir)
        assets[species] = []
        
        # Find all PNGs
        pngs = glob.glob(os.path.join(s_dir, "*.png"))
        
        for png_path in pngs:
            json_path = png_path.replace('.png', '.json')
            if not os.path.exists(json_path): continue
            
            try:
                # Load image (RGBA)
                img = cv2.imread(png_path, cv2.IMREAD_UNCHANGED)
                if img is None or img.shape[2] != 4: continue
                
                # Load metadata
                with open(json_path, 'r') as f:
                    meta = json.load(f)
                
                # Create Asset object
                asset = ColonyAsset(
                    image=img,
                    mask=img[:,:,3],
                    species=species,
                    source_stats=tuple(meta.get('bg_mean', [0,0,0])), # RGB mean
                    area_px=meta.get('area_px', 0)
                )
                assets[species].append(asset)
            except Exception as e:
                # print(f"Error loading {png_path}: {e}")
                continue
                
        print(f"Loaded {len(assets[species])} assets for {species}")
        
    return assets

def generate_synthetic_image(
    background_path: str, 
    assets: Dict[str, List[ColonyAsset]], 
    num_colonies: int,
    output_path: str,
    output_label_path: str
):
    """
    Generate a single synthetic image.
    """
    # 1. Initialize Plate Model
    try:
        plate = PlateModel(background_path)
        # Remove text from background BEFORE placing colonies
        plate.remove_text()
        # Debug ROI for the first image
        if "0000" in output_path:
             plate.debug_roi(output_path.replace(".jpg", "_roi_debug.jpg"))
    except Exception as e:
        print(f"Error loading background {background_path}: {e}")
        return

    # 2. Initialize Placement Engine
    engine = PlacementEngine(plate)
    
    # 3. Placement Loop
    available_species = list(assets.keys())
    if not available_species: return
    
    current_bg = plate.background.copy()
    labels = [] # YOLO format: class x_center y_center w h
    
    max_attempts = num_colonies * 3  # Allow extra attempts for rejected placements
    placed = 0
    
    for _ in range(max_attempts):
        if placed >= num_colonies:
            break
            
        # Select random species
        species = random.choice(available_species)
        if not assets[species]: continue
        
        # Select random asset
        asset = random.choice(assets[species])
        
        # Propose location
        x, y = engine.propose_location()
        
        # Calculate colony half-size for boundary check
        asset_h, asset_w = asset.image.shape[:2]
        asset_r = max(asset_h, asset_w) / 2
        
        # Check if the ENTIRE colony (not just center) fits inside the plate
        if not plate.is_valid_location(x, y, margin=0.90):
            continue
            
        # Also check that edges don't overflow
        edge_dist = np.sqrt((x - plate.center[0])**2 + (y - plate.center[1])**2) + asset_r
        if edge_dist > plate.radius * 0.92:
            continue
        
        # Check overlap constraints
        if engine.check_overlap(x, y, asset_r, max_iou=0.2):
            continue
        
        # All checks passed — Place it!
        
        # Radiometric Matching
        local_bg_mean, _ = plate.get_local_stats(x, y)
        matched_asset_img = Blender.MatchColor(asset, local_bg_mean)
        
        # Blending
        current_bg = Blender.SeamlessClone(current_bg, matched_asset_img, x, y)
        
        # Record placement
        engine.placed_colonies.append((x, y, asset_r, species))
        placed += 1
        
        # Record Label (YOLO format: normalized x, y, w, h)
        h_img, w_img = plate.h, plate.w
        
        # BBox global coords
        x1 = x - asset_w // 2
        x2 = x + asset_w // 2
        y1 = y - asset_h // 2
        y2 = y + asset_h // 2
        
        # Clip to image
        x1 = max(0, x1); x2 = min(w_img, x2)
        y1 = max(0, y1); y2 = min(h_img, y2)
        
        if x2 > x1 and y2 > y1:
            bw = x2 - x1
            bh = y2 - y1
            bx = x1 + bw / 2
            by = y1 + bh / 2
            
            norm_x = bx / w_img
            norm_y = by / h_img
            norm_w = bw / w_img
            norm_h = bh / h_img
            
            class_id = 0 # Default 'colony'
            labels.append(f"{class_id} {norm_x:.6f} {norm_y:.6f} {norm_w:.6f} {norm_h:.6f}")

    # 4. Artifact Injection
    final_img = ArtifactInjector.apply_all(current_bg)
    
    # 5. Save Output
    cv2.imwrite(output_path, final_img)
    
    with open(output_label_path, 'w') as f:
        f.write("\n".join(labels))

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--assets", default="assets/colonies", help="Path to assets")
    parser.add_argument("--background", default="images/agar_001.jpeg", help="Path to empty plate background")
    parser.add_argument("--output", default="output/synthetic", help="Output directory")
    parser.add_argument("--count", type=int, default=5, help="Number of images to generate")
    args = parser.parse_args()
    
    os.makedirs(args.output, exist_ok=True)
    images_dir = os.path.join(args.output, "images")
    labels_dir = os.path.join(args.output, "labels")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)
    
    # Load assets
    assets = load_assets(args.assets)
    
    if not assets:
        print("No assets found! Please run extraction first.")
        exit(1)
        
    print(f"Generating {args.count} synthetic images using background: {args.background}")
    
    for i in tqdm(range(args.count)):
        out_name = f"synth_{i:04d}"
        out_img_path = os.path.join(images_dir, f"{out_name}.jpg")
        out_lbl_path = os.path.join(labels_dir, f"{out_name}.txt")
        
        # Randomize colony count per plate
        n_colonies = random.randint(20, 300)
        
        generate_synthetic_image(
            args.background,
            assets,
            n_colonies,
            out_img_path,
            out_lbl_path
        )
        
    print("Generation complete.")
