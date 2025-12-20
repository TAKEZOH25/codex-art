import json
import os
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "entities.json"
IMG_DIR = BASE_DIR / "assets" / "illustrations"

def check_images():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    missing = []
    
    if not IMG_DIR.exists():
        print(f"Warning: {IMG_DIR} does not exist.")
        
    for item in data:
        slug = item['slug']
        # Check specific override or default convention
        # MVP: strict convention {slug}.webp
        expected = IMG_DIR / f"{slug}.webp"
        
        # If item explicit says has_image: false, skip
        if item.get('media', {}).get('has_image') is False:
            continue
            
        if not expected.exists():
            missing.append(slug)
            
    print(f"Found {len(missing)} missing images.")
    
    with open(BASE_DIR / "docs" / "IMAGES_NEEDED.txt", "w", encoding="utf-8") as f: # Assuming docs dir exists or we create it
        for m in missing:
            f.write(m + "\n")
            print(f" - {m}")

if __name__ == "__main__":
    # Ensure docs dir exists
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    check_images()
