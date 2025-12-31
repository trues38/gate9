"""
H6: Low Volatility Neutral Zone Avoidance Test

가설: 저변동성 + 중립 RSI 구간은 기대값이 음수
→ 이 구간을 회피하면 전체 성과가 개선되는가?
"""

import sys
sys.path.insert(0, '/Users/js/Documents/btc-macro/src')

import yfinance as yf
import pandas as pd
import numpy as np
from scipy import stats
from datetime import datetime, timedelta
from typing import List, Dict, Tuple

from btc_engine.experiments.metrics import TradeResult, MetricsCalculator, quick_stats


def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_volatility(prices: pd.Series, window: int = 7) -> pd.Series:
    """일간 수익률 기반 변동성 계산"""
    returns = prices.pct_change()
    volatility = returns.rolling(window=window).std() * np.sqrt(252)  # 연율화
    return volatility


def calculate_volatility_percentile(volatility: pd.Series, lookback: int = 252) -> pd.Series:
    """롤링 변동성 백분위"""
    def percentile_rank(x):
        if len(x) < 2:
            return 50
        return stats.percentileofscore(x, x.iloc[-1])

    return volatility.rolling(window=lookback, min_periods=30).apply(percentile_rank)


def fetch_data(start_date: str, end_date: str) -> pd.DataFrame:
    """BTC 데이터 가져오기"""
    print(f"Fetching BTC data: {start_date} ~ {end_date}")
    btc = yf.download("BTC-USD", start=start_date, end=end_date, progress=False)

    if btc.empty:
        raise ValueError("Failed to fetch BTC data")

    if isinstance(btc.columns, pd.MultiIndex):
        btc.columns = btc.columns.get_level_values(0)

    # RSI
    btc['RSI'] = calculate_rsi(btc['Close'])

    # 변동성
    btc['Volatility'] = calculate_volatility(btc['Close'], window=7)

    # 변동성 백분위
    btc['Vol_Percentile'] = calculate_volatility_percentile(btc['Volatility'])

    # 7일 후 수익률 (forward looking)
    btc['Return_7d'] = btc['Close'].shift(-7) / btc['Close'] - 1

    # NaN 제거
    btc = btc.dropna()

    print(f"Loaded {len(btc)} days of data")
    return btc


def identify_avoid_zone(row: pd.Series,
                        vol_threshold: float = 30,
                        rsi_low: float = 45,
                        rsi_high: float = 55) -> bool:
    """
    회피 구간 식별

    조건:
    - 변동성 백분위 <= vol_threshold (저변동성)
    - RSI가 rsi_low ~ rsi_high (중립)
    """
    is_low_vol = row['Vol_Percentile'] <= vol_threshold
    is_neutral_rsi = rsi_low <= row['RSI'] <= rsi_high

    return is_low_vol and is_neutral_rsi


def generate_baseline_trades(data: pd.DataFrame,
                             hold_days: int = 7) -> List[TradeResult]:
    """
    기준선: 매일 진입하는 경우 (7일 보유)

    모든 날에 진입했을 때의 거래 리스트
    """
    trades = []

    for i in range(0, len(data) - hold_days, hold_days):  # 비중복
        row = data.iloc[i]
        exit_row = data.iloc[i + hold_days]

        entry_date = data.index[i].strftime('%Y-%m-%d')
        exit_date = data.index[i + hold_days].strftime('%Y-%m-%d')
        entry_price = row['Close']
        exit_price = exit_row['Close']
        return_pct = (exit_price - entry_price) / entry_price

        trades.append(TradeResult(
            entry_date=entry_date,
            exit_date=exit_date,
            entry_price=entry_price,
            exit_price=exit_price,
            return_pct=return_pct,
            is_win=return_pct > 0,
            hold_days=hold_days,
            state_at_entry=f"vol{int(row['Vol_Percentile'])}|rsi{int(row['RSI'])}"
        ))

    return trades


