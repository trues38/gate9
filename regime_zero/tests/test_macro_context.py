from regime_zero.engine.macro_context import MacroContextLoader

def test_macro_context():
    loader = MacroContextLoader()
    
    # Test 1: Recent Date (RSS)
    print("\n--- Test 1: Recent Date (2025-12-02) ---")
    print(loader.get_macro_context("2025-12-02"))
    
    # Test 2: Historical Date (Archive)
    # Pick a date likely to be in the scraped data (e.g., today or yesterday for OIL/GOLD, 2024 for FED)
    print("\n--- Test 2: Historical Date (2025-12-01) ---")
    print(loader.get_macro_context("2025-12-01"))

if __name__ == "__main__":
    test_macro_context()
