#!/usr/bin/env python3
"""
Debug the exact button click scenario that's failing
"""

import sys
import traceback

def simulate_button_click():
    """Simulate exactly what happens when the Fetch Live Data button is clicked"""
    print("=== Simulating Fetch Live Data Button Click ===")

    try:
        # Import all required modules
        from ai_trading_signals_coingecko import CoinGeckoConnector, EnhancedTechnicalIndicators
        print("[OK] Imports successful")

        # Initialize connector (simulating session state)
        cg_connector = CoinGeckoConnector()
        print("[OK] CoinGecko connector initialized")

        # Set test parameters (simulating sidebar selections)
        selected_symbol = 'bitcoin'
        selected_timeframe = '1day'
        print(f"[OK] Parameters: {selected_symbol}, {selected_timeframe}")

        # Step 1: Get current price
        print("Step 1: Getting current price...")
        current_price_data = cg_connector.get_current_price(selected_symbol)
        print(f"[DEBUG] Current price data type: {type(current_price_data)}")
        print(f"[DEBUG] Current price data: {current_price_data}")

        # Step 2: Get historical OHLCV data
        print("Step 2: Getting enhanced market data...")
        df = cg_connector.get_enhanced_market_data(selected_symbol, selected_timeframe)
        print(f"[DEBUG] DataFrame type: {type(df)}")
        print(f"[DEBUG] DataFrame is None: {df is None}")
        if df is not None:
            print(f"[DEBUG] DataFrame empty: {df.empty}")
            print(f"[DEBUG] DataFrame shape: {df.shape}")

        # Step 3: Check the critical condition from the dashboard
        print("Step 3: Checking critical condition...")
        condition_result = df is not None and not df.empty
        print(f"[DEBUG] Condition 'df is not None and not df.empty': {condition_result}")

        if condition_result:
            print("[OK] Condition passed - proceeding to add indicators...")

            # Step 4: Add enhanced technical indicators
            df_with_indicators = EnhancedTechnicalIndicators.add_all_indicators(df, cg_connector)
            print(f"[DEBUG] Indicators added: {df_with_indicators is not None}")

            if df_with_indicators is not None:
                print(f"[OK] Indicators DataFrame shape: {df_with_indicators.shape}")

                # Step 5: Display current price info (simulate dashboard display)
                if current_price_data:
                    price = current_price_data['usd']
                    change_24h = current_price_data.get('usd_24h_change', 0)
                    print(f"[OK] Price display ready: ${price:,.2f} ({change_24h:+.2f}%)")

                    # Check for RSI in indicators
                    if 'rsi' in df_with_indicators.columns:
                        rsi = df_with_indicators['rsi'].iloc[-1]
                        print(f"[OK] RSI ready: {rsi:.1f}")
                    else:
                        print("[WARNING] RSI column not found")

                    print("[SUCCESS] All dashboard display components ready!")
                    print("This should show 'CoinGecko data loaded successfully!' message")
                    return True
                else:
                    print("[ERROR] Current price data is None or invalid")
                    return False
            else:
                print("[ERROR] Failed to add technical indicators")
                return False
        else:
            print("[ERROR] Critical condition failed - this triggers 'Failed to fetch data from CoinGecko'")
            return False

    except Exception as e:
        print(f"[ERROR] Exception during button click simulation: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = simulate_button_click()
    if success:
        print("\n✅ Button click simulation: SUCCESS")
        print("The dashboard should work correctly.")
    else:
        print("\n❌ Button click simulation: FAILED")
        print("This explains why you're seeing the error message.")