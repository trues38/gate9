import argparse
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent))

from orchestra.agent_orchestrator import run_orchestra

def main():
    parser = argparse.ArgumentParser(description="G9 Auto-SQL Orchestra CLI")
    parser.add_argument("query", nargs="?", default=None, help="Custom query for analysis")
    parser.add_argument("--country", default="KR", choices=["KR", "US", "JP", "CN"], help="Primary perspective")
    parser.add_argument("--level", default="G7", choices=["G3", "G7", "G9"], help="Report depth")
    
    args = parser.parse_args()

    print(f"🚀 Starting G9 Orchestra...")
    print(f"   Perspective: {args.country}")
    print(f"   Level: {args.level}")
    print(f"   Query: {args.query if args.query else 'Daily Auto Report'}")
    
    try:
        result = run_orchestra(
            country=args.country,
            level=args.level,
            mode="custom" if args.query else "daily",
            query=args.query
        )
        
        print("\n✅ Analysis Complete!")
        print("\n--- [Strategic Insight] ---\n")
        print(result.get('markdown_report', 'No report generated.'))
        
    except Exception as e:
        print(f"\n❌ Error: {e}")

if __name__ == "__main__":
    main()
