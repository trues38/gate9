"""
BTC Pattern Backtester - 패턴 검증 및 최적화

핵심 철학:
- 과적합 방지: Train/Test 분리, Walk-forward 검증
- 현실적 시뮬레이션: 슬리피지, 수수료 반영
- 패턴 발견: 높은 승률 조합 자동 탐색
"""
import urllib.request
import json
import math
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import defaultdict

from btc_engine.patterns.graph_db import (
    PatternGraphDB, MarketState, Pattern
)


@dataclass
class OHLCV:
    """캔들 데이터"""
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float


@dataclass
class Trade:
    """백테스트 거래"""
    entry_date: datetime
    entry_price: float
    exit_date: Optional[datetime] = None
    exit_price: Optional[float] = None
    exit_reason: Optional[str] = None
    pnl: float = 0
    pnl_pct: float = 0
    pattern_id: Optional[str] = None
    state_key: Optional[str] = None
    tp_price: float = 0
    sl_price: float = 0


@dataclass
class BacktestResult:
    """백테스트 결과"""
    # 기본 통계
    total_trades: int = 0
    wins: int = 0
    losses: int = 0
    win_rate: float = 0

    # 수익
    total_return: float = 0
    avg_return: float = 0
    best_trade: float = 0
    worst_trade: float = 0

    # 리스크
    max_drawdown: float = 0
    sharpe_ratio: float = 0
    profit_factor: float = 0

    # 기간
    start_date: str = ""
    end_date: str = ""

    # 상세
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[str, float]] = field(default_factory=list)

    # 패턴별 성과
    pattern_stats: Dict[str, dict] = field(default_factory=dict)


class DataFetcher:
    """과거 데이터 수집"""

    @staticmethod
    def get_json(url: str, timeout: int = 15) -> dict:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return json.loads(r.read().decode())

    def fetch_daily_candles(self, symbol: str = "BTCUSDT",
                           days: int = 1000) -> List[OHLCV]:
        """일봉 데이터 수집 (최대 1000일)"""
        url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval=1d&limit={min(days, 1000)}"
        data = self.get_json(url)

        candles = []
        for c in data:
            candles.append(OHLCV(
                timestamp=datetime.fromtimestamp(c[0] / 1000),
                open=float(c[1]),
                high=float(c[2]),
                low=float(c[3]),
                close=float(c[4]),
                volume=float(c[5])
            ))
        return candles

    def fetch_fear_greed_history(self, days: int = 1000) -> Dict[str, int]:
        """Fear & Greed 히스토리"""
        try:
            url = f"https://api.alternative.me/fng/?limit={min(days, 1000)}"
            data = self.get_json(url)

            fng_by_date = {}
            for item in data.get('data', []):
                date = datetime.fromtimestamp(int(item['timestamp'])).strftime('%Y-%m-%d')
                fng_by_date[date] = int(item['value'])
            return fng_by_date
        except Exception as e:
            print(f"FNG fetch failed: {e}")
            return {}


