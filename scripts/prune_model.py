import torch
import torch.nn.utils.prune as prune
import os
import sys

def prune_model():
    model_path = r"C:\Bacterial colony counter\best1.pt"
    output_path = r"C:\Bacterial colony counter\test_output\models\best1_pruned_25.pt"
    
    print(f"Loading {model_path} for Pruning...")
    try:
        # Load the model
        # specific to Ultralytics YOLO, we load the pt file
        # We need to access the underlying torch module
        from ultralytics import YOLO
        yolo_model = YOLO(model_path)
        model = yolo_model.model # This is the nn.Module
        
        print("Applying L1 Unstructured Pruning (25% sparsity) to all Conv2d layers...")
        
        # Collect layers to prune
        parameters_to_prune = []
        for name, module in model.named_modules():
            if isinstance(module, torch.nn.Conv2d):
                parameters_to_prune.append((module, 'weight'))
        
        # Apply pruning globally
        # This removes the lowest 25% of weights across the whole model (by L1 norm)
        prune.global_unstructured(
            parameters_to_prune,
            pruning_method=prune.L1Unstructured,
            amount=0.25,
        )
        
        # Make the pruning permanent (remove the masks and actually set weights to 0)
        for module, name in parameters_to_prune:
            prune.remove(module, name)
            
        # Save
        # We save the state dict or the whole model?
        # Ultralytics .pt files are actually dictionaries with {'model': ...}
        # We should try to save it in a way compatible with YOLO() wrapper if possible, 
        # but changing weights might break hash checks.
        # Simplest is to just torch.save the model object or state_dict.
        # But to load it back into YOLO(), we usually need the full checkpoint structure.
        
        # Let's try to overwrite the model in the yolo wrapper and save using its method
        updated_ckpt = yolo_model.ckpt
        updated_ckpt['model'] = model
        
        torch.save(updated_ckpt, output_path)
        print(f"Success! Saved Pruned model to {output_path}")
        
        # Check sparsity
        print("Verifying sparsity...")
        zero_count = 0
        total_count = 0
        for name, module in model.named_modules():
            if isinstance(module, torch.nn.Conv2d):
                w = module.weight.data
                zero_count += torch.sum(w == 0)
                total_count += w.nelement()
        
        print(f"Global Sparsity: {100. * zero_count / total_count:.2f}%")

    except Exception as e:
        print(f"Pruning failed: {e}")

if __name__ == "__main__":
    prune_model()
