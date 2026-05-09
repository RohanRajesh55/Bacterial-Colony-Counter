
import os

file_path = r"c:\Bacterial colony counter\web\frontend\src\index.css"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Lines to delete: 1745 to 1952 (1-based)
# 0-based: 1744 to 1951
# We want to keep 0..1743 and 1952..end
start_delete_idx = 1744
end_delete_idx = 1952 # Python slice end is exclusive, so lines[1952] is the first line to KEEP if we want to skip up to 1951.
# wait.
# line 1952 (1-based) is index 1951.
# I want to delete index 1951.
# So I should start keeping again at index 1952.
# So lines[1952:] is correct.

new_lines = lines[:start_delete_idx] + lines[end_delete_idx:]

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print(f"Deleted lines {start_delete_idx+1} to {end_delete_idx} from {file_path}")
