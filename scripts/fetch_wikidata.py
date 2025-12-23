"""
Enhanced Wikidata fetcher - Retrieves rich data for SEO-optimized pages
"""
import requests
import json
import time
import re
from pathlib import Path
from datetime import datetime

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "ArtVirtuosoSSG/1.0 (contact: support@art-virtuoso.com)"
}

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "entities.json"

def slugify(text):
    """Convert text to URL-friendly slug"""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r"[''`]", '', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')[:80]

def query_wikidata(sparql_query):
    """Execute SPARQL query and return results"""
    try:
        r = requests.get(
            ENDPOINT,
            params={"query": sparql_query, "format": "json"},
            headers=HEADERS,
            timeout=120
        )
        r.raise_for_status()
        return r.json().get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"  Query error: {e}")
        return []

def get_value(row, key, default=""):
    """Safe extraction of value from SPARQL result"""
    return row.get(key, {}).get("value", default)

def parse_date(date_str):
    """Parse Wikidata date to readable format"""
    if not date_str:
        return None
    try:
        # Handle format like "1853-03-30T00:00:00Z"
        if "T" in date_str:
            date_str = date_str.split("T")[0]
        return date_str
    except:
        return None

def fetch_artists(limit=200):
    """Fetch famous painters with rich data from Wikidata"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn 
           ?birthDate ?deathDate ?birthPlaceFr ?birthPlaceEn 
           ?deathPlaceFr ?deathPlaceEn ?image ?movementLabelFr ?movementSlug
    WHERE {{
      ?item wdt:P31 wd:Q5;
            wdt:P106 wd:Q1028181.
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 15)
      
      OPTIONAL {{ ?item wdt:P569 ?birthDate. }}
      OPTIONAL {{ ?item wdt:P570 ?deathDate. }}
      OPTIONAL {{ ?item wdt:P18 ?image. }}
      OPTIONAL {{ 
        ?item wdt:P19 ?birthPlace.
        ?birthPlace rdfs:label ?birthPlaceFr FILTER(LANG(?birthPlaceFr) = "fr").
        ?birthPlace rdfs:label ?birthPlaceEn FILTER(LANG(?birthPlaceEn) = "en").
      }}
      OPTIONAL {{ 
        ?item wdt:P20 ?deathPlace.
        ?deathPlace rdfs:label ?deathPlaceFr FILTER(LANG(?deathPlaceFr) = "fr").
        ?deathPlace rdfs:label ?deathPlaceEn FILTER(LANG(?deathPlaceEn) = "en").
      }}
      OPTIONAL {{
        ?item wdt:P135 ?movement.
        ?movement rdfs:label ?movementLabelFr FILTER(LANG(?movementLabelFr) = "fr").
      }}
      
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "fr".
        ?item rdfs:label ?itemLabelFr.
        ?item schema:description ?descFr.
      }}
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en".
        ?item rdfs:label ?itemLabelEn.
        ?item schema:description ?descEn.
      }}
    }}
    ORDER BY DESC(?sitelinks)
    LIMIT {limit}
    """
    print(f"Fetching {limit} artists with enriched data...")
    results = query_wikidata(query)
    
    # Group by item (multiple movements per artist)
    artists_map = {}
    for r in results:
        item_id = get_value(r, "item").split("/")[-1]
        name_fr = get_value(r, "itemLabelFr")
        
        if not name_fr or name_fr.startswith("Q"):
            continue
            
        if item_id not in artists_map:
            artists_map[item_id] = {
                "id": f"wd:{item_id}",
                "slug": slugify(name_fr),
                "type": "artist",
                "group": "peinture",
                "dates": {
                    "birth": parse_date(get_value(r, "birthDate")),
                    "death": parse_date(get_value(r, "deathDate"))
                },
                "locations": {
                    "birthPlace": {
                        "fr": get_value(r, "birthPlaceFr"),
                        "en": get_value(r, "birthPlaceEn")
                    },
                    "deathPlace": {
                        "fr": get_value(r, "deathPlaceFr"),
                        "en": get_value(r, "deathPlaceEn")
                    }
                },
                "relations": {
                    "movements": []
                },
                "text": {
                    "fr": {
                        "name": name_fr,
                        "short_description": get_value(r, "descFr", f"{name_fr}, artiste peintre.")[:170],
                        "description_long": f"<p>{get_value(r, 'descFr', f'{name_fr} est un artiste peintre.')}</p>",
                        "tags": ["peintre", "artiste"]
                    },
                    "en": {
                        "name": get_value(r, "itemLabelEn", name_fr),
                        "short_description": get_value(r, "descEn", f"{name_fr}, painter.")[:170],
                        "description_long": f"<p>{get_value(r, 'descEn', f'{name_fr} is a painter.')}</p>",
                        "tags": ["painter", "artist"]
                    }
                },
                "media": {
                    "has_image": bool(get_value(r, "image"))
                },
                "sources": [
                    {"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{item_id}"}
                ]
            }
        
        # Add movement if present
        movement = get_value(r, "movementLabelFr")
        if movement and movement not in [m for m in artists_map[item_id]["relations"]["movements"]]:
            movement_slug = slugify(movement)
            if movement_slug:
                artists_map[item_id]["relations"]["movements"].append(movement_slug)
    
    entities = [e for e in artists_map.values() if e["slug"]]
    print(f"  Found {len(entities)} artists")
    return entities

