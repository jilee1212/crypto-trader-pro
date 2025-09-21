#!/usr/bin/env python3
"""
CoinGecko Dashboard Launcher
Launch the enhanced CoinGecko-based trading system
"""

import subprocess
import sys
import os
from datetime import datetime

def check_requirements():
    """Check if all required components are available"""
    print("🔍 Checking CoinGecko system requirements...")

    required_files = [
        'ai_trading_signals_coingecko.py',
        'coingecko_ml_components.py',
        'ai_trading_signals_coingecko_complete.py'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)

    if missing_files:
        print(f"❌ Missing required files: {missing_files}")
        return False

    print("✅ All CoinGecko components found")

    # Check Python packages
    try:
        import streamlit
        import pandas
        import numpy
        import requests
        import sklearn
        import plotly
        print("✅ All required Python packages available")
    except ImportError as e:
        print(f"❌ Missing Python package: {e}")
        return False

    # Check optional pandas_ta
    try:
        import pandas_ta
        print("✅ pandas_ta available (enhanced indicators)")
    except ImportError:
        print("⚠️ pandas_ta not available (install with: pip install pandas_ta)")

    return True

def launch_dashboard():
    """Launch the CoinGecko dashboard"""
    print("\n🚀 Launching CoinGecko Trading Dashboard...")

    try:
        # Launch Streamlit app
        cmd = [
            sys.executable, "-m", "streamlit", "run",
            "ai_trading_signals_coingecko_complete.py",
            "--server.port=8503",  # Use different port from Alpha Vantage
            "--server.headless=false"
        ]

        print(f"Command: {' '.join(cmd)}")
        print("📊 Dashboard starting...")
        print("🌐 Access at: http://localhost:8503")
        print("\n" + "="*50)
        print("COINGECKO TRADING DASHBOARD")
        print("="*50)
        print("Features:")
        print("• 10,000 API requests/month (20x more than Alpha Vantage)")
        print("• 7+ cryptocurrencies supported")
        print("• Enhanced technical indicators with pandas_ta")
        print("• Real-time market sentiment (Fear & Greed Index)")
        print("• No API key required")
        print("• Faster response times")
        print("="*50)
        print("Press Ctrl+C to stop the dashboard")

        # Execute the command
        subprocess.run(cmd)

    except KeyboardInterrupt:
        print("\n\n👋 CoinGecko dashboard stopped by user")
    except Exception as e:
        print(f"\n❌ Error launching dashboard: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure Streamlit is installed: pip install streamlit")
        print("2. Check all CoinGecko files are present")
        print("3. Verify Python packages are installed")

def show_migration_info():
    """Show migration information"""
    print("📋 MIGRATION INFORMATION")
    print("-" * 30)
    print("• Alpha Vantage version: DEPRECATED")
    print("• CoinGecko version: ACTIVE")
    print("• Migration date: 2025-09-21")
    print("• Performance improvement: 20x better")
    print("• New features: Market sentiment, more coins")
    print("• Setup: No API key required")

def main():
    """Main launcher function"""
    print("🚀 CoinGecko Trading System Launcher")
    print("=" * 40)
    print(f"Launch time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Show migration info
    show_migration_info()
    print()

    # Check requirements
    if not check_requirements():
        print("\n❌ Requirements check failed. Please fix issues and try again.")
        return

    # Launch dashboard
    try:
        launch_dashboard()
    except Exception as e:
        print(f"\n❌ Launch failed: {e}")

if __name__ == "__main__":
    main()