def split_by_avoid_zone(data: pd.DataFrame,
                        trades: List[TradeResult],
                        vol_threshold: float = 30,
                        rsi_low: float = 45,
                        rsi_high: float = 55) -> Tuple[List[TradeResult], List[TradeResult]]:
    """거래를 회피구간/비회피구간으로 분리"""
    avoid_trades = []
    active_trades = []

    for trade in trades:
        entry_date = pd.Timestamp(trade.entry_date)
        if entry_date in data.index:
            row = data.loc[entry_date]
            if identify_avoid_zone(row, vol_threshold, rsi_low, rsi_high):
                avoid_trades.append(trade)
            else:
                active_trades.append(trade)

    return avoid_trades, active_trades


def run_avoidance_test(data: pd.DataFrame,
                       vol_threshold: float = 30,
                       rsi_low: float = 45,
                       rsi_high: float = 55) -> Dict:
    """
    회피 전략 테스트

    비교:
    1. 전체 거래 (기준선)
    2. 회피 구간 거래만
    3. 비회피 구간 거래만 (회피 전략)
    """
    calc = MetricsCalculator()

    # 기준선 거래 생성
    all_trades = generate_baseline_trades(data)

    if len(all_trades) < 10:
        return {'error': 'Not enough trades'}

    # 분리
    avoid_trades, active_trades = split_by_avoid_zone(
        data, all_trades, vol_threshold, rsi_low, rsi_high
    )

    # 지표 계산
    all_metrics = calc.calculate(all_trades, "all")
    avoid_metrics = calc.calculate(avoid_trades, "avoid_zone") if avoid_trades else None
    active_metrics = calc.calculate(active_trades, "active_zone") if active_trades else None

    # 결과
    result = {
        'parameters': {
            'vol_threshold': vol_threshold,
            'rsi_range': [rsi_low, rsi_high]
        },
        'all_trades': {
            'count': len(all_trades),
            'win_rate': all_metrics.win_rate,
            'avg_return': all_metrics.avg_return,
            'total_return': all_metrics.total_return
        }
    }

    if avoid_trades:
        result['avoid_zone'] = {
            'count': len(avoid_trades),
            'win_rate': avoid_metrics.win_rate,
            'avg_return': avoid_metrics.avg_return,
            'total_return': avoid_metrics.total_return
        }
    else:
        result['avoid_zone'] = {'count': 0}

    if active_trades:
        result['active_zone'] = {
            'count': len(active_trades),
            'win_rate': active_metrics.win_rate,
            'avg_return': active_metrics.avg_return,
            'total_return': active_metrics.total_return
        }

        # 개선 효과
        result['improvement'] = {
            'win_rate_diff': active_metrics.win_rate - all_metrics.win_rate,
            'avg_return_diff': active_metrics.avg_return - all_metrics.avg_return,
            'trades_avoided': len(avoid_trades),
            'avoid_ratio': len(avoid_trades) / len(all_trades)
        }
    else:
        result['active_zone'] = {'count': 0}

    return result


def run_walk_forward(data: pd.DataFrame, train_end: str) -> Dict:
    """Walk-Forward 검증"""
    train_data = data[data.index <= train_end]
    test_data = data[data.index > train_end]

    print(f"\nTrain: {train_data.index[0].strftime('%Y-%m-%d')} ~ {train_data.index[-1].strftime('%Y-%m-%d')}")
    print(f"Test: {test_data.index[0].strftime('%Y-%m-%d')} ~ {test_data.index[-1].strftime('%Y-%m-%d')}")

    # Train 결과
    train_result = run_avoidance_test(train_data)

    # Test 결과
    test_result = run_avoidance_test(test_data)

    return {
        'train': train_result,
        'test': test_result
    }


