#!/usr/bin/env python3
"""
경제 이벤트 화이트리스트 설정 도우미
Twitter 계정 검증 및 n8n 워크플로우용 배열 생성
"""

import json
from typing import List, Dict

# 3-Tier 화이트리스트 정의
WHITELIST = {
    "tier1": {
        "name": "Central Banks & Government",
        "description": "중앙은행, 정부 기관 (최고 신뢰도)",
        "accounts": [
            {"handle": "federalreserve", "name": "Federal Reserve", "region": "US"},
            {"handle": "ecb", "name": "European Central Bank", "region": "EU"},
            {"handle": "bankofengland", "name": "Bank of England", "region": "UK"},
            {"handle": "federalreserve", "name": "Federal Reserve", "region": "US"},
            {"handle": "federalreserve", "name": "Federal Reserve", "region": "US"},
            {"handle": "BIS_org", "name": "Bank for International Settlements", "region": "Global"},
            {"handle": "USTreasury", "name": "US Department of the Treasury", "region": "US"},
            {"handle": "IMFNews", "name": "International Monetary Fund", "region": "Global"},
            {"handle": "WorldBank", "name": "World Bank", "region": "Global"},
        ]
    },
    "tier2": {
        "name": "Financial Media",
        "description": "주요 금융 언론사 (높은 신뢰도)",
        "accounts": [
            {"handle": "business", "name": "Bloomberg", "region": "Global"},
            {"handle": "markets", "name": "Bloomberg Markets", "region": "Global"},
            {"handle": "ReutersMarkets", "name": "Reuters Markets", "region": "Global"},
            {"handle": "FT", "name": "Financial Times", "region": "Global"},
            {"handle": "WSJ", "name": "Wall Street Journal", "region": "Global"},
            {"handle": "economics", "name": "The Economist", "region": "Global"},
            {"handle": "MarketWatch", "name": "MarketWatch", "region": "US"},
            {"handle": "YahooFinance", "name": "Yahoo Finance", "region": "Global"},
        ]
    },
    "tier3": {
        "name": "Analysts & Quants",
        "description": "저명한 분석가, 퀀트 (중간 신뢰도)",
        "accounts": [
            {"handle": "RaoulGMI", "name": "Raoul Pal", "specialty": "Macro"},
            {"handle": "LynAldenContact", "name": "Lyn Alden", "specialty": "Macro/Bitcoin"},
            {"handle": "MacroAlf", "name": "Alfonso Peccatiello", "specialty": "Macro Strategy"},
            {"handle": "jam_croissant", "name": "Jawad Mian", "specialty": "Macro"},
            {"handle": "StanChart", "name": "Standard Chartered Research", "specialty": "Bank Research"},
            {"handle": "GoldmanSachs", "name": "Goldman Sachs Research", "specialty": "Bank Research"},
            {"handle": "MorganStanley", "name": "Morgan Stanley Research", "specialty": "Bank Research"},
            {"handle": "boes_", "name": "Brent Donnelly", "specialty": "FX/Rates"},
            {"handle": "concodanomics", "name": "Concoda Economics", "specialty": "Economic Data"},
        ]
    }
}

def print_whitelist_summary():
    """화이트리스트 요약 출력"""
    print("=" * 80)
    print("경제 이벤트 파이프라인 화이트리스트")
    print("=" * 80)

    total_accounts = 0
    for tier_key, tier_data in WHITELIST.items():
        tier_num = tier_key[-1]
        count = len(tier_data['accounts'])
        total_accounts += count

        print(f"\n{tier_data['name']} (Tier {tier_num})")
        print(f"{tier_data['description']}")
        print(f"계정 수: {count}개\n")

        for account in tier_data['accounts']:
            handle = account['handle']
            name = account['name']
            extra = account.get('region') or account.get('specialty', '')
            print(f"  @{handle:20s} - {name:40s} [{extra}]")

    print(f"\n{'='*80}")
    print(f"총 화이트리스트 계정: {total_accounts}개")
    print(f"{'='*80}\n")

def generate_n8n_code():
    """n8n 워크플로우용 JavaScript 코드 생성"""
    print("\n" + "=" * 80)
    print("n8n Switch 노드용 JavaScript 코드")
    print("=" * 80)
    print("""
// 복사해서 n8n의 'Switch (Whitelist Check)' 노드에 붙여넣기

// Tier 1: Central Banks & Government (최고 신뢰도)
const tier1 = [""")

    for account in WHITELIST['tier1']['accounts']:
        print(f"  '{account['handle']}',  // {account['name']}")

    print("];\n\n// Tier 2: Financial Media (높은 신뢰도)\nconst tier2 = [")

    for account in WHITELIST['tier2']['accounts']:
        print(f"  '{account['handle']}',  // {account['name']}")

    print("];\n\n// Tier 3: Analysts & Quants (중간 신뢰도)\nconst tier3 = [")

    for account in WHITELIST['tier3']['accounts']:
        specialty = account.get('specialty', 'Unknown')
        print(f"  '{account['handle']}',  // {account['name']} - {specialty}")

    print("""];

// 트위터 핸들 추출 (대소문자 무시)
const username = $json.user.username.toLowerCase();

// Tier 매칭
if (tier1.includes(username)) {
  return { tier: 1, trust: 'high' };
} else if (tier2.includes(username)) {
  return { tier: 2, trust: 'medium' };
} else if (tier3.includes(username)) {
  return { tier: 3, trust: 'medium-low' };
} else {
  return null; // 화이트리스트에 없음 → 필터링
}
""")

def generate_twitter_list_url():
    """Twitter List 생성용 핸들 목록"""
    all_handles = []
    for tier_data in WHITELIST.values():
        for account in tier_data['accounts']:
            all_handles.append(account['handle'])

    print("\n" + "=" * 80)
    print("Twitter List 생성 가이드")
    print("=" * 80)
    print("""
1. Twitter에 로그인
2. Lists → Create a new list
3. 이름: "Economic Event Monitor"
4. Description: "경제 이벤트 파이프라인용 화이트리스트"
5. Private로 설정 (선택)
6. 아래 계정들을 추가:
""")

    for handle in all_handles:
        print(f"   @{handle}")

    print(f"\n총 {len(all_handles)}개 계정")

def export_json(filepath: str = "/Users/js/g9/config/economic_whitelist.json"):
    """JSON 파일로 내보내기"""
    output = {
        "version": "1.0",
        "updated": "2025-12-25",
        "whitelist": WHITELIST
    }

    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 화이트리스트를 JSON으로 저장: {filepath}")

def main():
    print("\n경제 이벤트 파이프라인 - 화이트리스트 설정 도우미\n")

    while True:
        print("선택하세요:")
        print("  1. 화이트리스트 요약 보기")
        print("  2. n8n Switch 노드 코드 생성")
        print("  3. Twitter List 생성 가이드")
        print("  4. JSON 파일로 내보내기")
        print("  5. 전체 실행")
        print("  0. 종료")

        choice = input("\n선택 (0-5): ").strip()

        if choice == '1':
            print_whitelist_summary()
        elif choice == '2':
            generate_n8n_code()
        elif choice == '3':
            generate_twitter_list_url()
        elif choice == '4':
            export_json()
        elif choice == '5':
            print_whitelist_summary()
            generate_n8n_code()
            generate_twitter_list_url()
            export_json()
            break
        elif choice == '0':
            print("\n종료합니다.")
            break
        else:
            print("\n잘못된 입력입니다. 다시 선택하세요.")

        input("\n[Enter]를 눌러 계속...")

if __name__ == "__main__":
    main()
