"""
BTC Relative Engine v1.0

ETF 시대, BTC 생태계 내 상대 우위 판단 엔진

비교 대상: BTC, ETH, SOL, MSTR
스코어 = ETF Flow Sensitivity + Lag Advantage - Overheat

매일 출력:
- 1등: LONG
- 3-4등: NO TRADE or SHORT 후보
"""

import yfinance as yf
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class AssetScore:
    ticker: str
    name: str
    price: float
    ret_5d: float
    etf_sensitivity: float
    lag_advantage: float
    overheat: float
    total_score: float
    rank: int
    signal: str


class BTCRelativeEngine:
    """BTC Relative Strength Engine"""

    ASSETS = {
        'BTC-USD': 'BTC',
        'ETH-USD': 'ETH',
        'SOL-USD': 'SOL',
        'MSTR': 'MSTR',
    }

    def __init__(
        self,
        etf_weight: float = 0.4,
        lag_weight: float = 0.4,
        overheat_weight: float = 0.2,
        rsi_period: int = 14,
        lookback_days: int = 60,
    ):
        self.etf_weight = etf_weight
        self.lag_weight = lag_weight
        self.overheat_weight = overheat_weight
        self.rsi_period = rsi_period
        self.lookback_days = lookback_days

    def fetch_data(self) -> Dict[str, pd.DataFrame]:
        """Fetch price data for all assets"""
        end_date = datetime.now()
        start_date = end_date - timedelta(days=self.lookback_days + 30)

        data = {}

        # Fetch IBIT for ETF flow reference
        ibit = yf.download('IBIT', start=start_date, end=end_date, progress=False)
        if isinstance(ibit.columns, pd.MultiIndex):
            ibit.columns = ibit.columns.get_level_values(0)
        data['IBIT'] = ibit

        # Fetch other assets
        for ticker in self.ASSETS.keys():
            df = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            data[ticker] = df

        return data

    def calculate_rsi(self, prices: pd.Series, period: int = 14) -> float:
        """Calculate current RSI"""
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi.iloc[-1] if len(rsi) > 0 else 50

    def calculate_etf_sensitivity(
        self, asset_prices: pd.Series, ibit_volume: pd.Series
    ) -> float:
        """
        ETF Flow Sensitivity: 자산이 IBIT 볼륨에 얼마나 반응하는지
        높을수록 ETF 자금 유입에 민감 → 긍정적
        """
        # Align dates
        common_idx = asset_prices.index.intersection(ibit_volume.index)
        if len(common_idx) < 20:
            return 0.0

        asset_ret = asset_prices.reindex(common_idx).pct_change(5)
        vol_ma = ibit_volume.reindex(common_idx).rolling(10).mean()
        vol_ratio = ibit_volume.reindex(common_idx) / vol_ma

        # Correlation between high ETF volume and asset returns
        df = pd.DataFrame({'ret': asset_ret, 'vol': vol_ratio}).dropna()
        if len(df) < 10:
            return 0.0

        # When ETF vol is high (>1.2x), what's the avg return?
        high_vol = df[df['vol'] > 1.2]
        if len(high_vol) < 3:
            return 0.0

        sensitivity = high_vol['ret'].mean() * 100  # Normalize to %
        return np.clip(sensitivity, -10, 10)

    def calculate_lag_advantage(
        self, asset_prices: pd.Series, btc_prices: pd.Series
    ) -> float:
        """
        Lag Advantage: 최근 5일 BTC 대비 상대 강도
        양수면 BTC보다 강함 → 모멘텀 있음
        """
        common_idx = asset_prices.index.intersection(btc_prices.index)
        if len(common_idx) < 10:
            return 0.0

        asset = asset_prices.reindex(common_idx)
        btc = btc_prices.reindex(common_idx)

        asset_ret_5d = (asset.iloc[-1] - asset.iloc[-6]) / asset.iloc[-6]
        btc_ret_5d = (btc.iloc[-1] - btc.iloc[-6]) / btc.iloc[-6]

        # Relative strength vs BTC
        lag_adv = (asset_ret_5d - btc_ret_5d) * 100
        return np.clip(lag_adv, -20, 20)

    def calculate_overheat(self, prices: pd.Series) -> float:
        """
        Overheat: RSI 기반 과열 정도
        높을수록 과열 → 부정적 (감점)
        """
        rsi = self.calculate_rsi(prices, self.rsi_period)

        # Normalize: RSI 50 = neutral (0), RSI 70+ = high overheat, RSI 30- = oversold (negative overheat)
        overheat = (rsi - 50) / 5  # -4 to +4 range roughly
        return np.clip(overheat, -5, 5)

    def calculate_scores(self) -> List[AssetScore]:
        """Calculate scores for all assets"""
        data = self.fetch_data()

        if 'IBIT' not in data or len(data['IBIT']) == 0:
            raise ValueError("IBIT data not available")

        ibit_volume = data['IBIT']['Volume']
        btc_prices = data['BTC-USD']['Close']

        scores = []

        for ticker, name in self.ASSETS.items():
            if ticker not in data or len(data[ticker]) == 0:
                continue

            prices = data[ticker]['Close']
            current_price = prices.iloc[-1]
            ret_5d = (prices.iloc[-1] - prices.iloc[-6]) / prices.iloc[-6] if len(prices) > 6 else 0

            # Calculate components
            etf_sens = self.calculate_etf_sensitivity(prices, ibit_volume)
            lag_adv = self.calculate_lag_advantage(prices, btc_prices)
            overheat = self.calculate_overheat(prices)

            # Total score
            total = (
                self.etf_weight * etf_sens +
                self.lag_weight * lag_adv -
                self.overheat_weight * overheat
            )

            scores.append(AssetScore(
                ticker=ticker,
                name=name,
                price=current_price,
                ret_5d=ret_5d,
                etf_sensitivity=etf_sens,
                lag_advantage=lag_adv,
                overheat=overheat,
                total_score=total,
                rank=0,
                signal='',
            ))

        # Rank by total score (descending)
        scores.sort(key=lambda x: -x.total_score)

        for i, s in enumerate(scores):
            s.rank = i + 1
            if s.rank == 1:
                s.signal = 'LONG'
            elif s.rank == 2:
                s.signal = 'HOLD'
            elif s.rank == 3:
                s.signal = 'AVOID'
            else:
                s.signal = 'SHORT_BIAS'

        return scores

    def get_command(self) -> str:
        """Generate daily command output"""
        scores = self.calculate_scores()
        today = datetime.now().strftime('%Y-%m-%d')

        # Find top and bottom
        long_asset = scores[0]
        avoid_assets = [s for s in scores if s.signal in ['AVOID', 'SHORT_BIAS']]

        lines = [
            "=" * 50,
            f"[BTC RELATIVE COMMAND] {today}",
            "=" * 50,
            "",
            f"1️⃣  LONG: {long_asset.name}",
        ]

        if len(avoid_assets) > 0:
            lines.append(f"2️⃣  AVOID: {avoid_assets[0].name}")
        if len(avoid_assets) > 1:
            lines.append(f"3️⃣  SHORT BIAS: {avoid_assets[1].name}")

        lines.extend([
            "",
            "REASON:",
            f"  • ETF Sensitivity: {long_asset.name} = {long_asset.etf_sensitivity:+.2f}",
            f"  • Relative Strength: {long_asset.lag_advantage:+.2f}% vs BTC",
            f"  • RSI Overheat: {long_asset.overheat:+.1f}",
            "",
            "SCORES:",
        ])

        for s in scores:
            lines.append(
                f"  {s.rank}. {s.name:<6} Score={s.total_score:+.2f} "
                f"(ETF={s.etf_sensitivity:+.1f}, Lag={s.lag_advantage:+.1f}, Heat={s.overheat:+.1f})"
            )

        lines.extend([
            "",
            "=" * 50,
        ])

        return "\n".join(lines)

    def print_detailed_report(self):
        """Print detailed analysis report"""
        scores = self.calculate_scores()
        today = datetime.now().strftime('%Y-%m-%d')

        print("=" * 70)
        print(f"BTC RELATIVE ENGINE v1.0 - {today}")
        print("=" * 70)

        print("\n[SCORE BREAKDOWN]")
        print(f"{'Rank':<6} {'Asset':<8} {'Price':<12} {'5d Ret':<10} {'ETF Sens':<10} {'Lag Adv':<10} {'Heat':<8} {'TOTAL':<10} {'Signal'}")
        print("-" * 90)

        for s in scores:
            print(
                f"{s.rank:<6} {s.name:<8} ${s.price:,.0f}    {s.ret_5d*100:+.1f}%     "
                f"{s.etf_sensitivity:+.2f}      {s.lag_advantage:+.2f}      {s.overheat:+.1f}     "
                f"{s.total_score:+.2f}      {s.signal}"
            )

        print("\n" + "=" * 70)
        print("[COMMAND OUTPUT]")
        print("=" * 70)
        print(self.get_command())


def main():
    engine = BTCRelativeEngine()
    engine.print_detailed_report()


if __name__ == "__main__":
    main()
