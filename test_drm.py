#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# Test DynamicRiskManager fixes
try:
    from ai_trading_signals import DynamicRiskManager

    # Create instance with default params to avoid Unicode output
    class TestDRM(DynamicRiskManager):
        def __init__(self):
            self.max_leverage = 10
            self.max_margin_usage = 0.5
            self.min_position_size = 100.0
            self.daily_loss_limit = 0.05
            self.max_correlation_exposure = 0.3

            # Portfolio tracking
            self.active_positions = {}
            self.daily_pnl = 0.0
            self.consecutive_losses = 0
            self.win_rate_history = []

            # Kelly formula parameters
            self.kelly_lookback = 20
            self.kelly_fraction = 0.25

            print("DynamicRiskManager test instance created")

    # Test the method
    drm = TestDRM()
    print("Testing calculate_position_size method...")

    result = drm.calculate_position_size(
        entry_price=50000,
        stop_loss_price=49000,
        account_balance=10000,
        ai_confidence=0.8
    )

    print(f"Success: {result.get('success', False)}")
    if result.get('success'):
        print(f"Position size: {result.get('position_size', 0)}")
        print(f"Leverage: {result.get('leverage', 0)}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")

except Exception as e:
    print(f"Test failed: {str(e)}")
    import traceback
    traceback.print_exc()