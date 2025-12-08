def print_summary(results):
    """
    Prints a summary of backtest results.
    results: list of dicts {date, ticker, return_pct, is_success}
    """
    total = len(results)
    if total == 0:
        print("\n📊 No trades executed.")
        return

    successes = [r for r in results if r['is_success']]
    success_count = len(successes)
    success_rate = (success_count / total) * 100
    
    avg_return = sum(r['return_pct'] for r in results) / total
    
    print("\n" + "="*40)
    print("📊 BACKTEST SUMMARY REPORT")
    print("="*40)
    print(f"Total Trades: {total}")
    print(f"Successes   : {success_count}")
    print(f"Success Rate: {success_rate:.1f}%")
    print(f"Avg Return  : {avg_return:.2f}%")
    print("-" * 40)
    
    print("Top Performers:")
    sorted_results = sorted(results, key=lambda x: x['return_pct'], reverse=True)
    for r in sorted_results[:5]:
        status = "✅" if r['is_success'] else "❌"
        z_info = ""
        # We need to pass scores to results in backtest_runner first, but assuming we might add it later.
        # For now, let's just print what we have.
        print(f"{status} {r['date']} {r['ticker']}: {r['return_pct']:.2f}%")
        
    print("="*40)
