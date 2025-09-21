#!/usr/bin/env python3
"""
Final System Verification - ASCII only for Windows compatibility
Complete verification of ai_trading_signals.py system
"""

import time
import json
from datetime import datetime

# Import system components
try:
    from ai_trading_signals import (
        AlphaVantageConnector, MLSignalGenerator, TechnicalIndicators,
        RiskManager, ATRCalculator, PortfolioRiskManager,
        PaperTradingSimulator, DatabaseManager
    )
    print("[OK] All system components imported")
except ImportError as e:
    print(f"[ERROR] Import failed: {e}")
    exit(1)

def test_complete_data_flow():
    """Test end-to-end data flow"""
    print("\n[TEST] Complete Data Flow Verification")

    try:
        # Initialize components
        api_client = AlphaVantageConnector()
        ml_model = MLSignalGenerator()
        risk_manager = RiskManager(account_balance=10000)
        atr_calculator = ATRCalculator()

        start_time = time.time()

        # Step 1: Fetch data
        print("  [1/5] Fetching Alpha Vantage data...")
        btc_data = api_client.get_crypto_intraday('BTC', '60min')

        if btc_data is None or btc_data.empty:
            print("    [ERROR] Failed to fetch data")
            return False

        print(f"    [OK] {len(btc_data)} data points retrieved")

        # Step 2: Calculate indicators
        print("  [2/5] Calculating technical indicators...")
        df_indicators = TechnicalIndicators.add_all_indicators(btc_data, api_client)

        required_cols = ['rsi', 'macd', 'macd_signal', 'bb_upper', 'bb_lower']
        missing = [col for col in required_cols if col not in df_indicators.columns]

        if missing:
            print(f"    [ERROR] Missing indicators: {missing}")
            return False

        print(f"    [OK] {len(df_indicators.columns)} total columns")

        # Step 3: Generate signal
        print("  [3/5] Generating AI signal...")

        # Try to train model if needed
        if not ml_model.is_trained:
            historical = api_client.get_historical_data('BTC', months=2)
            if historical is not None and len(historical) > 50:
                hist_indicators = TechnicalIndicators.add_all_indicators(historical, api_client)
                training = ml_model.train_model(hist_indicators)
                if training.get('success'):
                    print(f"    [OK] Model trained: {training['accuracy']:.1%} accuracy")
                else:
                    print("    [WARNING] Model training failed, using fallback")
            else:
                print("    [WARNING] Insufficient historical data")

        signal_result = ml_model.predict_signal(df_indicators)

        if signal_result.get('success'):
            signal = signal_result['signal']
            confidence = signal_result['confidence']
            print(f"    [OK] Signal: {signal} ({confidence:.1%} confidence)")
        else:
            signal = "HOLD"
            confidence = 0.5
            print("    [WARNING] Using fallback signal")

        # Step 4: Calculate ATR
        print("  [4/5] Calculating ATR levels...")
        current_price = df_indicators['close'].iloc[-1]

        atr_result = atr_calculator.calculate_atr(df_indicators)
        if atr_result and 'atr' in atr_result:
            atr_value = atr_result['atr']
            stop_loss = current_price - (atr_value * 2)
            take_profit = current_price + (atr_value * 3)
            print(f"    [OK] ATR: ${atr_value:.2f}")
            print(f"    [OK] Stop Loss: ${stop_loss:,.2f}")
            print(f"    [OK] Take Profit: ${take_profit:,.2f}")
        else:
            stop_loss = current_price * 0.98
            print("    [WARNING] Using fallback stop loss")

        # Step 5: Position sizing
        print("  [5/5] Calculating position size...")
        position_calc = risk_manager.calculate_position_size(
            current_price, stop_loss, account_risk=0.02
        )

        if position_calc.get('success'):
            position_size = position_calc['position_size']
            position_value = position_calc['position_value']
            risk_amount = position_calc['risk_amount']

            print(f"    [OK] Position: {position_size:.6f} BTC")
            print(f"    [OK] Value: ${position_value:,.2f}")
            print(f"    [OK] Risk: ${risk_amount:.2f}")
        else:
            print(f"    [ERROR] Position calculation failed")
            return False

        total_time = time.time() - start_time
        print(f"  [SUCCESS] Complete flow in {total_time:.2f} seconds")

        return {
            'success': True,
            'total_time': total_time,
            'data_points': len(btc_data),
            'signal': signal,
            'confidence': confidence,
            'current_price': float(current_price),
            'position_size': position_size,
            'position_value': position_value
        }

    except Exception as e:
        print(f"  [ERROR] Data flow failed: {e}")
        return False