class StateGenerator:
    """각 날짜별 MarketState 생성"""

    def __init__(self, db: PatternGraphDB):
        self.db = db

    def calculate_rsi(self, closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0

        gains, losses = [], []
        for i in range(1, len(closes)):
            change = closes[i] - closes[i-1]
            gains.append(max(0, change))
            losses.append(max(0, -change))

        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period if sum(losses[-period:]) > 0 else 0.0001
        rs = avg_gain / avg_loss
        return 100 - (100 / (1 + rs))

    def calculate_bb_position(self, closes: List[float], period: int = 20) -> float:
        if len(closes) < period:
            return 50.0

        window = closes[-period:]
        sma = sum(window) / period
        variance = sum((x - sma) ** 2 for x in window) / period
        std = math.sqrt(variance)

        if std == 0:
            return 50.0

        bb_upper = sma + 2 * std
        bb_lower = sma - 2 * std
        current = closes[-1]

        return max(0, min(100, (current - bb_lower) / (bb_upper - bb_lower) * 100))

    def calculate_atr_pct(self, candles: List[OHLCV], period: int = 14) -> float:
        if len(candles) < period:
            return 3.0

        tr_list = []
        for i in range(1, min(period + 1, len(candles))):
            c = candles[-i]
            prev_close = candles[-i-1].close if i < len(candles) else c.close
            tr = max(c.high - c.low, abs(c.high - prev_close), abs(c.low - prev_close))
            tr_list.append(tr)

        atr = sum(tr_list) / len(tr_list)
        return atr / candles[-1].close * 100

    def count_consecutive(self, candles: List[OHLCV], direction: str) -> int:
        count = 0
        for i in range(len(candles) - 1, 0, -1):
            c = candles[i]
            if direction == "down" and c.close < c.open:
                count += 1
            elif direction == "up" and c.close > c.open:
                count += 1
            else:
                break
        return count

    def generate_state(self, candles: List[OHLCV], fng: int = 50,
                      funding_rate: float = 0.01) -> MarketState:
        """캔들 데이터에서 MarketState 생성"""
        closes = [c.close for c in candles]

        rsi = self.calculate_rsi(closes)
        bb_pos = self.calculate_bb_position(closes)
        atr_pct = self.calculate_atr_pct(candles)
        consec_down = self.count_consecutive(candles, "down")
        consec_up = self.count_consecutive(candles, "up")

        return MarketState(
            rsi_zone=self.db.discretize_rsi(rsi),
            fng_zone=self.db.discretize_fng(fng),
            bb_zone=self.db.discretize_bb(bb_pos),
            trend_zone=self.db.discretize_trend(consec_down, consec_up),
            funding_zone=self.db.discretize_funding(funding_rate),
            volatility_zone=self.db.discretize_volatility(atr_pct)
        )


class Backtester:
    """패턴 백테스터"""

    def __init__(self, db: PatternGraphDB = None,
                 commission: float = 0.001,  # 0.1% 수수료
                 slippage: float = 0.001):   # 0.1% 슬리피지
        self.db = db or PatternGraphDB()
        self.commission = commission
        self.slippage = slippage
        self.fetcher = DataFetcher()
        self.state_gen = StateGenerator(self.db)

    def run_backtest(self,
                    candles: List[OHLCV],
                    fng_history: Dict[str, int],
                    patterns: List[Pattern] = None,
                    initial_capital: float = 10000,
                    position_size_pct: float = 50,
                    max_hold_days: int = 14) -> BacktestResult:
        """
        백테스트 실행

        Args:
            candles: 일봉 데이터
            fng_history: 날짜별 Fear & Greed
            patterns: 테스트할 패턴들 (None이면 DB에서 로드)
            initial_capital: 초기 자본
            position_size_pct: 포지션 크기 (%)
            max_hold_days: 최대 보유 기간
        """
        if patterns is None:
            patterns = self.db.get_active_patterns()

        result = BacktestResult()
        result.start_date = candles[0].timestamp.strftime('%Y-%m-%d')
        result.end_date = candles[-1].timestamp.strftime('%Y-%m-%d')

        capital = initial_capital
        peak_capital = initial_capital
        max_drawdown = 0

        trades: List[Trade] = []
        current_trade: Optional[Trade] = None
        pattern_trades: Dict[str, List[Trade]] = defaultdict(list)

        # 충분한 히스토리가 필요 (RSI 14일 + BB 20일)
        lookback = 30

        for i in range(lookback, len(candles)):
            current_candle = candles[i]
            current_date = current_candle.timestamp
            date_str = current_date.strftime('%Y-%m-%d')

            # FNG 조회 (없으면 50)
            fng = fng_history.get(date_str, 50)

            # 현재 상태 생성
            historical_candles = candles[max(0, i-lookback):i+1]
            state = self.state_gen.generate_state(historical_candles, fng)
            state_key = state.to_key()

            # 포지션이 있으면 청산 조건 체크
            if current_trade:
                days_held = (current_date - current_trade.entry_date).days

                # TP 체크
                if current_candle.high >= current_trade.tp_price:
                    current_trade.exit_date = current_date
                    current_trade.exit_price = current_trade.tp_price
                    current_trade.exit_reason = "TP"

                # SL 체크
                elif current_candle.low <= current_trade.sl_price:
                    current_trade.exit_date = current_date
                    current_trade.exit_price = current_trade.sl_price
                    current_trade.exit_reason = "SL"

                # 최대 보유 기간 체크
                elif days_held >= max_hold_days:
                    current_trade.exit_date = current_date
                    current_trade.exit_price = current_candle.close
                    current_trade.exit_reason = "TIMEOUT"

                # 청산 처리
                if current_trade.exit_date:
                    # 슬리피지/수수료 적용
                    exit_price = current_trade.exit_price * (1 - self.slippage)
                    exit_price *= (1 - self.commission)

                    pnl_pct = (exit_price - current_trade.entry_price) / current_trade.entry_price * 100
                    position_value = capital * (position_size_pct / 100)
                    pnl = position_value * (pnl_pct / 100)

                    current_trade.pnl = pnl
                    current_trade.pnl_pct = pnl_pct

                    capital += pnl
                    trades.append(current_trade)

                    if current_trade.pattern_id:
                        pattern_trades[current_trade.pattern_id].append(current_trade)

                    current_trade = None

            # 포지션이 없으면 진입 조건 체크
            if not current_trade:
                # 패턴 매칭
                for pattern in patterns:
                    matched = False
                    for entry_state in pattern.entry_states:
                        # 와일드카드 매칭
                        entry_parts = entry_state.split('|')
                        state_parts = state_key.split('|')

                        if len(entry_parts) != len(state_parts):
                            continue

                        match_count = 0
                        for ep, sp in zip(entry_parts, state_parts):
                            if ep == '*' or ep == sp:
                                match_count += 1

                        # 70% 이상 매칭
                        if match_count / len(entry_parts) >= 0.7:
                            matched = True
                            break

                    if matched and pattern.win_rate >= 0.55:  # 승률 55% 이상만 진입
                        # 슬리피지/수수료 적용
                        entry_price = current_candle.close * (1 + self.slippage)
                        entry_price *= (1 + self.commission)

                        current_trade = Trade(
                            entry_date=current_date,
                            entry_price=entry_price,
                            pattern_id=pattern.pattern_id,
                            state_key=state_key,
                            tp_price=entry_price * (1 + pattern.optimal_tp / 100),
                            sl_price=entry_price * (1 - pattern.optimal_sl / 100)
                        )
                        break  # 첫 번째 매칭 패턴으로 진입

            # Equity curve 기록
            unrealized_pnl = 0
            if current_trade:
                unrealized_pnl = (current_candle.close - current_trade.entry_price) / current_trade.entry_price * (capital * position_size_pct / 100)

            current_equity = capital + unrealized_pnl
            result.equity_curve.append((date_str, current_equity))

            # Drawdown 계산
            if current_equity > peak_capital:
                peak_capital = current_equity
            drawdown = (peak_capital - current_equity) / peak_capital * 100
            if drawdown > max_drawdown:
                max_drawdown = drawdown

        # 미청산 포지션 청산
        if current_trade:
            current_trade.exit_date = candles[-1].timestamp
            current_trade.exit_price = candles[-1].close
            current_trade.exit_reason = "END"
            pnl_pct = (current_trade.exit_price - current_trade.entry_price) / current_trade.entry_price * 100
            position_value = capital * (position_size_pct / 100)
            current_trade.pnl = position_value * (pnl_pct / 100)
            current_trade.pnl_pct = pnl_pct
            capital += current_trade.pnl
            trades.append(current_trade)

        # 결과 계산
        result.trades = trades
        result.total_trades = len(trades)

        if trades:
            result.wins = sum(1 for t in trades if t.pnl > 0)
            result.losses = sum(1 for t in trades if t.pnl <= 0)
            result.win_rate = result.wins / result.total_trades

            returns = [t.pnl_pct for t in trades]
            result.total_return = (capital - initial_capital) / initial_capital * 100
            result.avg_return = sum(returns) / len(returns)
            result.best_trade = max(returns)
            result.worst_trade = min(returns)

            # 샤프비율 (연환산, rf=0 가정)
            if len(returns) > 1:
                avg_ret = sum(returns) / len(returns)
                std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns))
                if std_ret > 0:
                    result.sharpe_ratio = (avg_ret / std_ret) * math.sqrt(252 / max(1, len(trades)))

            # Profit Factor
            gross_profit = sum(t.pnl for t in trades if t.pnl > 0)
            gross_loss = abs(sum(t.pnl for t in trades if t.pnl < 0))
            if gross_loss > 0:
                result.profit_factor = gross_profit / gross_loss

        result.max_drawdown = max_drawdown

        # 패턴별 통계
        for pattern_id, ptrades in pattern_trades.items():
            if ptrades:
                wins = sum(1 for t in ptrades if t.pnl > 0)
                returns = [t.pnl_pct for t in ptrades]
                result.pattern_stats[pattern_id] = {
                    'trades': len(ptrades),
                    'wins': wins,
                    'win_rate': wins / len(ptrades),
                    'avg_return': sum(returns) / len(returns),
                    'total_return': sum(returns)
                }

        return result

    def walk_forward_test(self,
                         candles: List[OHLCV],
                         fng_history: Dict[str, int],
                         train_days: int = 365,
                         test_days: int = 90,
                         min_confidence: float = 0.6) -> List[BacktestResult]:
        """
        Walk-forward 검증 (과적합 방지)

        train_days 동안 패턴 학습 → test_days 동안 검증 → 롤링
        """
        results = []
        total_days = len(candles)
        window_size = train_days + test_days

        i = 0
        while i + window_size <= total_days:
            train_candles = candles[i:i + train_days]
            test_candles = candles[i + train_days:i + window_size]

            # Train: 패턴 성능 분석
            train_result = self.run_backtest(train_candles, fng_history)

            # 좋은 패턴만 선택
            good_patterns = []
            for pattern in self.db.get_active_patterns():
                if pattern.pattern_id in train_result.pattern_stats:
                    stats = train_result.pattern_stats[pattern.pattern_id]
                    if stats['win_rate'] >= min_confidence and stats['trades'] >= 5:
                        good_patterns.append(pattern)

            # Test: 선택된 패턴으로 검증
            if good_patterns:
                test_result = self.run_backtest(test_candles, fng_history, good_patterns)
                test_result.pattern_stats['_selected_patterns'] = [p.pattern_id for p in good_patterns]
                results.append(test_result)

            i += test_days  # 롤링

        return results

    def discover_patterns(self,
                         candles: List[OHLCV],
                         fng_history: Dict[str, int],
                         min_samples: int = 10,
                         min_win_rate: float = 0.6) -> List[Dict]:
        """
        높은 승률 패턴 자동 발견
        """
        lookback = 30
        state_outcomes: Dict[str, List[Tuple[float, float, float]]] = defaultdict(list)

        for i in range(lookback, len(candles) - 7):
            current_candle = candles[i]
            date_str = current_candle.timestamp.strftime('%Y-%m-%d')
            fng = fng_history.get(date_str, 50)

            historical_candles = candles[max(0, i-lookback):i+1]
            state = self.state_gen.generate_state(historical_candles, fng)
            state_key = state.to_key()

            # 1일, 3일, 7일 후 수익률
            if i + 7 < len(candles):
                ret_1d = (candles[i+1].close - current_candle.close) / current_candle.close * 100
                ret_3d = (candles[i+3].close - current_candle.close) / current_candle.close * 100
                ret_7d = (candles[i+7].close - current_candle.close) / current_candle.close * 100
                state_outcomes[state_key].append((ret_1d, ret_3d, ret_7d))

        # 좋은 패턴 필터링
        discovered = []
        for state_key, outcomes in state_outcomes.items():
            if len(outcomes) < min_samples:
                continue

            # 3일 수익률 기준
            returns_3d = [o[1] for o in outcomes]
            wins = sum(1 for r in returns_3d if r > 0)
            win_rate = wins / len(outcomes)
            avg_return = sum(returns_3d) / len(returns_3d)

            if win_rate >= min_win_rate and avg_return > 0:
                discovered.append({
                    'state_key': state_key,
                    'samples': len(outcomes),
                    'win_rate': win_rate,
                    'avg_return_3d': avg_return,
                    'avg_return_1d': sum(o[0] for o in outcomes) / len(outcomes),
                    'avg_return_7d': sum(o[2] for o in outcomes) / len(outcomes),
                    'max_return': max(o[1] for o in outcomes),
                    'min_return': min(o[1] for o in outcomes)
                })

        # 승률 순 정렬
        discovered.sort(key=lambda x: (x['win_rate'], x['avg_return_3d']), reverse=True)
        return discovered