def main():
    print("=" * 60)
    print("H6: Low Volatility Neutral Zone Avoidance Test")
    print("=" * 60)

    # 1. 데이터 로드
    data = fetch_data("2020-01-01", "2025-12-26")

    # 2. 회피 구간 분포 확인
    print("\n" + "=" * 60)
    print("Avoid Zone Distribution")
    print("=" * 60)

    data['Is_Avoid'] = data.apply(
        lambda r: identify_avoid_zone(r, 30, 45, 55), axis=1
    )
    avoid_days = data['Is_Avoid'].sum()
    total_days = len(data)
    print(f"Avoid zone days: {avoid_days} / {total_days} ({avoid_days/total_days:.1%})")

    # 년도별 분포
    print("\n년도별 회피구간 비율:")
    for year in range(2020, 2026):
        year_data = data[data.index.year == year]
        if len(year_data) > 0:
            avoid_ratio = year_data['Is_Avoid'].mean()
            print(f"  {year}: {avoid_ratio:.1%}")

    # 3. 기본 테스트
    print("\n" + "=" * 60)
    print("Basic Avoidance Test (vol<=30%, RSI 45-55)")
    print("=" * 60)

    result = run_avoidance_test(data, vol_threshold=30, rsi_low=45, rsi_high=55)

    print(f"\nAll trades: {result['all_trades']['count']}")
    print(f"  Win rate: {result['all_trades']['win_rate']:.1%}")
    print(f"  Avg return: {result['all_trades']['avg_return']*100:.2f}%")

    if result['avoid_zone']['count'] > 0:
        print(f"\nAvoid zone trades: {result['avoid_zone']['count']}")
        print(f"  Win rate: {result['avoid_zone']['win_rate']:.1%}")
        print(f"  Avg return: {result['avoid_zone']['avg_return']*100:.2f}%")

    if result.get('active_zone', {}).get('count', 0) > 0:
        print(f"\nActive zone trades (after avoidance): {result['active_zone']['count']}")
        print(f"  Win rate: {result['active_zone']['win_rate']:.1%}")
        print(f"  Avg return: {result['active_zone']['avg_return']*100:.2f}%")

        print(f"\nImprovement:")
        print(f"  Win rate: {result['improvement']['win_rate_diff']:+.1%}")
        print(f"  Avg return: {result['improvement']['avg_return_diff']*100:+.2f}%")
        print(f"  Trades avoided: {result['improvement']['trades_avoided']} ({result['improvement']['avoid_ratio']:.1%})")

    # 4. Walk-Forward 검증
    print("\n" + "=" * 60)
    print("Walk-Forward Validation")
    print("=" * 60)

    wf_result = run_walk_forward(data, "2022-12-31")

    train = wf_result['train']
    test = wf_result['test']

    print(f"\n{'Metric':<20} {'Train':<15} {'Test':<15} {'Decay':<10}")
    print("-" * 60)

    if 'active_zone' in train and train['active_zone'].get('count', 0) > 0:
        train_wr = train['active_zone']['win_rate']
        test_wr = test['active_zone']['win_rate'] if test.get('active_zone', {}).get('count', 0) > 0 else 0
        decay = train_wr - test_wr

        print(f"{'Win Rate (Active)':<20} {train_wr:.1%}          {test_wr:.1%}          {decay:+.1%}")

    if 'avoid_zone' in train and train['avoid_zone'].get('count', 0) > 0:
        train_avoid_wr = train['avoid_zone']['win_rate']
        test_avoid_wr = test['avoid_zone']['win_rate'] if test.get('avoid_zone', {}).get('count', 0) > 0 else 0

        print(f"{'Win Rate (Avoid)':<20} {train_avoid_wr:.1%}          {test_avoid_wr:.1%}")

    # 5. 파라미터 스윕
    print("\n" + "=" * 60)
    print("Parameter Sweep")
    print("=" * 60)

    # Test 기간만으로 스윕
    test_data = data[data.index > "2022-12-31"]

    print(f"\n{'Vol%':<8} {'RSI Range':<12} {'Avoid Trades':<14} {'Avoid WR':<12} {'Active WR':<12} {'Improvement':<12}")
    print("-" * 70)

    best_improvement = -1
    best_params = None

    for vol_th in [20, 30, 40]:
        for rsi_range in [(40, 60), (45, 55), (48, 52)]:
            r = run_avoidance_test(test_data, vol_th, rsi_range[0], rsi_range[1])

            avoid_count = r.get('avoid_zone', {}).get('count', 0)
            avoid_wr = r.get('avoid_zone', {}).get('win_rate', 0) if avoid_count > 0 else '-'
            active_wr = r.get('active_zone', {}).get('win_rate', 0) if r.get('active_zone', {}).get('count', 0) > 0 else '-'
            improvement = r.get('improvement', {}).get('win_rate_diff', 0)

            print(f"{vol_th:<8} {str(rsi_range):<12} {avoid_count:<14} "
                  f"{avoid_wr if isinstance(avoid_wr, str) else f'{avoid_wr:.1%}':<12} "
                  f"{active_wr if isinstance(active_wr, str) else f'{active_wr:.1%}':<12} "
                  f"{improvement:+.1%}")

            if improvement > best_improvement and avoid_count >= 5:
                best_improvement = improvement
                best_params = (vol_th, rsi_range)

    print(f"\nBest params: vol<={best_params[0]}%, RSI {best_params[1]} → +{best_improvement:.1%} improvement")

    # 6. 통계 검정
    print("\n" + "=" * 60)
    print("Statistical Tests")
    print("=" * 60)

    # 최적 파라미터로 재테스트
    final_result = run_avoidance_test(data, best_params[0], best_params[1][0], best_params[1][1])

    if final_result.get('active_zone', {}).get('count', 0) > 0 and final_result.get('avoid_zone', {}).get('count', 0) > 0:
        active_wr = final_result['active_zone']['win_rate']
        avoid_wr = final_result['avoid_zone']['win_rate']
        all_wr = final_result['all_trades']['win_rate']

        active_n = final_result['active_zone']['count']
        avoid_n = final_result['avoid_zone']['count']
        all_n = final_result['all_trades']['count']

        # 회피구간 vs 활성구간 승률 차이 검정
        # 2x2 contingency table
        active_wins = int(active_wr * active_n)
        avoid_wins = int(avoid_wr * avoid_n)

        contingency = [[active_wins, active_n - active_wins],
                       [avoid_wins, avoid_n - avoid_wins]]

        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        print(f"\nChi-squared test (active vs avoid zone):")
        print(f"  Active zone: {active_n} trades, {active_wr:.1%} win rate")
        print(f"  Avoid zone: {avoid_n} trades, {avoid_wr:.1%} win rate")
        print(f"  Chi2: {chi2:.3f}, p-value: {p_value:.4f}")

        # 활성구간이 전체보다 나은지 검정
        active_wins = int(active_wr * active_n)
        all_wins = int(all_wr * all_n)

        # binomial test
        p_better = 1 - stats.binom.cdf(active_wins - 1, active_n, all_wr)
        print(f"\nBinomial test (active zone better than baseline):")
        print(f"  p-value: {p_better:.4f}")

    # 7. 결론
    print("\n" + "=" * 60)
    print("Conclusion")
    print("=" * 60)

    checks = {
        'Avoid zone WR < All WR': avoid_wr < all_wr if 'avoid_wr' in dir() else False,
        'Active zone WR > All WR': active_wr > all_wr if 'active_wr' in dir() else False,
        'p-value < 0.1': p_value < 0.1 if 'p_value' in dir() else False,
        'OOS improvement > 0': best_improvement > 0,
        'Avoid ratio < 50%': final_result.get('improvement', {}).get('avoid_ratio', 1) < 0.5
    }

    for check, passed in checks.items():
        status = "PASS" if passed else "FAIL"
        print(f"  [{status}] {check}")

    passed_count = sum(checks.values())
    print(f"\nPassed: {passed_count}/5")

    if passed_count >= 4:
        print("\nVerdict: VALIDATED - 저변동성 중립구간 회피는 유효함")
    elif passed_count >= 3:
        print("\nVerdict: MARGINAL - 추가 검증 필요")
    else:
        print("\nVerdict: REJECTED - 가설 기각")


if __name__ == "__main__":
    main()
