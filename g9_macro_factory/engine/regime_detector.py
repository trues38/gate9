class RegimeDetector:
    """
    Detects the current Market Regime based on Macro Indicators.
    Regimes:
    1. Inflation Regime (High CPI, High Yields) -> Bond/Tech Bearish
    2. Growth Regime (Low CPI, Stable Yields, Rising Stocks) -> Bullish
    3. Liquidity Crisis (High VIX, Spiking DXY) -> Cash is King
    4. Neutral (No strong signal)
    """
    
    def __init__(self):
        # Default Thresholds (Can be tuned)
        self.CPI_HIGH_THRESHOLD = 3.0
        self.US10Y_HIGH_THRESHOLD = 3.5
        self.VIX_PANIC_THRESHOLD = 25.0
        self.DXY_STRONG_THRESHOLD = 105.0
        
    def detect(self, macro: dict) -> str:
        """
        G9 Regime Detector v1.5 (Pragmatic Pro)
        Required Data: CPI, US10Y, VIX, DXY, WTI, SPY_Trend
        """
        # Normalize keys (handle lowercase/uppercase)
        macro = {k.upper(): v for k, v in macro.items()}
        
        # Helper to extract value
        def get_val(key, default=0.0):
            val = macro.get(key, default)
            if isinstance(val, dict):
                return val.get('value', default)
            return val
            
        # Default values if missing
        vix = get_val('VIX', 0.0)
        dxy = get_val('DXY', 0.0)
        spy_trend = get_val('SPY_TREND', 'NEUTRAL') # UP, DOWN, CRASH, NEUTRAL
        cpi = get_val('CPI', 0.0)
        us10y = get_val('US10Y', 0.0)
        wti = get_val('WTI', 0.0)
        
        # [v1.7] Infer SPY_TREND if missing (Proxy)
        if spy_trend == 'NEUTRAL':
            if vix < 18.0:
                spy_trend = 'UP' # Low Volatility -> Bull Market
            elif vix > 30.0:
                spy_trend = 'CRASH' # Panic -> Crash
            elif vix > 25.0:
                spy_trend = 'DOWN' # High Vol -> Correction
        
        # Global+ Stress Proxies (Definitions only for now)
        macro['KR_Stress'] = (get_val('KR_WON', 0.0) > 1350)
        macro['JP_Stress'] = (get_val('JPY', 0.0) > 150)
        macro['CN_Stress'] = (get_val('CN_PMI', 50.0) < 50)

        # 1. Liquidity Crisis (System Risk)
        if vix > 30 and (dxy > 106 or spy_trend == 'CRASH'):
            return "LIQUIDITY_CRISIS"

        # 2. Stagflation (High Inflation, Low Growth)
        if cpi > 3.2 and spy_trend == 'DOWN':
            return "STAGFLATION"

        # 3. Inflation Fear (Tightening/Inflation Fear)
        if cpi > 3.0 and (us10y > 4.0 or wti > 85):
            return "INFLATION_FEAR"

        # 4. Growth / Goldilocks (Healthy Bull Market)
        if vix < 20 and us10y < 4.0 and spy_trend == 'UP':
            return "GROWTH_GOLDILOCKS"

        # 5. Neutral
        return "NEUTRAL"

    def get_regime_context(self, regime: str) -> str:
        """Returns a description string for the LLM context."""
        if regime == "Liquidity Crisis":
            return "MARKET PANIC (High VIX). Cash is King. Avoid leverage."
        elif regime == "Inflation Regime":
            return "HIGH INFLATION. Rates are high. Tech/Growth stocks under pressure."
        elif regime == "Growth Regime":
            return "STABLE GROWTH. Favorable for equities. Risk-on."
        else:
            return "NEUTRAL MARKET. Follow specific signals."
