import os
import json
import csv
import re
import sys
from tqdm import tqdm

# Increase CSV field size limit
csv.field_size_limit(sys.maxsize)

def load_json_map(path):
    if not os.path.exists(path):
        print(f"Warning: {path} not found.")
        return {}
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def build_keyword_map(json_data):
    """
    Flattens the nested JSON map into a single dict {keyword_lower: value}
    """
    lookup = {}
    for category, items in json_data.items():
        for keyword, value in items.items():
            if keyword:
                lookup[keyword.strip().lower()] = value
    return lookup

def build_regex(keywords):
    if not keywords:
        return None
    # Sort by length desc
    sorted_kws = sorted(keywords, key=len, reverse=True)
    escaped = [re.escape(k) for k in sorted_kws]
    # Use word boundaries
    pattern_str = "|".join(escaped)
    final_pattern = r'\b(' + pattern_str + r')\b'
    return re.compile(final_pattern, re.IGNORECASE)

def process_csv(input_csv, output_csv, concept_map, inference_map):
    print(f"Processing {input_csv} -> {output_csv}...")
    
    # Build lookups
    concept_lookup = build_keyword_map(concept_map)
    inference_lookup = build_keyword_map(inference_map)
    
    concept_regex = build_regex(list(concept_lookup.keys()))
    inference_regex = build_regex(list(inference_lookup.keys()))
    
    events = []
    
    with open(input_csv, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if "concepts" not in fieldnames:
            fieldnames.append("concepts")
            
        for row in tqdm(reader, desc="Mapping Concepts"):
            title = row.get("title", "")
            summary = row.get("summary", "")
            text_to_scan = f"{title} {summary}".strip()
            
            # 1. Concept Mapping
            found_concepts = set()
            if concept_regex:
                matches = concept_regex.findall(text_to_scan)
                for m in matches:
                    val = concept_lookup.get(m.lower())
                    if val:
                        found_concepts.add(val)
            
            # Add existing concepts if any (though usually none in input)
            existing = row.get("concepts", "")
            if existing:
                found_concepts.update([c.strip() for c in existing.split(",") if c.strip()])
            
            row["concepts"] = ",".join(sorted(list(found_concepts)))
            
            # 2. Inference Mapping (Fill missing ticker)
            if not row.get("ticker") and inference_regex:
                matches = inference_regex.findall(text_to_scan)
                for m in matches:
                    val = inference_lookup.get(m.lower())
                    if val:
                        row["ticker"] = val
                        break # Take first match
            
            events.append(row)
            
    # Save
    with open(output_csv, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(events)
    print("Done.")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Apply concepts to CSV")
    parser.add_argument("--input", help="Input CSV path")
    parser.add_argument("--output", help="Output CSV path")
    args = parser.parse_args()

    BASE_DIR = "/Users/js/g9"
    CONCEPT_MAP_PATH = os.path.join(BASE_DIR, "ticker_global/concept_map.json")
    INFERENCE_MAP_PATH = os.path.join(BASE_DIR, "ticker_global/inference_rules.json")
    
    # Default paths
    INPUT_CSV = args.input if args.input else os.path.join(BASE_DIR, "ticker_global/US/cleaned_events_final.csv")
    OUTPUT_CSV = args.output if args.output else os.path.join(BASE_DIR, "ticker_global/US/cleaned_events_final_with_concepts.csv")
    
    # Check if input exists
    if not os.path.exists(INPUT_CSV):
        print(f"Input file {INPUT_CSV} not found. Please run pipeline_us.py first.")
        exit(1)
        
    concept_map = load_json_map(CONCEPT_MAP_PATH)
    inference_map = load_json_map(INFERENCE_MAP_PATH)
    
    process_csv(INPUT_CSV, OUTPUT_CSV, concept_map, inference_map)
