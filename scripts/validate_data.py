import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "entities.json"

def validate():
    print("Validating data...")
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"FAIL: Could not load JSON: {e}")
        return False

    slugs = set()
    errors = 0
    
    for i, item in enumerate(data):
        # 1. ID check
        if 'id' not in item:
            print(f"Item #{i} missing 'id'")
            errors += 1
            
        # 2. Slug check
        slug = item.get('slug')
        if not slug:
            print(f"Item #{i} missing 'slug'")
            errors += 1
        elif slug in slugs:
            print(f"Duplicate slug found: {slug}")
            errors += 1
        else:
            slugs.add(slug)
            
        # 3. Text check
        txt = item.get('text', {})
        if 'fr' not in txt or 'en' not in txt:
            print(f"Item {slug}: missing 'text.fr' or 'text.en'")
            errors += 1
        else:
            if 'name' not in txt['fr']:
                print(f"Item {slug}: missing 'text.fr.name'")
                errors += 1
                
    if errors == 0:
        print("SUCCESS: Data is valid.")
        return True
    else:
        print(f"FAIL: Found {errors} errors.")
        return False

if __name__ == "__main__":
    if not validate():
        sys.exit(1)
