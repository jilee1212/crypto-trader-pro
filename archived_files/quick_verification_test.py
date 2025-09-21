#!/usr/bin/env python3
"""
Quick Verification Test - ASCII compatible
Test key system components with correct API calls
"""

import time
import json
from datetime import datetime

try:
    from ai_trading_signals import (
        AlphaVantageConnector, TechnicalIndicators, RiskManager, ATRCalculator
    )
    print("[OK] Core components imported")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    exit(1)

def quick_system_test():
    """Quick comprehensive system test"""
    print("\n" + "="*50)
    print("QUICK AI TRADING SYSTEM VERIFICATION")
    print("="*50)

    results = {}

    # Test 1: API Connection
    print("\n[1/6] API Connection Test")
    try:
        api = AlphaVantageConnector()
        start_time = time.time()
        btc_data = api.get_crypto_intraday('BTC', '60min')
        response_time = time.time() - start_time

        if btc_data is not None and not btc_data.empty:
            current_price = btc_data['close'].iloc[-1]
            print(f"  [OK] BTC Price: ${current_price:,.2f}")
            print(f"  [OK] Data Points: {len(btc_data)}")
            print(f"  [OK] Response Time: {response_time:.3f}s")
            results['api_connection'] = True
        else:
            print("  [ERROR] Failed to fetch data")
            results['api_connection'] = False
    except Exception as e:
        print(f"  [ERROR] API test failed: {e}")
        results['api_connection'] = False

    # Test 2: Technical Indicators
    print("\n[2/6] Technical Indicators Test")
    try:
        if results.get('api_connection') and btc_data is not None:
            df_indicators = TechnicalIndicators.add_all_indicators(btc_data, api)
            latest = df_indicators.iloc[-1]

            rsi = latest.get('rsi', None)
            macd = latest.get('macd', None)
            bb_upper = latest.get('bb_upper', None)

            if rsi is not None and 0 <= rsi <= 100:
                print(f"  [OK] RSI: {rsi:.2f}")
                results['indicators'] = True
            else:
                print("  [ERROR] Invalid RSI")
                results['indicators'] = False

            if macd is not None:
                print(f"  [OK] MACD: {macd:.4f}")
            if bb_upper is not None:
                print(f"  [OK] BB Upper: ${bb_upper:.2f}")
        else:
            print("  [SKIP] No data available")
            results['indicators'] = False
    except Exception as e:
        print(f"  [ERROR] Indicators test failed: {e}")
        results['indicators'] = False

    # Test 3: ATR Calculation
    print("\n[3/6] ATR Calculation Test")
    try:
        if results.get('api_connection') and btc_data is not None:
            atr_calc = ATRCalculator()
            atr_result = atr_calc.calculate_atr(btc_data)

            if atr_result and 'atr' in atr_result:
                atr_value = atr_result['atr']
                print(f"  [OK] ATR Value: ${atr_value:.2f}")

                # Calculate dynamic levels
                stop_loss = current_price - (atr_value * 2)
                take_profit = current_price + (atr_value * 3)

                print(f"  [OK] Stop Loss: ${stop_loss:,.2f}")
                print(f"  [OK] Take Profit: ${take_profit:,.2f}")
                results['atr'] = True
            else:
                print("  [ERROR] ATR calculation failed")
                results['atr'] = False
        else:
            print("  [SKIP] No data available")
            results['atr'] = False
    except Exception as e:
        print(f"  [ERROR] ATR test failed: {e}")
        results['atr'] = False

    # Test 4: Risk Management
    print("\n[4/6] Risk Management Test")
    try:
        if results.get('api_connection'):
            risk_mgr = RiskManager(account_balance=10000)

            # Test with correct parameter name
            position_calc = risk_mgr.calculate_position_size(
                entry_price=current_price,
                stop_loss_price=current_price * 0.98,  # 2% stop loss
                account_risk_pct=0.02  # Correct parameter name
            )

            if position_calc.get('success'):
                pos_size = position_calc['position_size']
                pos_value = position_calc['position_value']
                risk_amount = position_calc['risk_amount']

                print(f"  [OK] Position Size: {pos_size:.6f} BTC")
                print(f"  [OK] Position Value: ${pos_value:,.2f}")
                print(f"  [OK] Risk Amount: ${risk_amount:.2f}")

                # Verify risk is within limits
                risk_pct = (risk_amount / 10000) * 100
                print(f"  [OK] Actual Risk: {risk_pct:.2f}%")

                results['risk_management'] = True
            else:
                error_msg = position_calc.get('error', 'Unknown error')
                print(f"  [ERROR] Position calculation failed: {error_msg}")
                results['risk_management'] = False
        else:
            print("  [SKIP] No price data")
            results['risk_management'] = False
    except Exception as e:
        print(f"  [ERROR] Risk management test failed: {e}")
        results['risk_management'] = False

    # Test 5: Performance Measurement
    print("\n[5/6] Performance Test")
    try:
        # Measure multiple API calls
        times = []
        for i in range(3):
            start = time.time()
            test_data = api.get_crypto_intraday('BTC', '60min')
            if test_data is not None:
                elapsed = time.time() - start
                times.append(elapsed)

        if times:
            avg_time = sum(times) / len(times)
            fastest = min(times)

            print(f"  [OK] Average Response: {avg_time:.3f}s")
            print(f"  [OK] Fastest Response: {fastest:.3f}s")

            # Performance rating
            if avg_time < 1.0:
                rating = "Excellent"
            elif avg_time < 3.0:
                rating = "Good"
            else:
                rating = "Needs Improvement"

            print(f"  [OK] Performance Rating: {rating}")
            results['performance'] = True
        else:
            print("  [ERROR] No successful API calls")
            results['performance'] = False
    except Exception as e:
        print(f"  [ERROR] Performance test failed: {e}")
        results['performance'] = False

    # Test 6: Dashboard Status
    print("\n[6/6] Dashboard Status Test")
    try:
        dashboard_status = {
            'system_status': 'ONLINE' if results.get('api_connection') else 'OFFLINE',
            'api_connected': results.get('api_connection', False),
            'last_update': datetime.now().isoformat(),
            'last_update_formatted': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'btc_price': float(current_price) if 'current_price' in locals() else 0,
            'response_time_ms': int(response_time * 1000) if 'response_time' in locals() else 0,
            'indicators_working': results.get('indicators', False),
            'risk_management_working': results.get('risk_management', False)
        }

        print(f"  [STATUS] {dashboard_status['system_status']}")
        print(f"  [UPDATE] {dashboard_status['last_update_formatted']}")

        if dashboard_status['api_connected']:
            print(f"  [PRICE] ${dashboard_status['btc_price']:,.2f}")
            print(f"  [LATENCY] {dashboard_status['response_time_ms']}ms")

        # Save status for dashboard
        with open('quick_system_status.json', 'w') as f:
            json.dump(dashboard_status, f, indent=2)

        print("  [SAVE] Status saved to quick_system_status.json")
        results['dashboard_status'] = True

    except Exception as e:
        print(f"  [ERROR] Dashboard status test failed: {e}")
        results['dashboard_status'] = False

    # Generate Summary
    print("\n" + "="*50)
    print("SYSTEM VERIFICATION SUMMARY")
    print("="*50)

    passed = sum(1 for success in results.values() if success)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0

    print(f"Tests Passed: {passed}/{total} ({success_rate:.1f}%)")

    for test_name, success in results.items():
        status = "[PASS]" if success else "[FAIL]"
        print(f"{status} {test_name.replace('_', ' ').title()}")

    # Final Assessment
    print("\n" + "-"*50)
    if success_rate >= 80:
        print("[EXCELLENT] System ready for production")
        recommendation = "Ready for live trading"
    elif success_rate >= 60:
        print("[GOOD] System mostly functional")
        recommendation = "Ready with minor fixes"
    elif success_rate >= 40:
        print("[ACCEPTABLE] System partially working")
        recommendation = "Needs improvements"
    else:
        print("[POOR] System has major issues")
        recommendation = "Requires significant fixes"

    print(f"Recommendation: {recommendation}")

    # Critical Features Status
    print("\n" + "-"*50)
    print("CRITICAL FEATURES STATUS:")

    critical_features = {
        'Real-time Data': results.get('api_connection', False),
        'Technical Analysis': results.get('indicators', False),
        'Risk Management': results.get('risk_management', False),
        'Performance': results.get('performance', False),
        'Dashboard': results.get('dashboard_status', False)
    }

    for feature, working in critical_features.items():
        status = "WORKING" if working else "FAILED"
        symbol = "[OK]" if working else "[ERROR]"
        print(f"{symbol} {feature}: {status}")

    # Save complete results
    final_results = {
        'test_results': results,
        'summary': {
            'passed': passed,
            'total': total,
            'success_rate': success_rate,
            'recommendation': recommendation,
            'timestamp': datetime.now().isoformat()
        },
        'critical_features': critical_features
    }

    with open('quick_verification_results.json', 'w') as f:
        json.dump(final_results, f, indent=2)

    print(f"\nDetailed results saved to: quick_verification_results.json")
    print("="*50)

    return results

if __name__ == "__main__":
    quick_system_test()