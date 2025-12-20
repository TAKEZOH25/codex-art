"""
Fetches art data from Wikidata SPARQL endpoint and populates entities.json
"""
import requests
import json
import time
import re
from pathlib import Path

ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "Accept": "application/sparql-results+json",
    "User-Agent": "ArtVirtuosoSSG/1.0 (contact: support@art-virtuoso.com)"
}

BASE_DIR = Path(__file__).parent.parent
DATA_FILE = BASE_DIR / "data" / "entities.json"

def slugify(text):
    """Convert text to URL-friendly slug"""
    text = text.lower().strip()
    text = re.sub(r'[àáâãäå]', 'a', text)
    text = re.sub(r'[èéêë]', 'e', text)
    text = re.sub(r'[ìíîï]', 'i', text)
    text = re.sub(r'[òóôõö]', 'o', text)
    text = re.sub(r'[ùúûü]', 'u', text)
    text = re.sub(r'[ç]', 'c', text)
    text = re.sub(r'[ñ]', 'n', text)
    text = re.sub(r'[^a-z0-9\s-]', '', text)
    text = re.sub(r'[\s_]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')

def query_wikidata(sparql_query, limit=100):
    """Execute SPARQL query and return results"""
    try:
        r = requests.get(
            ENDPOINT,
            params={"query": sparql_query, "format": "json"},
            headers=HEADERS,
            timeout=60
        )
        r.raise_for_status()
        return r.json().get("results", {}).get("bindings", [])
    except Exception as e:
        print(f"Query error: {e}")
        return []

def fetch_artists(limit=100):
    """Fetch famous painters from Wikidata"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn ?image WHERE {{
      ?item wdt:P31 wd:Q5;           # Human
            wdt:P106 wd:Q1028181.    # Painter occupation
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 20)        # At least 20 Wikipedia links (notable)
      
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
    print(f"Fetching {limit} artists...")
    results = query_wikidata(query)
    
    entities = []
    for r in results:
        name_fr = r.get("itemLabelFr", {}).get("value", "")
        name_en = r.get("itemLabelEn", {}).get("value", name_fr)
        desc_fr = r.get("descFr", {}).get("value", "Artiste peintre")
        desc_en = r.get("descEn", {}).get("value", "Painter")
        item_id = r.get("item", {}).get("value", "").split("/")[-1]
        
        if not name_fr or name_fr.startswith("Q"):
            continue
            
        slug = slugify(name_fr)
        if not slug:
            continue
            
        entities.append({
            "id": f"wd:{item_id}",
            "slug": slug,
            "type": "artist",
            "group": "peinture",
            "text": {
                "fr": {
                    "name": name_fr,
                    "short_description": desc_fr[:170] if desc_fr else f"{name_fr}, artiste peintre.",
                    "description_long": f"<p>{desc_fr}</p>" if desc_fr else f"<p>{name_fr} est un artiste peintre.</p>",
                    "tags": ["peintre"]
                },
                "en": {
                    "name": name_en,
                    "short_description": desc_en[:170] if desc_en else f"{name_en}, painter.",
                    "description_long": f"<p>{desc_en}</p>" if desc_en else f"<p>{name_en} is a painter.</p>",
                    "tags": ["painter"]
                }
            },
            "media": {
                "has_image": bool(r.get("image"))
            }
        })
    
    print(f"  Found {len(entities)} artists")
    return entities

def fetch_movements(limit=50):
    """Fetch art movements from Wikidata"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn WHERE {{
      ?item wdt:P31 wd:Q968159.      # Art movement
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 10)
      
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
    for r in results:
        name_fr = r.get("itemLabelFr", {}).get("value", "")
        name_en = r.get("itemLabelEn", {}).get("value", name_fr)
        desc_fr = r.get("descFr", {}).get("value", "Mouvement artistique")
        desc_en = r.get("descEn", {}).get("value", "Art movement")
        item_id = r.get("item", {}).get("value", "").split("/")[-1]
        
        if not name_fr or name_fr.startswith("Q"):
            continue
            
        slug = slugify(name_fr)
        if not slug:
            continue
            
        entities.append({
            "id": f"wd:{item_id}",
            "slug": slug,
            "type": "movement",
            "group": "art-moderne",
            "text": {
                "fr": {
                    "name": name_fr,
                    "short_description": desc_fr[:170] if desc_fr else f"{name_fr}, mouvement artistique.",
                    "description_long": f"<p>{desc_fr}</p>",
                    "tags": ["mouvement"]
                },
                "en": {
                    "name": name_en,
                    "short_description": desc_en[:170] if desc_en else f"{name_en}, art movement.",
                    "description_long": f"<p>{desc_en}</p>",
                    "tags": ["movement"]
                }
            }
        })
    
    print(f"  Found {len(entities)} movements")
    return entities

def fetch_artworks(limit=100):
    """Fetch famous paintings from Wikidata"""
    query = f"""
    SELECT DISTINCT ?item ?itemLabelFr ?itemLabelEn ?descFr ?descEn ?image WHERE {{
      ?item wdt:P31 wd:Q3305213.     # Painting
      ?item wikibase:sitelinks ?sitelinks.
      FILTER(?sitelinks > 15)
      
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
    print(f"Fetching {limit} artworks...")
    results = query_wikidata(query)
    
    entities = []
    for r in results:
        name_fr = r.get("itemLabelFr", {}).get("value", "")
        name_en = r.get("itemLabelEn", {}).get("value", name_fr)
        desc_fr = r.get("descFr", {}).get("value", "Peinture")
        desc_en = r.get("descEn", {}).get("value", "Painting")
        item_id = r.get("item", {}).get("value", "").split("/")[-1]
        
        if not name_fr or name_fr.startswith("Q"):
            continue
            
        slug = slugify(name_fr)
        if not slug:
            continue
            
        entities.append({
            "id": f"wd:{item_id}",
            "slug": slug,
            "type": "artwork",
            "group": "peinture",
            "text": {
                "fr": {
                    "name": name_fr,
                    "short_description": desc_fr[:170] if desc_fr else f"{name_fr}, œuvre d'art.",
                    "description_long": f"<p>{desc_fr}</p>",
                    "tags": ["peinture", "oeuvre"]
                },
                "en": {
                    "name": name_en,
                    "short_description": desc_en[:170] if desc_en else f"{name_en}, artwork.",
                    "description_long": f"<p>{desc_en}</p>",
                    "tags": ["painting", "artwork"]
                }
            },
            "media": {
                "has_image": bool(r.get("image"))
            }
        })
    
    print(f"  Found {len(entities)} artworks")
    return entities

def main():
    print("=" * 50)
    print("Fetching data from Wikidata...")
    print("=" * 50)
    
    all_entities = []
    seen_slugs = set()
    
    # Fetch each type
    for entities in [
        fetch_artists(150),
        fetch_movements(50),
        fetch_artworks(150)
    ]:
        time.sleep(1)  # Rate limiting
        for e in entities:
            if e["slug"] not in seen_slugs:
                seen_slugs.add(e["slug"])
                all_entities.append(e)
    
    print("=" * 50)
    print(f"Total unique entities: {len(all_entities)}")
    
    # Save to file
    DATA_FILE.parent.mkdir(exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(all_entities, f, ensure_ascii=False, indent=2)
    
    print(f"Saved to {DATA_FILE}")
    print("=" * 50)

if __name__ == "__main__":
    main()
