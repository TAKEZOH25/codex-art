import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

# --- CONFIG ---
SITE_NAME = "Art Virtuoso"
SITE_URL = "https://art-virtuoso.com"
DEFAULT_LANG = "fr"
OTHER_LANGS = ["en"]
LANGS = [DEFAULT_LANG] + OTHER_LANGS

BASE_DIR = Path(__file__).parent
DATA_FILE = BASE_DIR / "data" / "entities.json"
OUTPUT_DIR = BASE_DIR / "output_build"
TEMPLATE_DIR_REL = "templates"
ASSETS_DIR = BASE_DIR / "assets"

# --- HELPERS ---
def load_data():
    if not DATA_FILE.exists():
        print(f"Error: Data file not found at {DATA_FILE}")
        sys.exit(1)
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def get_i18n_strings():
    return {
        "fr": {
            "hero_title": "L'Art à portée de main",
            "hero_subtitle": "Explorez les mouvements, artistes et œuvres qui ont marqué l'histoire.",
            "featured_title": "À la une",
            "explore_codex": "Explorer le Codex",
            "read_more": "Lire la suite",
            "search_placeholder": "Rechercher...",
            "nav": { "home": "Accueil", "codex": "Codex" }
        },
        "en": {
            "hero_title": "Art at your fingertips",
            "hero_subtitle": "Explore the movements, artists and artworks that shaped history.",
            "featured_title": "Featured",
            "explore_codex": "Explore the Codex",
            "read_more": "Read more",
            "search_placeholder": "Search...",
            "nav": { "home": "Home", "codex": "Codex" }
        }
    }

def clean_output():
    # Disabled clean to avoid Windows locking issues
    pass
    # OUTPUT_DIR.mkdir(parents=True, exist_ok=True) # Check done in main

def copy_assets():
    dest = OUTPUT_DIR / "assets"
    if ASSETS_DIR.exists():
        shutil.copytree(ASSETS_DIR, dest, dirs_exist_ok=True)

# --- ROUTING ---
def get_url(lang, type_slug=None, entity_slug=None):
    prefix = "" if lang == DEFAULT_LANG else f"/{lang}"
    if not type_slug and not entity_slug:
        return f"{prefix}/" if prefix else "/"
    if type_slug == "codex":
        return f"{prefix}/codex/"
    if type_slug == "plan-du-site":
        return f"{prefix}/plan-du-site/"

    type_plurals = {
        "artist": "artistes" if lang == "fr" else "artists",
        "movement": "mouvements" if lang == "fr" else "movements",
        "artwork": "oeuvres" if lang == "fr" else "artworks",
        "technique": "techniques" if lang == "fr" else "techniques",
        "concept": "concepts" if lang == "fr" else "concepts",
    }
    coll = type_plurals.get(type_slug, type_slug)
    base = f"{prefix}/{coll}/"
    if entity_slug:
        return f"{base}{entity_slug}/"
    return base

