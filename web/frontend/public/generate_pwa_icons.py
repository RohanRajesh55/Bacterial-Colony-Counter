
from PIL import Image
import os

source_path = r"c:\Bacterial colony counter\web\frontend\public\logo.jpeg"
output_dir = r"c:\Bacterial colony counter\web\frontend\public"

if not os.path.exists(source_path):
    print(f"Error: Source file {source_path} not found.")
    exit(1)

img = Image.open(source_path)

# Generate PWA icons
sizes = [
    (192, 192, "pwa-192x192.png"),
    (512, 512, "pwa-512x512.png"),
    (180, 180, "apple-touch-icon.png")
]

for w, h, name in sizes:
    resized_img = img.resize((w, h), Image.Resampling.LANCZOS)
    resized_img.save(os.path.join(output_dir, name))
    print(f"Generated {name}")

# Generate favicon.ico (multi-size)
img.save(os.path.join(output_dir, "favicon.ico"), format='ICO', sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
print("Generated favicon.ico")
