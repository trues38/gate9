import json

with open("historical_test_results.json", "r") as f:
    results = json.load(f)

total = len(results)
correct = sum(1 for r in results if r['correct'])
real_news_count = sum(1 for r in results if r.get('news_source') == 'Real')

print(f"📊 Summary:")
print(f"   Total Events: {total}")
print(f"   Win Rate: {correct}/{total} ({correct/total:.1%})")
print(f"   Real News Used: {real_news_count}/{total}")

print("\n🔍 COVID-19 Check (2020-03-11):")
for r in results:
    if r['date'] == "2020-03-11":
        print(f"   Action: {r['decision']['action']}")
        print(f"   Meta-RAG Status: {r['decision'].get('meta_rag_status')}")
        print(f"   Reason: {r['decision'].get('reason')}")