# --- GENERATOR ---
def main():
    print("Starting build...")
    
    # 1. Setup
    if OUTPUT_DIR.exists():
         print(f"Warning: Output dir {OUTPUT_DIR} exists, overwriting files...")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    entities = load_data()
    i18n = get_i18n_strings()
    
    # 2. Indexing
    slug_map = {e['slug']: e for e in entities}
    type_map = {}
    for e in entities:
        type_map.setdefault(e['type'], []).append(e)
        
    for e in entities:
        e['_urls'] = {}
        for lang in LANGS:
            e['_urls'][lang] = get_url(lang, e['type'], e['slug'])
        e['image_url'] = f"/assets/illustrations/{e['slug']}.webp" if e.get('media', {}).get('has_image', True) else "/assets/illustrations/default.webp"

    # 3. Jinja Environment
    # Using relative path string for loader
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR_REL))
    env.globals['site_name'] = SITE_NAME
    env.globals['current_year'] = datetime.now().year
    
    # 4. Rendering
    render_count = 0
    
    for lang in LANGS:
        t = i18n[lang]
        prefix = OUTPUT_DIR if lang == DEFAULT_LANG else OUTPUT_DIR / lang
        
        base_context = {
            'lang': lang,
            'root_url': "",
            'nav': {
                'home_url': get_url(lang),
                'codex_url': get_url(lang, 'codex'),
                'plan_url': get_url(lang, 'plan-du-site'),
                'legal_contact_url': "#", 
                'main': []
            },
            'other_langs': [{'code': l, 'url': get_url(l)} for l in LANGS if l != lang],
            't': t
        }

        def render(template_name, path_suffix, context):
            out_path = prefix / path_suffix
            if path_suffix.endswith("/"):
                out_path = out_path / "index.html"
            
            out_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Here is the call that was failing
            template = env.get_template(template_name)
            
            full_context = base_context.copy()
            full_context.update(context)
            full_context['canonical_url'] = f"{SITE_URL}{get_url(lang, path_suffix.strip('/'))}" if path_suffix != "index.html" else f"{SITE_URL}{get_url(lang)}"
            
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(template.render(full_context))
            nonlocal render_count
            render_count += 1
            
        featured = [e for e in entities if e.get('seo', {}).get('priority', 0) >= 0.9][:3]
        render("pages/index.html", "", {
            'title': t.get('hero_title'),
            'description': t.get('hero_subtitle'),
            'featured_entities': featured
        })
        
        render("pages/index.html", "codex/", { 
            'title': "Codex",
            'description': "All entities",
            'featured_entities': entities
        }) 

        for type_key, group_entities in type_map.items():
            coll_slug = get_url(lang, type_key).strip("/")
            rel_coll_path = coll_slug.replace(f"{lang}/", "", 1) if lang != DEFAULT_LANG else coll_slug
            if rel_coll_path.startswith("/"): rel_coll_path = rel_coll_path[1:]

            render("pages/index.html", rel_coll_path, {
                'title': type_key.capitalize(),
                'description': f"Browse {type_key}",
                'featured_entities': group_entities
            })

            for entity in group_entities:
                rel_ent_path = entity['_urls'][lang].replace(f"/{lang}/", "", 1) if lang != DEFAULT_LANG else entity['_urls'][lang]
                if rel_ent_path.startswith("/"): rel_ent_path = rel_ent_path[1:]
                
                render("pages/entity.html", rel_ent_path, {
                    'title': entity['text'][lang]['name'],
                    'description': entity['text'][lang]['short_description'],
                    'entity': entity,
                    'related_entities': []
                })

    # 5. Assets
    copy_assets()
    
    # 6. Search
    search_index = []
    for e in entities:
        for lang in LANGS:
            search_index.append({
                'label': e['text'][lang]['name'],
                'url': e['_urls'][lang],
                'lang': lang,
                'type': e['type']
            })
    with open(OUTPUT_DIR / "search.json", "w", encoding="utf-8") as f:
        json.dump(search_index, f)

    # 7. Sitemaps
    for lang in LANGS:
        urls = []
        urls.append(f"{SITE_URL}{get_url(lang)}")
        urls.append(f"{SITE_URL}{get_url(lang, 'codex')}")
        for e in entities:
             urls.append(f"{SITE_URL}{e['_urls'][lang]}")
        
        sitemap_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
        sitemap_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        for u in urls:
            sitemap_content += f'  <url><loc>{u}</loc></url>\n'
        sitemap_content += '</urlset>'
        
        with open(OUTPUT_DIR / f"sitemap-{lang}.xml", "w", encoding="utf-8") as f:
            f.write(sitemap_content)
            
    sm_index = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sm_index += '<sitemapindex xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for lang in LANGS:
        sm_index += f'  <sitemap><loc>{SITE_URL}/sitemap-{lang}.xml</loc></sitemap>\n'
    sm_index += '</sitemapindex>'
    
    with open(OUTPUT_DIR / "sitemap_index.xml", "w", encoding="utf-8") as f:
        f.write(sm_index)
        
    robots = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap_index.xml"
    with open(OUTPUT_DIR / "robots.txt", "w", encoding="utf-8") as f:
        f.write(robots)

    print(f"Done! Generated {render_count} pages.")

if __name__ == "__main__":
    main()
