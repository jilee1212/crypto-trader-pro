#!/usr/bin/env python3
"""
Hyperparameter Optimization Runner for MultiIndicatorStrategy
Automated parameter tuning with performance tracking
"""

import sys
import os
import subprocess
import json
import pandas as pd
from datetime import datetime, timedelta
import argparse
import warnings
warnings.filterwarnings('ignore')


class HyperOptRunner:
    """Runs hyperparameter optimization for trading strategies"""

    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.results_dir = "user_data/hyperopt_results"
        os.makedirs(self.results_dir, exist_ok=True)

        # Default hyperopt settings
        self.default_settings = {
            'epochs': 300,
            'spaces': ['buy', 'sell', 'stoploss', 'roi'],
            'loss_function': 'SharpeHyperOptLoss',
            'timerange': '20241101-20241222',  # 2 months
            'timeframe': '5m',
            'strategy': 'MultiIndicatorStrategy',
            'hyperopt': 'MultiIndicatorHyperOpt'
        }

    def prepare_data(self, timerange, pairs=None):
        """Download required data for hyperopt"""
        try:
            print(f"[INFO] Downloading data for timerange: {timerange}")

            if pairs is None:
                pairs = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']

            # Calculate days from timerange
            start_date = datetime.strptime(timerange.split('-')[0], '%Y%m%d')
            end_date = datetime.strptime(timerange.split('-')[1], '%Y%m%d')
            days = (end_date - start_date).days + 10  # Extra buffer

            cmd = [
                'docker-compose', 'exec', '-T', 'freqtrade',
                'freqtrade', 'download-data',
                '--config', '/freqtrade/config/config.json',
                '--days', str(days),
                '--timeframes', '5m', '1h',
                '--pairs'] + pairs

            result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print("[INFO] Data download completed successfully")
                return True
            else:
                print(f"[ERROR] Data download failed: {result.stderr}")
                return False

        except Exception as e:
            print(f"[ERROR] Failed to download data: {e}")
            return False

    def run_hyperopt(self, settings):
        """Execute hyperparameter optimization"""
        try:
            print(f"[INFO] Starting hyperopt with {settings['epochs']} epochs...")

            # Build hyperopt command
            cmd = [
                'docker-compose', 'exec', '-T', 'freqtrade',
                'freqtrade', 'hyperopt',
                '--config', '/freqtrade/config/config.json',
                '--strategy', settings['strategy'],
                '--hyperopt', settings['hyperopt'],
                '--hyperopt-loss', settings['loss_function'],
                '--timerange', settings['timerange'],
                '--epochs', str(settings['epochs']),
                '--spaces'] + settings['spaces']

            # Add additional parameters
            if 'jobs' in settings:
                cmd.extend(['--jobs', str(settings['jobs'])])

            if 'min-trades' in settings:
                cmd.extend(['--min-trades', str(settings['min-trades'])])

            if 'enable-protections' in settings and settings['enable-protections']:
                cmd.append('--enable-protections')

            print(f"[INFO] Running command: {' '.join(cmd)}")

            # Execute hyperopt
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print("[INFO] Hyperopt completed successfully")
                return self.parse_hyperopt_results(result.stdout, settings)
            else:
                print(f"[ERROR] Hyperopt failed: {result.stderr}")
                return None

        except Exception as e:
            print(f"[ERROR] Failed to run hyperopt: {e}")
            return None

    def parse_hyperopt_results(self, output, settings):
        """Parse hyperopt output and extract best parameters"""
        try:
            lines = output.split('\n')
            results = {
                'timestamp': datetime.now().isoformat(),
                'settings': settings,
                'best_params': {},
                'performance': {},
                'epochs_completed': 0
            }

            # Parse output for key information
            for i, line in enumerate(lines):
                line = line.strip()

                # Extract best parameters
                if 'Best parameters:' in line:
                    # Look for parameter lines following
                    j = i + 1
                    while j < len(lines) and lines[j].strip():
                        param_line = lines[j].strip()
                        if ':' in param_line and not param_line.startswith('#'):
                            key, value = param_line.split(':', 1)
                            try:
                                # Try to convert to appropriate type
                                value = value.strip().strip("'\"")
                                if value.lower() in ['true', 'false']:
                                    value = value.lower() == 'true'
                                elif '.' in value:
                                    value = float(value)
                                elif value.isdigit():
                                    value = int(value)
                                results['best_params'][key.strip()] = value
                            except:
                                results['best_params'][key.strip()] = value.strip()
                        j += 1

                # Extract performance metrics
                elif 'Best result:' in line or 'Total profit' in line:
                    if 'Total profit' in line:
                        try:
                            profit = self.extract_number(line)
                            results['performance']['total_profit'] = profit
                        except:
                            pass

                elif 'Avg profit' in line:
                    try:
                        avg_profit = self.extract_number(line)
                        results['performance']['avg_profit'] = avg_profit
                    except:
                        pass

                elif 'Total trade count' in line:
                    try:
                        trade_count = int(self.extract_number(line))
                        results['performance']['trade_count'] = trade_count
                    except:
                        pass

                elif 'epochs' in line.lower() and 'completed' in line.lower():
                    try:
                        epochs = int(self.extract_number(line))
                        results['epochs_completed'] = epochs
                    except:
                        pass

            return results

        except Exception as e:
            print(f"[ERROR] Failed to parse hyperopt results: {e}")
            return None

    def extract_number(self, text):
        """Extract numeric value from text"""
        import re
        numbers = re.findall(r'-?\d+\.?\d*', text.replace(',', ''))
        return float(numbers[-1]) if numbers else 0.0

    def save_results(self, results, suffix=""):
        """Save hyperopt results to files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"hyperopt_results_{timestamp}{suffix}.json"
            filepath = os.path.join(self.results_dir, filename)

            with open(filepath, 'w') as f:
                json.dump(results, f, indent=2, default=str)

            print(f"[INFO] Results saved to: {filepath}")
            return filepath

        except Exception as e:
            print(f"[ERROR] Failed to save results: {e}")
            return None

    def run_optimization_sequence(self, config):
        """Run a sequence of hyperopt optimizations"""
        print("🔧 Starting Hyperopt Optimization Sequence")
        print("=" * 60)

        all_results = []

        # Phase 1: Basic parameters (quick optimization)
        print("\n📊 Phase 1: Basic Parameter Optimization")
        phase1_config = config.copy()
        phase1_config.update({
            'epochs': 100,
            'spaces': ['buy', 'sell'],
            'loss_function': 'SharpeHyperOptLoss',
            'min-trades': 30
        })

        if not self.prepare_data(phase1_config['timerange']):
            print("[ERROR] Failed to prepare data for Phase 1")
            return False

        phase1_results = self.run_hyperopt(phase1_config)
        if phase1_results:
            self.save_results(phase1_results, "_phase1_basic")
            all_results.append(phase1_results)
            print(f"[INFO] Phase 1 completed. Best profit: {phase1_results.get('performance', {}).get('total_profit', 'N/A')}%")

        # Phase 2: ROI and Stoploss optimization
        print("\n💰 Phase 2: ROI and Stoploss Optimization")
        phase2_config = config.copy()
        phase2_config.update({
            'epochs': 150,
            'spaces': ['roi', 'stoploss'],
            'loss_function': 'CalmarHyperOptLoss',
            'min-trades': 50
        })

        phase2_results = self.run_hyperopt(phase2_config)
        if phase2_results:
            self.save_results(phase2_results, "_phase2_roi_stoploss")
            all_results.append(phase2_results)
            print(f"[INFO] Phase 2 completed. Best profit: {phase2_results.get('performance', {}).get('total_profit', 'N/A')}%")

        # Phase 3: Complete optimization
        print("\n🎯 Phase 3: Complete Strategy Optimization")
        phase3_config = config.copy()
        phase3_config.update({
            'epochs': 300,
            'spaces': ['buy', 'sell', 'roi', 'stoploss'],
            'loss_function': 'SharpeHyperOptLoss',
            'min-trades': 100,
            'enable-protections': True
        })

        phase3_results = self.run_hyperopt(phase3_config)
        if phase3_results:
            self.save_results(phase3_results, "_phase3_complete")
            all_results.append(phase3_results)
            print(f"[INFO] Phase 3 completed. Best profit: {phase3_results.get('performance', {}).get('total_profit', 'N/A')}%")

        # Summary
        self.print_optimization_summary(all_results)

        return len(all_results) > 0

    def print_optimization_summary(self, results_list):
        """Print summary of optimization results"""
        print("\n📈 OPTIMIZATION SUMMARY")
        print("=" * 60)

        if not results_list:
            print("No results to display")
            return

        for i, results in enumerate(results_list, 1):
            performance = results.get('performance', {})
            settings = results.get('settings', {})

            print(f"\nPhase {i} ({settings.get('loss_function', 'Unknown')}):")
            print(f"  Epochs: {results.get('epochs_completed', 0)}/{settings.get('epochs', 0)}")
            print(f"  Total Profit: {performance.get('total_profit', 0):.2f}%")
            print(f"  Avg Profit: {performance.get('avg_profit', 0):.3f}%")
            print(f"  Trade Count: {performance.get('trade_count', 0)}")

        # Find best overall result
        best_result = max(results_list,
                         key=lambda x: x.get('performance', {}).get('total_profit', -999))

        print(f"\n🏆 BEST OVERALL RESULT:")
        best_perf = best_result.get('performance', {})
        print(f"  Total Profit: {best_perf.get('total_profit', 0):.2f}%")
        print(f"  Avg Profit: {best_perf.get('avg_profit', 0):.3f}%")
        print(f"  Trade Count: {best_perf.get('trade_count', 0)}")

        # Display best parameters
        best_params = best_result.get('best_params', {})
        if best_params:
            print(f"\n⚙️  BEST PARAMETERS:")
            for key, value in best_params.items():
                print(f"  {key}: {value}")

    def generate_config_file(self, results, output_path="optimized_config.json"):
        """Generate optimized configuration file"""
        try:
            best_params = results.get('best_params', {})

            # Read current config
            with open(self.config_path, 'r') as f:
                config = json.load(f)

            # Update with optimized parameters
            # This would need to be customized based on your config structure
            if 'stoploss' in best_params:
                config['stoploss'] = best_params['stoploss']

            # ROI table
            roi_params = {k: v for k, v in best_params.items() if k.startswith('roi-')}
            if roi_params:
                # Convert roi parameters to ROI table
                config['minimal_roi'] = self.generate_roi_table(roi_params)

            # Save optimized config
            output_file = os.path.join(self.results_dir, output_path)
            with open(output_file, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"[INFO] Optimized config saved to: {output_file}")
            return output_file

        except Exception as e:
            print(f"[ERROR] Failed to generate config file: {e}")
            return None

    def generate_roi_table(self, roi_params):
        """Generate ROI table from parameters"""
        # Default ROI table
        return {
            "0": 0.10,
            "40": 0.04,
            "100": 0.02,
            "240": 0
        }


def main():
    """Main hyperopt runner"""
    parser = argparse.ArgumentParser(description='Run hyperparameter optimization')

    parser.add_argument('--epochs', type=int, default=300, help='Number of optimization epochs')
    parser.add_argument('--timerange', default='20241101-20241222', help='Timerange for optimization')
    parser.add_argument('--strategy', default='MultiIndicatorStrategy', help='Strategy to optimize')
    parser.add_argument('--loss', default='SharpeHyperOptLoss', help='Loss function')
    parser.add_argument('--spaces', nargs='+', default=['buy', 'sell', 'roi', 'stoploss'], help='Parameter spaces')
    parser.add_argument('--sequence', action='store_true', help='Run optimization sequence')
    parser.add_argument('--jobs', type=int, help='Number of parallel jobs')

    args = parser.parse_args()

    # Initialize runner
    runner = HyperOptRunner()

    # Build configuration
    config = runner.default_settings.copy()
    config.update({
        'epochs': args.epochs,
        'timerange': args.timerange,
        'strategy': args.strategy,
        'loss_function': args.loss,
        'spaces': args.spaces
    })

    if args.jobs:
        config['jobs'] = args.jobs

    # Run optimization
    if args.sequence:
        success = runner.run_optimization_sequence(config)
    else:
        # Single optimization run
        if not runner.prepare_data(config['timerange']):
            print("[ERROR] Failed to prepare data")
            sys.exit(1)

        results = runner.run_hyperopt(config)
        if results:
            runner.save_results(results)
            runner.print_optimization_summary([results])
            success = True
        else:
            success = False

    if success:
        print("\n🎉 Hyperopt optimization completed successfully!")
        print("Check user_data/hyperopt_results/ for detailed results.")
    else:
        print("\n❌ Hyperopt optimization failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()