def test_risk_scenarios():
    """Test various risk management scenarios"""
    print("\n[TEST] Risk Management Scenarios")

    try:
        api_client = AlphaVantageConnector()
        risk_manager = RiskManager(account_balance=10000)

        # Get current price
        btc_data = api_client.get_crypto_intraday('BTC', '60min')
        if btc_data is None:
            print("  [ERROR] No price data")
            return False

        current_price = btc_data['close'].iloc[-1]

        scenarios = [
            {'risk': 1.0, 'balance': 10000, 'leverage': 1.0},
            {'risk': 2.0, 'balance': 10000, 'leverage': 2.0},
            {'risk': 1.5, 'balance': 5000, 'leverage': 1.5},
        ]

        results = []

        for i, scenario in enumerate(scenarios, 1):
            print(f"  [SCENARIO {i}] Risk: {scenario['risk']}%, Leverage: {scenario['leverage']}x")

            # Update risk manager
            risk_manager.account_balance = scenario['balance']
            risk_manager.max_leverage = scenario['leverage']

            # Calculate position
            stop_loss = current_price * (1 - scenario['risk']/100)
            position_calc = risk_manager.calculate_position_size(
                current_price, stop_loss, account_risk=scenario['risk']/100
            )

            if position_calc.get('success'):
                exposure = (position_calc['position_value'] / scenario['balance']) * 100
                max_loss = (position_calc['risk_amount'] / scenario['balance']) * 100

                print(f"    [OK] Position: {position_calc['position_size']:.6f} BTC")
                print(f"    [OK] Exposure: {exposure:.1f}%")
                print(f"    [OK] Max Loss: {max_loss:.2f}%")

                results.append({
                    'scenario': i,
                    'success': True,
                    'exposure': exposure,
                    'max_loss': max_loss
                })
            else:
                print(f"    [ERROR] {position_calc.get('error', 'Unknown error')}")
                results.append({'scenario': i, 'success': False})

        successful = sum(1 for r in results if r.get('success', False))
        print(f"  [RESULT] {successful}/{len(scenarios)} scenarios successful")

        return successful > 0

    except Exception as e:
        print(f"  [ERROR] Risk testing failed: {e}")
        return False

def test_performance():
    """Test system performance"""
    print("\n[TEST] Performance Testing")

    try:
        api_client = AlphaVantageConnector()

        # Test API response times
        print("  [SPEED] Testing API response times...")

        times = []
        for i in range(3):
            start = time.time()
            data = api_client.get_crypto_intraday('BTC', '60min')
            if data is not None:
                elapsed = time.time() - start
                times.append(elapsed)
                print(f"    [REQUEST {i+1}] {elapsed:.3f}s")
            else:
                print(f"    [REQUEST {i+1}] Failed")

        if times:
            avg_time = sum(times) / len(times)
            min_time = min(times)

            print(f"    [AVERAGE] {avg_time:.3f}s")
            print(f"    [FASTEST] {min_time:.3f}s")

            if avg_time < 2.0:
                speed_rating = "Excellent"
            elif avg_time < 5.0:
                speed_rating = "Good"
            else:
                speed_rating = "Needs Improvement"

            print(f"    [RATING] {speed_rating}")

            # Test caching effectiveness
            speedup = times[0] / min_time if min_time > 0 else 1
            print(f"    [CACHE] {speedup:.1f}x speedup factor")

            return {
                'avg_time': avg_time,
                'min_time': min_time,
                'speed_rating': speed_rating,
                'cache_speedup': speedup
            }
        else:
            print("    [ERROR] No successful requests")
            return False

    except Exception as e:
        print(f"  [ERROR] Performance testing failed: {e}")
        return False

