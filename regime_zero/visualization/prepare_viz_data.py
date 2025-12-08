import json
import os
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

OBJECTS_FILE = "regime_zero/data/regime_objects.jsonl"
FAMILIES_FILE = "regime_zero/data/regime_families.json"
OUTPUT_FILE = "regime_zero/visualization/viz_data.json"
LIMIT = 5000  # Limit to last N days for performance

def prepare_data():
    nodes = []
    links = []
    
    # 1. Load Objects (Nodes)
    regimes = {}
    if os.path.exists(OBJECTS_FILE):
        with open(OBJECTS_FILE, "r") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    regimes[r['date']] = r
                except:
                    pass
                    
    # Sort and slice to limit
    sorted_dates = sorted(regimes.keys())
    if len(sorted_dates) > LIMIT:
        print(f"⚠️ Truncating visualization to last {LIMIT} days (from {len(sorted_dates)} total).")
        sorted_dates = sorted_dates[-LIMIT:]
        # Filter regimes dict
        regimes = {d: regimes[d] for d in sorted_dates}
    
    # 2. Load Families (Clusters)
    families = []
    if os.path.exists(FAMILIES_FILE):
        with open(FAMILIES_FILE, "r") as f:
            try:
                families = json.load(f)
            except:
                pass
                
    # 3. Build Graph
    # Map dates to family names
    date_to_family = {}
    for fam in families:
        for date in fam['member_dates']:
            date_to_family[date] = fam['family_name']
            
    # Create Nodes
    for date, r in regimes.items():
        family = date_to_family.get(date, "Unclustered")
        
        nodes.append({
            "id": date,
            "name": r['regime_name'],
            "date": date,
            "group": family,
            "val": 1, # Size
            "desc": r.get('structural_reasoning', 'No description.'),
            "signature": r.get('signature', []),
            "risks": r.get('risks', []),
            "upside": r.get('upside', []),
            "vibe": r.get('historical_vibe', '')
        })
        
    # Create Links (Temporal or Semantic)
    # For now, link consecutive days to show time flow
    for i in range(len(sorted_dates) - 1):
        links.append({
            "source": sorted_dates[i],
            "target": sorted_dates[i+1],
            "value": 1
        })
        
    # Also link members of the same family to a central "Family Node" (optional)
    # Or just let color handle it.
    # Let's add links between same family members to create clusters
    # Only link if both nodes exist in our sliced set
    existing_dates = set(regimes.keys())
    
    for fam in families:
        members = [m for m in fam['member_dates'] if m in existing_dates]
        # Link all to the first member (star topology) or chain them
        if len(members) > 1:
            center = members[0]
            for m in members[1:]:
                links.append({
                    "source": center,
                    "target": m,
                    "value": 2
                })

    graph_data = {
        "nodes": nodes,
        "links": links
    }
    
    with open(OUTPUT_FILE, "w") as f:
        json.dump(graph_data, f, indent=2)
        
    print(f"✅ Prepared visualization data: {len(nodes)} nodes, {len(links)} links.")

if __name__ == "__main__":
    prepare_data()
