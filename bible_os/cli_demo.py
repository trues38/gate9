import sys
from engine import MeaningEngine

def main():
    print("Initializing Bible Meaning OS Engine...")
    try:
        engine = MeaningEngine()
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    print("\n=== Bible Meaning Cloud (CLI Demo) ===")
    print("Type your concern, feeling, or situation. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("User >> ").strip()
            if not user_input:
                continue
            if user_input.lower() in ["exit", "stop", "quit"]:
                print("Goodbye.")
                break
                
            print("\n... Analyzing Regime ...")
            regimes = engine.identify_regime(user_input)
            
            if not regimes:
                print("Could not identify a clear regime. Please try again with more detail.")
                continue
                
            selected_regime = regimes[0]
            print(f"Detected Regime: {selected_regime}")
            
            print("... Searching Verses (Vector Search) ...")
            verses = engine.retrieve_verses(user_input, selected_regime, limit=1)
            
            if not verses:
                print("No suitable verses found.")
                continue
                
            v = verses[0]
            print(f"Selected Context: {v['ref']} (Score: {v.get('score', 'N/A'):.4f})")
            
            print("... Synthesizing Interpretation ...\n")
            response = engine.synthesize_interpretation(user_input, selected_regime, v)
            
            print("=== AI COUNSELOR ===")
            print(response)
            print("====================\n")
            
        except KeyboardInterrupt:
            print("\nGoodbye.")
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    main()