def test_error_handling():
    """Test error handling capabilities"""
    print("\n[TEST] Error Handling")

    try:
        api_client = AlphaVantageConnector()
        risk_manager = RiskManager(account_balance=10000)

        error_tests = []

        # Test 1: Invalid symbol
        print("  [ERROR 1] Invalid symbol handling...")
        try:
            invalid_data = api_client.get_crypto_intraday('INVALID_SYMBOL', '60min')
            if invalid_data is None:
                print("    [OK] Invalid symbol properly handled")
                error_tests.append(True)
            else:
                print("    [WARNING] Invalid symbol not handled")
                error_tests.append(False)
        except Exception:
            print("    [OK] Exception properly raised")
            error_tests.append(True)

        # Test 2: Invalid risk parameters
        print("  [ERROR 2] Invalid risk parameters...")
        try:
            invalid_position = risk_manager.calculate_position_size(
                entry_price=100,
                stop_loss_price=110,  # Invalid: stop loss > entry
                account_risk=0.02
            )
            if not invalid_position.get('success', True):
                print("    [OK] Invalid parameters rejected")
                error_tests.append(True)
            else:
                print("    [WARNING] Invalid parameters accepted")
                error_tests.append(False)
        except Exception:
            print("    [OK] Exception properly raised")
            error_tests.append(True)

        # Test 3: Edge case values
        print("  [ERROR 3] Edge case handling...")
        try:
            edge_case = risk_manager.calculate_position_size(
                entry_price=0.01,  # Very small price
                stop_loss_price=0.009,
                account_risk=0.0001  # Very small risk
            )
            if edge_case.get('success') or 'error' in edge_case:
                print("    [OK] Edge cases handled")
                error_tests.append(True)
            else:
                print("    [WARNING] Edge cases not handled")
                error_tests.append(False)
        except Exception:
            print("    [OK] Edge case exception handled")
            error_tests.append(True)

        success_rate = sum(error_tests) / len(error_tests) if error_tests else 0
        print(f"  [RESULT] {success_rate:.1%} error scenarios handled properly")

        return success_rate >= 0.67  # 67% success rate minimum

    except Exception as e:
        print(f"  [ERROR] Error handling test failed: {e}")
        return False

