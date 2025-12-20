import json
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "entities.json"
IMG_DIR = BASE_DIR / "assets" / "illustrations"

def generate_prompts():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    missing_items = []
    for item in data:
        slug = item['slug']
        if item.get('media', {}).get('has_image') is False:
            continue
        expected = IMG_DIR / f"{slug}.webp"
        if not expected.exists():
            missing_items.append(item)
            
    lines_csv = ["slug,prompt_fr,prompt_en"]
    lines_txt = []
    
    for item in missing_items:
        name = item['text']['fr']['name']
        desc = item['text']['fr']['short_description']
        # Simple heuristic prompt
        prompt = f"Illustration artistique pour {name}: {desc}. Style Art Virtuoso, haute qualité, détaillé."
        
        lines_txt.append(f"SLUG: {item['slug']}\nPROMPT: {prompt}\n")
        lines_csv.append(f"{item['slug']},\"{prompt}\",\"Prompts in EN to be added\"")
        
    (BASE_DIR / "docs").mkdir(exist_ok=True)
    
    with open(BASE_DIR / "docs" / "PROMPTS_MANQUANTS.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_txt))
        
    with open(BASE_DIR / "docs" / "IMAGES_MANQUANTES.csv", "w", encoding="utf-8") as f:
        f.write("\n".join(lines_csv))
        
    print(f"Generated prompts for {len(missing_items)} items in docs/.")

if __name__ == "__main__":
    generate_prompts()