def fetch_movements(limit=80):
    """Fetch art movements with rich data"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn 
           ?startDate ?endDate ?image
    WHERE {{
      ?item wdt:P31 wd:Q968159.
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 8)
      
      OPTIONAL {{ ?item wdt:P580 ?startDate. }}
      OPTIONAL {{ ?item wdt:P582 ?endDate. }}
      OPTIONAL {{ ?item wdt:P18 ?image. }}
      
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "fr".
        ?item rdfs:label ?itemLabelFr.
        ?item schema:description ?descFr.
      }}
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en".
        ?item rdfs:label ?itemLabelEn.
        ?item schema:description ?descEn.
      }}
    }}
    ORDER BY DESC(?sitelinks)
    LIMIT {limit}
    """
    print(f"Fetching {limit} art movements...")
    results = query_wikidata(query)
    
    entities = []
    seen = set()
    for r in results:
        name_fr = get_value(r, "itemLabelFr")
        item_id = get_value(r, "item").split("/")[-1]
        
        if not name_fr or name_fr.startswith("Q") or item_id in seen:
            continue
        seen.add(item_id)
        
        slug = slugify(name_fr)
        if not slug:
            continue
            
        entities.append({
            "id": f"wd:{item_id}",
            "slug": slug,
            "type": "movement",
            "group": "art-moderne",
            "dates": {
                "start": parse_date(get_value(r, "startDate")),
                "end": parse_date(get_value(r, "endDate"))
            },
            "relations": {
                "artists": []  # Will be populated by cross-reference
            },
            "text": {
                "fr": {
                    "name": name_fr,
                    "short_description": get_value(r, "descFr", f"{name_fr}, mouvement artistique.")[:170],
                    "description_long": f"<p>{get_value(r, 'descFr', f'{name_fr} est un mouvement artistique.')}</p>",
                    "tags": ["mouvement", "art"]
                },
                "en": {
                    "name": get_value(r, "itemLabelEn", name_fr),
                    "short_description": get_value(r, "descEn", f"{name_fr}, art movement.")[:170],
                    "description_long": f"<p>{get_value(r, 'descEn', f'{name_fr} is an art movement.')}</p>",
                    "tags": ["movement", "art"]
                }
            },
            "media": {
                "has_image": bool(get_value(r, "image"))
            },
            "sources": [
                {"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{item_id}"}
            ]
        })
    
    print(f"  Found {len(entities)} movements")
    return entities