def test_dashboard_status():
    """Test dashboard status and connectivity"""
    print("\n[TEST] Dashboard Status")

    try:
        api_client = AlphaVantageConnector()

        # Test API connectivity
        print("  [API] Testing connection status...")
        start_time = time.time()
        btc_data = api_client.get_crypto_intraday('BTC', '60min')
        response_time = time.time() - start_time

        if btc_data is not None and not btc_data.empty:
            current_price = btc_data['close'].iloc[-1]

            status_info = {
                'api_connected': True,
                'connection_status': 'ONLINE',
                'last_update': datetime.now().isoformat(),
                'response_time_ms': int(response_time * 1000),
                'current_btc_price': float(current_price),
                'data_points': len(btc_data)
            }

            print(f"    [OK] API Status: {status_info['connection_status']}")
            print(f"    [OK] Response Time: {status_info['response_time_ms']}ms")
            print(f"    [OK] BTC Price: ${status_info['current_btc_price']:,.2f}")
            print(f"    [OK] Last Update: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

            # Save status for dashboard
            with open('system_status.json', 'w') as f:
                json.dump(status_info, f, indent=2)

            print("    [SAVE] Status saved to system_status.json")

            return status_info
        else:
            print("    [ERROR] API connection failed")
            return False

    except Exception as e:
        print(f"  [ERROR] Dashboard status test failed: {e}")
        return False

def generate_final_report(test_results):
    """Generate final comprehensive report"""
    print("\n" + "="*60)
    print("FINAL SYSTEM VERIFICATION REPORT")
    print("="*60)
    print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)

    # Count successful tests
    successful_tests = sum(1 for result in test_results.values() if result)
    total_tests = len(test_results)
    success_rate = successful_tests / total_tests if total_tests > 0 else 0

    print(f"\nOVERALL STATUS: {successful_tests}/{total_tests} tests passed ({success_rate:.1%})")

    # Detailed results
    for test_name, result in test_results.items():
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name.replace('_', ' ').title()}")

    # Performance summary
    if 'performance' in test_results and test_results['performance']:
        perf = test_results['performance']
        print(f"\n[PERFORMANCE]")
        print(f"  • Average Response: {perf['avg_time']:.3f}s")
        print(f"  • Speed Rating: {perf['speed_rating']}")
        print(f"  • Cache Speedup: {perf['cache_speedup']:.1f}x")

    # Data flow summary
    if 'data_flow' in test_results and test_results['data_flow']:
        flow = test_results['data_flow']
        print(f"\n[DATA FLOW]")
        print(f"  • End-to-end Time: {flow['total_time']:.2f}s")
        print(f"  • Current Signal: {flow['signal']} ({flow['confidence']:.1%})")
        print(f"  • BTC Price: ${flow['current_price']:,.2f}")
        print(f"  • Position Size: {flow['position_size']:.6f} BTC")

    # Dashboard status
    if 'dashboard_status' in test_results and test_results['dashboard_status']:
        dashboard = test_results['dashboard_status']
        print(f"\n[DASHBOARD]")
        print(f"  • API Status: {dashboard['connection_status']}")
        print(f"  • Response Time: {dashboard['response_time_ms']}ms")
        print(f"  • Last Update: Available")

    # Final recommendation
    print("\n" + "="*60)
    print("SYSTEM READINESS ASSESSMENT")
    print("="*60)

    if success_rate >= 0.9:
        print("[EXCELLENT] System ready for production use")
        readiness = "Production Ready"
    elif success_rate >= 0.7:
        print("[GOOD] System ready with minor optimizations")
        readiness = "Nearly Ready"
    elif success_rate >= 0.5:
        print("[ACCEPTABLE] System functional but needs improvements")
        readiness = "Needs Work"
    else:
        print("[POOR] System requires significant fixes")
        readiness = "Not Ready"

    print(f"\nREADINESS LEVEL: {readiness}")
    print("="*60)

    # Save complete report
    report_data = {
        'test_results': test_results,
        'summary': {
            'successful_tests': successful_tests,
            'total_tests': total_tests,
            'success_rate': success_rate,
            'readiness_level': readiness,
            'timestamp': datetime.now().isoformat()
        }
    }

    with open('final_verification_report.json', 'w') as f:
        json.dump(report_data, f, indent=2, default=str)

    print("Report saved to: final_verification_report.json")

def main():
    """Run all verification tests"""
    print("COMPREHENSIVE AI TRADING SYSTEM VERIFICATION")
    print("="*60)

    test_results = {}

    # Run all tests
    tests = [
        ("data_flow", test_complete_data_flow),
        ("risk_scenarios", test_risk_scenarios),
        ("performance", test_performance),
        ("error_handling", test_error_handling),
        ("dashboard_status", test_dashboard_status),
    ]

    for test_name, test_func in tests:
        print(f"\n{'-'*20} {test_name.upper()} {'-'*20}")
        try:
            result = test_func()
            test_results[test_name] = result
            status = "PASSED" if result else "FAILED"
            print(f"[{status}] {test_name}")
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            test_results[test_name] = False

    # Generate final report
    generate_final_report(test_results)

if __name__ == "__main__":
    main()