def run_full_backtest(days: int = 1000):
    """전체 백테스트 실행"""
    print("=" * 70)
    print("  BTC Pattern Backtester")
    print("=" * 70)

    # 1. 데이터 수집
    print("\n[1] 데이터 수집...")
    fetcher = DataFetcher()
    candles = fetcher.fetch_daily_candles(days=days)
    fng = fetcher.fetch_fear_greed_history(days=days)

    print(f"   캔들: {len(candles)}일 ({candles[0].timestamp.strftime('%Y-%m-%d')} ~ {candles[-1].timestamp.strftime('%Y-%m-%d')})")
    print(f"   FNG: {len(fng)}일")

    # 2. 패턴 DB 초기화
    print("\n[2] 패턴 DB 초기화...")
    from btc_engine.patterns.graph_db import initialize_pattern_db
    db = initialize_pattern_db()
    patterns = db.get_active_patterns()
    print(f"   활성 패턴: {len(patterns)}개")

    # 3. 백테스트 실행
    print("\n[3] 백테스트 실행...")
    backtester = Backtester(db)
    result = backtester.run_backtest(candles, fng)

    print(f"\n{'=' * 70}")
    print(f"  백테스트 결과 ({result.start_date} ~ {result.end_date})")
    print(f"{'=' * 70}")

    print(f"\n📊 기본 통계:")
    print(f"   총 거래: {result.total_trades}")
    print(f"   승/패: {result.wins}/{result.losses}")
    print(f"   승률: {result.win_rate*100:.1f}%")

    print(f"\n💰 수익:")
    print(f"   총 수익률: {result.total_return:+.2f}%")
    print(f"   평균 수익: {result.avg_return:+.2f}%")
    print(f"   최고 거래: {result.best_trade:+.2f}%")
    print(f"   최저 거래: {result.worst_trade:+.2f}%")

    print(f"\n⚠️ 리스크:")
    print(f"   최대 낙폭: {result.max_drawdown:.1f}%")
    print(f"   샤프비율: {result.sharpe_ratio:.2f}")
    print(f"   Profit Factor: {result.profit_factor:.2f}")

    if result.pattern_stats:
        print(f"\n📈 패턴별 성과:")
        for pattern_id, stats in result.pattern_stats.items():
            emoji = "🟢" if stats['win_rate'] >= 0.6 else "🔴" if stats['win_rate'] < 0.5 else "🟡"
            print(f"   {emoji} {pattern_id}:")
            print(f"      거래: {stats['trades']}, 승률: {stats['win_rate']*100:.0f}%, 평균: {stats['avg_return']:+.2f}%")

    # 4. 패턴 발견
    print(f"\n[4] 새로운 패턴 발견...")
    discovered = backtester.discover_patterns(candles, fng, min_samples=10, min_win_rate=0.6)

    if discovered:
        print(f"   발견된 패턴: {len(discovered)}개")
        print(f"\n   상위 5개:")
        for i, p in enumerate(discovered[:5]):
            print(f"   {i+1}. {p['state_key']}")
            print(f"      샘플: {p['samples']}, 승률: {p['win_rate']*100:.0f}%, 3일수익: {p['avg_return_3d']:+.2f}%")
    else:
        print("   새로운 패턴 없음")

    return result, discovered


if __name__ == "__main__":
    run_full_backtest()
