#!/usr/bin/env python3
"""
Advanced Strategy Analysis and Performance Comparison Tool
Comprehensive backtesting and analysis for multiple strategies
"""

import sys
import os
import subprocess
import json
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

# Plotting libraries
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    PLOTTING_AVAILABLE = True
except ImportError:
    PLOTTING_AVAILABLE = False
    print("[WARN] Matplotlib/Seaborn not available. Plotting disabled.")


class StrategyAnalyzer:
    """Advanced strategy analysis and comparison system"""

    def __init__(self, config_path="config/config.json"):
        self.config_path = config_path
        self.results_dir = "user_data/analysis_results"
        os.makedirs(self.results_dir, exist_ok=True)

        # Available strategies
        self.strategies = {
            'RSIStrategy': 'Conservative RSI-based strategy',
            'AITradingStrategy': 'AI-powered RandomForest + GradientBoosting',
            'MultiIndicatorStrategy': 'Multi-indicator with weighted signals'
        }

    def run_comprehensive_backtest(self, strategy, timerange, additional_args=None):
        """Run comprehensive backtest with detailed analysis"""
        try:
            print(f"[INFO] Running comprehensive backtest for {strategy}...")

            # Build backtest command
            cmd = [
                'docker-compose', 'exec', '-T', 'freqtrade',
                'freqtrade', 'backtesting',
                '--config', '/freqtrade/config/config.json',
                '--strategy', strategy,
                '--timerange', timerange,
                '--export', 'trades,signals',
                '--cache', 'none',  # Fresh calculation
                '--breakdown', 'day,week,month',
                '--export-filename', f'user_data/backtest_results/{strategy}_{timerange}_detailed'
            ]

            if additional_args:
                cmd.extend(additional_args)

            # Execute backtest
            result = subprocess.run(cmd, capture_output=True, text=True, cwd='.')

            if result.returncode == 0:
                print(f"[INFO] Backtest completed for {strategy}")
                return self.parse_detailed_backtest(result.stdout, strategy, timerange)
            else:
                print(f"[ERROR] Backtest failed for {strategy}: {result.stderr}")
                return None

        except Exception as e:
            print(f"[ERROR] Failed to run backtest for {strategy}: {e}")
            return None

    def parse_detailed_backtest(self, output, strategy, timerange):
        """Parse detailed backtest output"""
        try:
            lines = output.split('\n')
            results = {
                'strategy': strategy,
                'timerange': timerange,
                'timestamp': datetime.now().isoformat(),
                'performance': {},
                'risk_metrics': {},
                'trade_analysis': {},
                'daily_breakdown': [],
                'monthly_breakdown': []
            }

            # Parse key metrics
            for line in lines:
                line = line.strip()

                # Performance metrics
                if 'Total trades' in line:
                    results['performance']['total_trades'] = self.extract_number(line)
                elif 'Starting balance' in line:
                    results['performance']['starting_balance'] = self.extract_number(line)
                elif 'Final balance' in line:
                    results['performance']['final_balance'] = self.extract_number(line)
                elif 'Absolute profit' in line:
                    results['performance']['absolute_profit'] = self.extract_number(line)
                elif 'Total profit %' in line:
                    results['performance']['total_return'] = self.extract_number(line)
                elif 'Avg. profit %' in line:
                    results['performance']['avg_profit_per_trade'] = self.extract_number(line)
                elif 'Median profit %' in line:
                    results['performance']['median_profit'] = self.extract_number(line)

                # Risk metrics
                elif 'Sharpe' in line:
                    results['risk_metrics']['sharpe_ratio'] = self.extract_number(line)
                elif 'Sortino' in line:
                    results['risk_metrics']['sortino_ratio'] = self.extract_number(line)
                elif 'Calmar' in line:
                    results['risk_metrics']['calmar_ratio'] = self.extract_number(line)
                elif 'Max Drawdown' in line:
                    results['risk_metrics']['max_drawdown'] = self.extract_number(line)
                elif 'Avg. Drawdown' in line:
                    results['risk_metrics']['avg_drawdown'] = self.extract_number(line)

                # Win/Loss analysis
                elif 'Wins/Draws/Losses' in line:
                    parts = line.split(':')[1].strip() if ':' in line else ''
                    if '/' in parts:
                        wins, draws, losses = parts.split('/')
                        results['trade_analysis']['wins'] = int(wins.strip())
                        results['trade_analysis']['draws'] = int(draws.strip())
                        results['trade_analysis']['losses'] = int(losses.strip())
                elif 'Win rate' in line:
                    results['trade_analysis']['win_rate'] = self.extract_number(line)

                # Time-based performance
                elif 'Best day' in line:
                    results['performance']['best_day'] = self.extract_number(line)
                elif 'Worst day' in line:
                    results['performance']['worst_day'] = self.extract_number(line)

            # Calculate additional metrics
            results = self.calculate_additional_metrics(results)

            return results

        except Exception as e:
            print(f"[ERROR] Failed to parse backtest results: {e}")
            return None

    def calculate_additional_metrics(self, results):
        """Calculate additional performance metrics"""
        try:
            perf = results['performance']
            risk = results['risk_metrics']
            trade = results['trade_analysis']

            # Profit factor
            total_trades = perf.get('total_trades', 0)
            wins = trade.get('wins', 0)
            losses = trade.get('losses', 0)

            if total_trades > 0:
                # Average trade duration (estimated)
                results['trade_analysis']['avg_trade_duration'] = '2.5 hours'  # Placeholder

                # Profit factor calculation (simplified)
                if losses > 0:
                    win_rate = trade.get('win_rate', 0) / 100
                    avg_win = perf.get('avg_profit_per_trade', 0) * (wins / max(total_trades, 1))
                    avg_loss = perf.get('avg_profit_per_trade', 0) * (losses / max(total_trades, 1))

                    if avg_loss < 0:
                        profit_factor = abs(avg_win) / abs(avg_loss)
                        results['risk_metrics']['profit_factor'] = profit_factor

                # Expectancy
                avg_profit = perf.get('avg_profit_per_trade', 0)
                win_rate_decimal = trade.get('win_rate', 0) / 100
                results['risk_metrics']['expectancy'] = avg_profit

                # Recovery factor
                max_dd = risk.get('max_drawdown', 1)
                total_return = perf.get('total_return', 0)
                if max_dd != 0:
                    results['risk_metrics']['recovery_factor'] = total_return / abs(max_dd)

            return results

        except Exception as e:
            print(f"[ERROR] Failed to calculate additional metrics: {e}")
            return results

    def extract_number(self, text):
        """Extract numeric value from text"""
        import re
        numbers = re.findall(r'-?\d+\.?\d*', text.replace(',', ''))
        return float(numbers[-1]) if numbers else 0.0

    def compare_strategies(self, strategies, timerange, save_results=True):
        """Compare multiple strategies comprehensively"""
        print("📊 Strategy Comparison Analysis")
        print("=" * 80)

        results = {}

        # Run backtests for all strategies
        for strategy in strategies:
            print(f"\n🔄 Analyzing {strategy}...")
            result = self.run_comprehensive_backtest(strategy, timerange)
            if result:
                results[strategy] = result
            else:
                print(f"[WARN] Skipping {strategy} due to backtest failure")

        if not results:
            print("[ERROR] No successful backtests to compare")
            return None

        # Generate comparison
        comparison = self.generate_comparison_analysis(results)

        # Save results
        if save_results:
            self.save_analysis_results(comparison, timerange)

        # Display results
        self.display_comparison_results(comparison)

        return comparison

    def generate_comparison_analysis(self, results):
        """Generate comprehensive comparison analysis"""
        comparison = {
            'timestamp': datetime.now().isoformat(),
            'strategies': list(results.keys()),
            'summary': {},
            'detailed_comparison': {},
            'rankings': {},
            'recommendations': {}
        }

        # Create comparison table
        metrics = [
            'total_return', 'avg_profit_per_trade', 'total_trades',
            'win_rate', 'max_drawdown', 'sharpe_ratio', 'profit_factor'
        ]

        comparison_data = {}
        for strategy, result in results.items():
            comparison_data[strategy] = {}
            perf = result.get('performance', {})
            risk = result.get('risk_metrics', {})
            trade = result.get('trade_analysis', {})

            comparison_data[strategy].update({
                'total_return': perf.get('total_return', 0),
                'avg_profit_per_trade': perf.get('avg_profit_per_trade', 0),
                'total_trades': perf.get('total_trades', 0),
                'win_rate': trade.get('win_rate', 0),
                'max_drawdown': risk.get('max_drawdown', 0),
                'sharpe_ratio': risk.get('sharpe_ratio', 0),
                'profit_factor': risk.get('profit_factor', 1.0)
            })

        comparison['detailed_comparison'] = comparison_data

        # Generate rankings
        comparison['rankings'] = self.generate_rankings(comparison_data)

        # Generate recommendations
        comparison['recommendations'] = self.generate_recommendations(comparison_data)

        return comparison

    def generate_rankings(self, data):
        """Generate strategy rankings by different metrics"""
        rankings = {}

        metrics_higher_better = ['total_return', 'avg_profit_per_trade', 'win_rate', 'sharpe_ratio', 'profit_factor']
        metrics_lower_better = ['max_drawdown']

        for metric in metrics_higher_better:
            sorted_strategies = sorted(data.items(), key=lambda x: x[1].get(metric, 0), reverse=True)
            rankings[metric] = [strategy for strategy, _ in sorted_strategies]

        for metric in metrics_lower_better:
            sorted_strategies = sorted(data.items(), key=lambda x: abs(x[1].get(metric, 999)))
            rankings[metric] = [strategy for strategy, _ in sorted_strategies]

        # Overall ranking (weighted score)
        overall_scores = {}
        for strategy in data.keys():
            score = 0
            weights = {
                'total_return': 0.25,
                'sharpe_ratio': 0.20,
                'max_drawdown': -0.15,  # Negative because lower is better
                'win_rate': 0.15,
                'profit_factor': 0.15,
                'avg_profit_per_trade': 0.10
            }

            for metric, weight in weights.items():
                value = data[strategy].get(metric, 0)
                if metric == 'max_drawdown':
                    score += weight * (1.0 / (1.0 + abs(value)))  # Inverse for drawdown
                else:
                    score += weight * value

            overall_scores[strategy] = score

        sorted_overall = sorted(overall_scores.items(), key=lambda x: x[1], reverse=True)
        rankings['overall'] = [strategy for strategy, _ in sorted_overall]

        return rankings

    def generate_recommendations(self, data):
        """Generate strategy recommendations"""
        recommendations = {
            'best_overall': '',
            'most_profitable': '',
            'safest': '',
            'most_active': '',
            'analysis': []
        }

        if not data:
            return recommendations

        # Best overall (highest total return with reasonable risk)
        best_overall = max(data.items(), key=lambda x: x[1].get('total_return', 0))
        recommendations['best_overall'] = best_overall[0]

        # Most profitable
        most_profitable = max(data.items(), key=lambda x: x[1].get('avg_profit_per_trade', 0))
        recommendations['most_profitable'] = most_profitable[0]

        # Safest (lowest drawdown with positive returns)
        safe_strategies = {k: v for k, v in data.items() if v.get('total_return', 0) > 0}
        if safe_strategies:
            safest = min(safe_strategies.items(), key=lambda x: abs(x[1].get('max_drawdown', 999)))
            recommendations['safest'] = safest[0]

        # Most active
        most_active = max(data.items(), key=lambda x: x[1].get('total_trades', 0))
        recommendations['most_active'] = most_active[0]

        # Generate analysis
        for strategy, metrics in data.items():
            analysis = f"{strategy}: "

            total_return = metrics.get('total_return', 0)
            max_dd = metrics.get('max_drawdown', 0)
            win_rate = metrics.get('win_rate', 0)
            sharpe = metrics.get('sharpe_ratio', 0)

            if total_return > 10 and max_dd < 10 and win_rate > 60:
                analysis += "Excellent performance with good risk control"
            elif total_return > 5 and max_dd < 15:
                analysis += "Good performance with acceptable risk"
            elif total_return > 0:
                analysis += "Profitable but needs optimization"
            else:
                analysis += "Needs significant improvement"

            if sharpe > 1.5:
                analysis += ", excellent risk-adjusted returns"
            elif sharpe > 1.0:
                analysis += ", good risk-adjusted returns"
            elif sharpe > 0.5:
                analysis += ", moderate risk-adjusted returns"
            else:
                analysis += ", poor risk-adjusted returns"

            recommendations['analysis'].append(analysis)

        return recommendations

    def display_comparison_results(self, comparison):
        """Display comprehensive comparison results"""
        print("\n📈 STRATEGY COMPARISON RESULTS")
        print("=" * 80)

        detailed = comparison.get('detailed_comparison', {})

        # Performance table
        print("\n🎯 Performance Metrics:")
        print("-" * 100)
        print(f"{'Strategy':<25} {'Return%':<10} {'Trades':<8} {'Avg%':<8} {'Win%':<8} {'Drawdown%':<12} {'Sharpe':<8}")
        print("-" * 100)

        for strategy, metrics in detailed.items():
            return_pct = metrics.get('total_return', 0)
            trades = metrics.get('total_trades', 0)
            avg_profit = metrics.get('avg_profit_per_trade', 0)
            win_rate = metrics.get('win_rate', 0)
            drawdown = metrics.get('max_drawdown', 0)
            sharpe = metrics.get('sharpe_ratio', 0)

            print(f"{strategy:<25} {return_pct:<10.2f} {trades:<8.0f} {avg_profit:<8.3f} {win_rate:<8.1f} {drawdown:<12.2f} {sharpe:<8.2f}")

        # Rankings
        rankings = comparison.get('rankings', {})
        print("\n🏆 Strategy Rankings:")
        print("-" * 50)

        key_rankings = ['overall', 'total_return', 'sharpe_ratio', 'max_drawdown']
        for ranking_type in key_rankings:
            if ranking_type in rankings:
                strategies = rankings[ranking_type]
                print(f"{ranking_type.replace('_', ' ').title():<20}: {' > '.join(strategies)}")

        # Recommendations
        recommendations = comparison.get('recommendations', {})
        print("\n💡 RECOMMENDATIONS:")
        print("-" * 50)

        rec_types = ['best_overall', 'most_profitable', 'safest', 'most_active']
        for rec_type in rec_types:
            if rec_type in recommendations and recommendations[rec_type]:
                print(f"{rec_type.replace('_', ' ').title():<20}: {recommendations[rec_type]}")

        print("\n📋 Analysis:")
        for analysis in recommendations.get('analysis', []):
            print(f"  • {analysis}")

        # Risk analysis
        print("\n⚠️  Risk Analysis:")
        print("-" * 50)
        for strategy, metrics in detailed.items():
            max_dd = metrics.get('max_drawdown', 0)
            sharpe = metrics.get('sharpe_ratio', 0)
            profit_factor = metrics.get('profit_factor', 1.0)

            risk_level = "LOW"
            if max_dd > 15 or sharpe < 0.5 or profit_factor < 1.2:
                risk_level = "HIGH"
            elif max_dd > 8 or sharpe < 1.0 or profit_factor < 1.5:
                risk_level = "MEDIUM"

            print(f"{strategy:<25}: {risk_level} risk (DD: {max_dd:.1f}%, Sharpe: {sharpe:.2f}, PF: {profit_factor:.2f})")

    def save_analysis_results(self, comparison, timerange):
        """Save analysis results to files"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Save detailed comparison
            results_file = os.path.join(self.results_dir, f"strategy_analysis_{timerange}_{timestamp}.json")
            with open(results_file, 'w') as f:
                json.dump(comparison, f, indent=2, default=str)

            # Save summary CSV
            detailed = comparison.get('detailed_comparison', {})
            if detailed:
                df = pd.DataFrame.from_dict(detailed, orient='index')
                csv_file = os.path.join(self.results_dir, f"strategy_summary_{timerange}_{timestamp}.csv")
                df.to_csv(csv_file)

            print(f"\n[INFO] Analysis results saved:")
            print(f"  - Detailed: {results_file}")
            if detailed:
                print(f"  - Summary: {csv_file}")

        except Exception as e:
            print(f"[ERROR] Failed to save analysis results: {e}")

    def generate_performance_report(self, timerange, strategies=None):
        """Generate comprehensive performance report"""
        if strategies is None:
            strategies = list(self.strategies.keys())

        print("📊 Generating Comprehensive Performance Report")
        print("=" * 80)

        # Run analysis
        comparison = self.compare_strategies(strategies, timerange)

        if not comparison:
            print("[ERROR] Failed to generate performance report")
            return False

        # Additional analysis
        self.analyze_market_conditions(timerange)
        self.analyze_parameter_sensitivity(strategies[0] if strategies else 'MultiIndicatorStrategy')

        print("\n🎉 Performance report generation completed!")
        print(f"Check {self.results_dir} for detailed results.")

        return True

    def analyze_market_conditions(self, timerange):
        """Analyze market conditions during the test period"""
        print(f"\n📈 Market Conditions Analysis ({timerange})")
        print("-" * 50)

        # This would analyze market volatility, trends, etc.
        # For now, provide a placeholder analysis
        print("• Market analysis would show volatility patterns")
        print("• Trend analysis would identify bull/bear periods")
        print("• Volume analysis would show trading activity levels")

    def analyze_parameter_sensitivity(self, strategy):
        """Analyze parameter sensitivity for a strategy"""
        print(f"\n🔧 Parameter Sensitivity Analysis ({strategy})")
        print("-" * 50)

        # This would test different parameter combinations
        print("• Parameter sensitivity testing would show:")
        print("  - Impact of RSI period changes")
        print("  - Effect of MACD parameter variations")
        print("  - Bollinger Band period sensitivity")
        print("  - Signal threshold optimization opportunities")


def main():
    """Main analysis script"""
    import argparse

    parser = argparse.ArgumentParser(description='Advanced strategy analysis and comparison')
    parser.add_argument('--strategies', nargs='+',
                       default=['RSIStrategy', 'AITradingStrategy', 'MultiIndicatorStrategy'],
                       help='Strategies to analyze')
    parser.add_argument('--timerange', default='20241101-20241222',
                       help='Timerange for analysis')
    parser.add_argument('--report', action='store_true',
                       help='Generate comprehensive report')

    args = parser.parse_args()

    # Initialize analyzer
    analyzer = StrategyAnalyzer()

    # Run analysis
    if args.report:
        success = analyzer.generate_performance_report(args.timerange, args.strategies)
    else:
        comparison = analyzer.compare_strategies(args.strategies, args.timerange)
        success = comparison is not None

    if success:
        print("\n🎉 Strategy analysis completed successfully!")
    else:
        print("\n❌ Strategy analysis failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()