def fetch_artworks(limit=200):
    """Fetch famous paintings with rich data"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn 
           ?creationDate ?creatorLabelFr ?creatorSlug ?image
           ?locationLabelFr ?locationLabelEn
    WHERE {{
      ?item wdt:P31 wd:Q3305213.
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 12)
      
      OPTIONAL {{ ?item wdt:P571 ?creationDate. }}
      OPTIONAL {{ ?item wdt:P18 ?image. }}
      OPTIONAL {{ 
        ?item wdt:P170 ?creator.
        ?creator rdfs:label ?creatorLabelFr FILTER(LANG(?creatorLabelFr) = "fr").
      }}
      OPTIONAL {{
        ?item wdt:P276 ?location.
        ?location rdfs:label ?locationLabelFr FILTER(LANG(?locationLabelFr) = "fr").
        ?location rdfs:label ?locationLabelEn FILTER(LANG(?locationLabelEn) = "en").
      }}
      
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "fr".
        ?item rdfs:label ?itemLabelFr.
        ?item schema:description ?descFr.
      }}
      SERVICE wikibase:label {{
        bd:serviceParam wikibase:language "en".
        ?item rdfs:label ?itemLabelEn.
        ?item schema:description ?descEn.
      }}
    }}
    ORDER BY DESC(?sitelinks)
    LIMIT {limit}
    """
    print(f"Fetching {limit} artworks...")
    results = query_wikidata(query)
    
    entities = []
    seen = set()
    for r in results:
        name_fr = get_value(r, "itemLabelFr")
        item_id = get_value(r, "item").split("/")[-1]
        
        if not name_fr or name_fr.startswith("Q") or item_id in seen:
            continue
        seen.add(item_id)
        
        slug = slugify(name_fr)
        if not slug:
            continue
        
        creator_fr = get_value(r, "creatorLabelFr")
        creator_slug = slugify(creator_fr) if creator_fr else None
            
        entities.append({
            "id": f"wd:{item_id}",
            "slug": slug,
            "type": "artwork",
            "group": "peinture",
            "dates": {
                "created": parse_date(get_value(r, "creationDate"))
            },
            "locations": {
                "current": {
                    "fr": get_value(r, "locationLabelFr"),
                    "en": get_value(r, "locationLabelEn")
                }
            },
            "relations": {
                "artist": creator_slug
            },
            "text": {
                "fr": {
                    "name": name_fr,
                    "short_description": get_value(r, "descFr", f"{name_fr}, œuvre d'art.")[:170],
                    "description_long": "<p>" + get_value(r, "descFr", name_fr + " est une oeuvre.") + "</p>",
                    "tags": ["peinture", "oeuvre"]
                },
                "en": {
                    "name": get_value(r, "itemLabelEn", name_fr),
                    "short_description": get_value(r, "descEn", f"{name_fr}, artwork.")[:170],
                    "description_long": f"<p>{get_value(r, 'descEn', f'{name_fr} is an artwork.')}</p>",
                    "tags": ["painting", "artwork"]
                }
            },
            "media": {
                "has_image": bool(get_value(r, "image"))
            },
            "sources": [
                {"label": "Wikidata", "url": f"https://www.wikidata.org/wiki/{item_id}"}
            ]
        })
    
    print(f"  Found {len(entities)} artworks")
    return entities

def build_cross_references(entities):
    """Build bidirectional links between entities"""
    print("Building cross-references...")
    slug_map = {e["slug"]: e for e in entities}
    
    # Link movements to their artists
    for e in entities:
        if e["type"] == "artist":
            for mov_slug in e.get("relations", {}).get("movements", []):
                if mov_slug in slug_map and slug_map[mov_slug]["type"] == "movement":
                    if e["slug"] not in slug_map[mov_slug].get("relations", {}).get("artists", []):
                        slug_map[mov_slug].setdefault("relations", {}).setdefault("artists", []).append(e["slug"])
        
        # Link artworks to their artists
        if e["type"] == "artwork":
            artist_slug = e.get("relations", {}).get("artist")
            if artist_slug and artist_slug in slug_map:
                slug_map[artist_slug].setdefault("relations", {}).setdefault("works", []).append(e["slug"])
    
    return entities

def main():
    print("=" * 60)
    print("Fetching enriched data from Wikidata...")
    print(f"Started at: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)
    
    all_entities = []
    seen_slugs = set()
    
    # Fetch each type with delays for rate limiting
    for fetch_func in [fetch_artists, fetch_movements, fetch_artworks]:
        time.sleep(2)
        entities = fetch_func()
        for e in entities:
            if e["slug"] and e["slug"] not in seen_slugs:
                seen_slugs.add(e["slug"])
                all_entities.append(e)
    
    # Build cross-references
    all_entities = build_cross_references(all_entities)
    
    print("=" * 60)
    print(f"Total unique entities: {len(all_entities)}")
    print(f"  - Artists: {len([e for e in all_entities if e['type'] == 'artist'])}")
    print(f"  - Movements: {len([e for e in all_entities if e['type'] == 'movement'])}")
    print(f"  - Artworks: {len([e for e in all_entities if e['type'] == 'artwork'])}")
    
    # Save to file
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_entities, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved to {DATA_FILE}")
    print(f"Finished at: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 60)

if __name__ == "__main__":
    main()
