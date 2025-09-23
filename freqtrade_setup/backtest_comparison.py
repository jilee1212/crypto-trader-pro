#!/usr/bin/env python3
"""
Backtest Comparison Tool
Compares RSIStrategy vs AITradingStrategy performance using Freqtrade backtesting
"""

import sys
import os
import subprocess
import json
import pandas as pd
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

class BacktestComparator:
    """Compares different strategies using Freqtrade backtesting"""

    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.results_dir = "user_data/backtest_results"
        self.comparison_dir = "user_data/comparison_results"
        os.makedirs(self.comparison_dir, exist_ok=True)

        # Strategy configurations
        self.strategies = {
            'RSIStrategy': {
                'name': 'RSIStrategy',
                'description': 'Conservative RSI-based strategy',
                'file': 'user_data/strategies/RSIStrategy.py'
            },
            'AITradingStrategy': {
                'name': 'AITradingStrategy',
                'description': 'AI-powered RandomForest + GradientBoosting strategy',
                'file': 'user_data/strategies/AITradingStrategy.py'
            }
        }

    def run_backtest(self, strategy_name, timerange, additional_args=None):
        """Run Freqtrade backtest for a specific strategy"""
        try:
            print(f"[INFO] Running backtest for {strategy_name}...")

            # Build command
            cmd = [
                'docker-compose', 'exec', '-T', 'freqtrade',
                'freqtrade', 'backtesting',
                '--config', '/freqtrade/config/config.json',
                '--strategy', strategy_name,
                '--timerange', timerange,
                '--export', 'trades',
                '--export-filename', f'user_data/backtest_results/{strategy_name}_{timerange}'
            ]

            if additional_args:
                cmd.extend(additional_args)

            # Execute command
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print(f"[INFO] Backtest completed for {strategy_name}")
                return self.parse_backtest_output(result.stdout, strategy_name)
            else:
                print(f"[ERROR] Backtest failed for {strategy_name}:")
                print(result.stderr)
                return None

        except Exception as e:
            print(f"[ERROR] Failed to run backtest for {strategy_name}: {e}")
            return None

    def parse_backtest_output(self, output, strategy_name):
        """Parse backtest output and extract key metrics"""
        try:
            lines = output.split('\n')
            metrics = {'strategy': strategy_name}

            # Look for key metrics in output
            for line in lines:
                line = line.strip()

                if 'Total trade count' in line or 'Total trades' in line:
                    metrics['total_trades'] = self.extract_number(line)
                elif 'Starting balance' in line:
                    metrics['starting_balance'] = self.extract_number(line)
                elif 'Final balance' in line or 'Ending balance' in line:
                    metrics['final_balance'] = self.extract_number(line)
                elif 'Absolute profit' in line or 'Total profit' in line:
                    metrics['absolute_profit'] = self.extract_number(line)
                elif 'Total profit %' in line or 'Total return %' in line:
                    metrics['total_return_pct'] = self.extract_number(line)
                elif 'Avg. profit %' in line or 'Avg profit' in line:
                    metrics['avg_profit_pct'] = self.extract_number(line)
                elif 'Best Pair' in line:
                    metrics['best_pair'] = line.split(':')[1].strip() if ':' in line else ''
                elif 'Worst Pair' in line:
                    metrics['worst_pair'] = line.split(':')[1].strip() if ':' in line else ''
                elif 'Win/Draw/Loss' in line:
                    wdl = line.split(':')[1].strip() if ':' in line else ''
                    metrics['win_draw_loss'] = wdl
                elif 'Winrate' in line or 'Win rate' in line:
                    metrics['winrate'] = self.extract_number(line)
                elif 'Sharpe' in line:
                    metrics['sharpe_ratio'] = self.extract_number(line)
                elif 'Max Drawdown' in line or 'Maximum drawdown' in line:
                    metrics['max_drawdown'] = self.extract_number(line)
                elif 'Calmar' in line:
                    metrics['calmar_ratio'] = self.extract_number(line)

            return metrics

        except Exception as e:
            print(f"[ERROR] Failed to parse backtest output: {e}")
            return {'strategy': strategy_name, 'error': str(e)}

    def extract_number(self, text):
        """Extract numeric value from text"""
        try:
            import re
            # Look for numbers (including decimals and percentages)
            numbers = re.findall(r'-?\d+\.?\d*', text.replace(',', ''))
            return float(numbers[-1]) if numbers else 0.0
        except:
            return 0.0

    def download_data(self, days=60):
        """Download required data for backtesting"""
        try:
            print(f"[INFO] Downloading {days} days of data...")

            cmd = [
                'docker-compose', 'exec', '-T', 'freqtrade',
                'freqtrade', 'download-data',
                '--config', '/freqtrade/config/config.json',
                '--days', str(days),
                '--timeframes', '5m', '1h', '1d'
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print("[INFO] Data download completed")
                return True
            else:
                print(f"[ERROR] Data download failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to download data: {e}")
            return False

    def train_ai_models_if_needed(self):
        """Train AI models if they don't exist"""
        try:
            models_dir = "user_data/models"
            signal_model_path = os.path.join(models_dir, "signal_model.pkl")

            if not os.path.exists(signal_model_path):
                print("[INFO] AI models not found. Training models...")

                # Run training script
                result = subprocess.run([
                    'python', 'train_ai_models.py',
                    '--symbol', 'BTC/USDT',
                    '--days', '90'
                ], capture_output=True, text=True, cwd='.')

                if result.returncode == 0:
                    print("[INFO] AI model training completed")
                    return True
                else:
                    print(f"[ERROR] AI model training failed: {result.stderr}")
                    return False
            else:
                print("[INFO] AI models already exist")
                return True

        except Exception as e:
            print(f"[ERROR] Failed to train AI models: {e}")
            return False

    def run_comparison(self, timerange, days=60):
        """Run complete strategy comparison"""
        print("📊 Strategy Backtest Comparison")
        print("=" * 50)

        # 1. Download data
        if not self.download_data(days):
            print("[ERROR] Failed to download data")
            return False

        # 2. Train AI models if needed
        if not self.train_ai_models_if_needed():
            print("[ERROR] Failed to prepare AI models")
            return False

        # 3. Run backtests for each strategy
        results = {}
        for strategy_name in self.strategies.keys():
            result = self.run_backtest(strategy_name, timerange)
            if result:
                results[strategy_name] = result
            else:
                print(f"[WARN] Skipping {strategy_name} due to backtest failure")

        if not results:
            print("[ERROR] No successful backtests")
            return False

        # 4. Compare results
        self.compare_results(results, timerange)

        # 5. Save comparison
        self.save_comparison(results, timerange)

        return True

    def compare_results(self, results, timerange):
        """Compare and display backtest results"""
        print(f"\n📈 BACKTEST RESULTS ({timerange})")
        print("=" * 80)

        # Create comparison table
        df_comparison = pd.DataFrame.from_dict(results, orient='index')

        # Display key metrics
        key_metrics = [
            'total_trades', 'total_return_pct', 'avg_profit_pct',
            'winrate', 'max_drawdown', 'sharpe_ratio'
        ]

        print("\n🎯 Key Performance Metrics:")
        print("-" * 80)
        print(f"{'Strategy':<20} {'Trades':<8} {'Return%':<10} {'Avg%':<8} {'Winrate':<8} {'Drawdown%':<12} {'Sharpe':<8}")
        print("-" * 80)

        for strategy_name, metrics in results.items():
            trades = metrics.get('total_trades', 0)
            ret_pct = metrics.get('total_return_pct', 0)
            avg_pct = metrics.get('avg_profit_pct', 0)
            winrate = metrics.get('winrate', 0)
            drawdown = metrics.get('max_drawdown', 0)
            sharpe = metrics.get('sharpe_ratio', 0)

            print(f"{strategy_name:<20} {trades:<8.0f} {ret_pct:<10.2f} {avg_pct:<8.2f} {winrate:<8.1f} {drawdown:<12.2f} {sharpe:<8.2f}")

        # Performance ranking
        print("\n🏆 Performance Ranking:")
        print("-" * 40)

        # Rank by total return
        if len(results) > 1:
            sorted_by_return = sorted(results.items(), key=lambda x: x[1].get('total_return_pct', 0), reverse=True)

            for i, (strategy, metrics) in enumerate(sorted_by_return, 1):
                return_pct = metrics.get('total_return_pct', 0)
                winrate = metrics.get('winrate', 0)
                print(f"{i}. {strategy}: {return_pct:.2f}% return, {winrate:.1f}% winrate")

        # Risk analysis
        print("\n⚠️  Risk Analysis:")
        print("-" * 40)

        for strategy_name, metrics in results.items():
            drawdown = metrics.get('max_drawdown', 0)
            sharpe = metrics.get('sharpe_ratio', 0)

            risk_level = "LOW"
            if drawdown > 20 or sharpe < 0.5:
                risk_level = "HIGH"
            elif drawdown > 10 or sharpe < 1.0:
                risk_level = "MEDIUM"

            print(f"{strategy_name}: {risk_level} risk (DD: {drawdown:.1f}%, Sharpe: {sharpe:.2f})")

        # AI vs Traditional comparison
        if 'RSIStrategy' in results and 'AITradingStrategy' in results:
            print("\n🤖 AI vs Traditional Strategy:")
            print("-" * 40)

            rsi_return = results['RSIStrategy'].get('total_return_pct', 0)
            ai_return = results['AITradingStrategy'].get('total_return_pct', 0)

            improvement = ai_return - rsi_return
            improvement_pct = (improvement / abs(rsi_return)) * 100 if rsi_return != 0 else 0

            if improvement > 0:
                print(f"✅ AI Strategy outperformed by {improvement:.2f}% ({improvement_pct:.1f}% improvement)")
            else:
                print(f"❌ Traditional Strategy outperformed by {abs(improvement):.2f}% ({abs(improvement_pct):.1f}% better)")

            # Trade efficiency
            rsi_trades = results['RSIStrategy'].get('total_trades', 0)
            ai_trades = results['AITradingStrategy'].get('total_trades', 0)

            if ai_trades > 0 and rsi_trades > 0:
                rsi_efficiency = rsi_return / rsi_trades
                ai_efficiency = ai_return / ai_trades
                print(f"Trade Efficiency - RSI: {rsi_efficiency:.3f}% per trade, AI: {ai_efficiency:.3f}% per trade")

    def save_comparison(self, results, timerange):
        """Save comparison results to files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed results
            results_file = os.path.join(self.comparison_dir, f"backtest_comparison_{timerange}_{timestamp}.json")
            with open(results_file, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            # Save summary CSV
            df = pd.DataFrame.from_dict(results, orient='index')
            csv_file = os.path.join(self.comparison_dir, f"backtest_summary_{timerange}_{timestamp}.csv")
            df.to_csv(csv_file)

            print(f"\n[INFO] Results saved to {self.comparison_dir}")
            print(f"  - Detailed: {results_file}")
            print(f"  - Summary: {csv_file}")

        except Exception as e:
            print(f"[ERROR] Failed to save comparison: {e}")

def main():
    """Main comparison script"""
    import argparse

    parser = argparse.ArgumentParser(description='Compare strategy backtesting performance')
    parser.add_argument('--timerange', default='20241201-20241222', help='Timerange for backtesting (YYYYMMDD-YYYYMMDD)')
    parser.add_argument('--days', type=int, default=60, help='Days of data to download')

    args = parser.parse_args()

    # Initialize comparator
    comparator = BacktestComparator()

    # Run comparison
    success = comparator.run_comparison(args.timerange, args.days)

    if success:
        print("\n🎉 Strategy comparison completed successfully!")
        print("Check user_data/comparison_results/ for detailed results.")
    else:
        print("\n❌ Strategy comparison failed. Check the logs above.")
        sys.exit(1)

if __name__ == "__main__":
    main()