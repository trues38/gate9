def refine_pattern(pattern_id, macro):
    """
    Refines generic patterns into specific sub-patterns based on macro context.
    """
    # Normalize macro keys
    macro = {k.upper(): v for k, v in macro.items()}
    
    # P-001: Yield Spike
    if pattern_id == 'P-001':
        us10y_change = macro.get('US10Y', {}).get('change_1w', '0%').strip('%')
        try:
            us10y_val = float(us10y_change)
        except:
            us10y_val = 0.0
            
        # We don't have SPY change in macro yet, assume bad if US10Y spikes fast
        if us10y_val > 5.0: # +5% change
            return "P-001A" # Bad Yield Spike
        else:
            return "P-001B" # Good/Normal Yield Spike
            
    # P-005: Inflation Shock
    if pattern_id == 'P-005':
        cpi_change = macro.get('CPI', {}).get('change_1w', '0%').strip('%')
        try:
            cpi_val = float(cpi_change)
        except:
            cpi_val = 0.0
            
        if cpi_val > 0:
            return "P-005A" # Bad CPI (Rising)
        else:
            return "P-005B" # Good CPI (Falling/Peak)

    # P-008: War / Geopolitical
    if pattern_id == 'P-008':
        vix_val = macro.get('VIX', {}).get('value', 20.0)
        
        if vix_val > 35.0:
            return "P-008B" # War Confirmed (Panic Peak -> Buy Dip)
        else:
            return "P-008A" # War Rumor (Uncertainty -> Sell)

    return pattern_id
