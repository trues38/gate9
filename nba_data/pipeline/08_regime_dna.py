import json
import os
import glob
import numpy as np
from tqdm import tqdm
from sklearn.metrics.pairwise import cosine_similarity

class RegimeDNAEngine:
    """
    Phase 2: Doppelganger Engine (Regime DNA).
    Matches current player vectors to historical "Main Characters".
    """
    
    DATA_DIR = "nba_data"
    LEGACY_RAW_DIR = os.path.join(DATA_DIR, "legacy_raw")
    VECTOR_DIR = os.path.join(DATA_DIR, "stories_vector_tags_v2")
    REGIME_DIR = os.path.join(DATA_DIR, "regimes")
    
    def __init__(self):
        os.makedirs(self.REGIME_DIR, exist_ok=True)
        # Load date map for season identification
        self.date_map = self._load_date_map()
        
    def _load_date_map(self):
        # We can reuse the map logic or just rely on the assumption for now
        # Ideally, legacy filename -> date mapping
        # For speed, let's just create a quick map if needed or extract from existing
        return {} 

    def get_legacy_game_ids(self):
        files = glob.glob(os.path.join(self.LEGACY_RAW_DIR, "*.json"))
        # legacy_123.json -> 123
        return set(os.path.basename(f).replace("legacy_", "").replace(".json", "") for f in files)

    def build_dna_bank(self):
        """
        Indexes the 1,856 Legacy Games into Player DNA Profiles.
        Returns: Dict { "Michael Jordan": [Vector], ... }
        """
        print("🧬 Indexing 30 Years of History (DNA Bank)...")
        legacy_ids = self.get_legacy_game_ids()
        
        # DNA Storage: { "Michael Jordan": [ [v1], [v2]... ] }
        player_vectors = {}
        
        # Scan all vector files, pick only Legacy ones
        vector_files = glob.glob(os.path.join(self.VECTOR_DIR, "*.jsonl"))
        
        processed_count = 0
        
        for fpath in tqdm(vector_files):
            gid = os.path.basename(fpath).replace(".jsonl", "")
            
            # Filter: Check if this is a Legacy Game
            if gid not in legacy_ids:
                continue
                
            try:
                with open(fpath, 'r') as f:
                    # Usually 1 line per file for v2
                    for line in f:
                        data = json.loads(line)
                        tags = data.get("vector_tags", {})
                        
                        # Who is the Main Character?
                        focus = tags.get("PlayerFocus", [])
                        if not focus:
                            continue
                            
                        embedding = data.get("embedding")
                        if not embedding:
                            continue
                            
                        # Attribute this game's DNA to the main characters
                        for player_name in focus:
                            if player_name not in player_vectors:
                                player_vectors[player_name] = []
                            player_vectors[player_name].append(embedding)
                            
                processed_count += 1
            except:
                pass

        print(f"✅ Indexed {processed_count} Historical Games.")
        print(f"🧬 Found {len(player_vectors)} Historical Figures.")
        
        # Consolidate into Mean Vectors (The "Season Archetype")
        dna_bank = []
        for name, vectors in player_vectors.items():
            if len(vectors) < 3: continue # Filter noise (needs at least 3 games to form a "Regime")
            
            mean_vec = np.mean(vectors, axis=0).tolist()
            dna_bank.append({
                "name": name,
                "vector": mean_vec,
                "sample_size": len(vectors),
                "era": "Legacy" 
            })
            
        return dna_bank

    def find_doppelgangers(self, current_players, dna_bank):
        """
        Input: Current Players (with latent_vector).
        Output: Enhanced Player Dict with 'Doppelganger' field.
        """
        print("🔍 Searching for Historical Doppelgangers...")
        
        if not dna_bank:
            print("❌ DNA Bank empty.")
            return []
            
        # Prepare Matrix for Bulk Search
        bank_vectors = np.array([d['vector'] for d in dna_bank])
        bank_names = [d['name'] for d in dna_bank]
        
        enhanced_regimes = []
        
        for player in tqdm(current_players):
            current_vec = player.get('latent_vector')
            if not current_vec:
                enhanced_regimes.append(player)
                continue
                
            # Cosine Similarity
            # Reshape current_vec to (1, 1024)
            sims = cosine_similarity([current_vec], bank_vectors)[0]
            
            # Find Top 3 Matches
            top_indices = sims.argsort()[-3:][::-1]
            
            matches = []
            for idx in top_indices:
                score = float(sims[idx])
                matches.append({
                    "name": bank_names[idx],
                    "similarity": round(score * 100, 1),
                    "era": "Legacy"
                })
                
            # Add to Player Object
            player['regime']['doppelganger'] = matches
            enhanced_regimes.append(player)
            
        return enhanced_regimes

    def run(self):
        # 1. Load Current Regimes
        current_path = os.path.join(self.REGIME_DIR, "current_regimes.json")
        if not os.path.exists(current_path):
            print("❌ No current regimes found. Run Phase 1 first.")
            return

        with open(current_path, 'r') as f:
            current_players = json.load(f)
            
        # 2. Build DNA Bank (History)
        dna_bank = self.build_dna_bank()
        
        # 3. Match
        final_results = self.find_doppelgangers(current_players, dna_bank)
        
        # 4. Save
        out_path = os.path.join(self.REGIME_DIR, "regimes_with_dna.json")
        with open(out_path, 'w') as f:
            json.dump(final_results, f, indent=2)
            
        print(f"✅ DNA Analysis Complete. Saved to {out_path}")
        
        # Sample Output
        if final_results:
            sample = final_results[0]
            print("\nSAMPLE MATCH:")
            print(f"Player: {sample['name']}")
            print(f"Doppelgangers: {sample['regime'].get('doppelganger')}")

if __name__ == "__main__":
    engine = RegimeDNAEngine()
    engine.run()
