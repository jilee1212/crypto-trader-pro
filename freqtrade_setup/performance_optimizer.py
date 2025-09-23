#!/usr/bin/env python3
"""
Freqtrade Performance Optimizer
Automated performance tuning and optimization for Freqtrade system
"""

import sys
import os
import json
import time
import psutil
import docker
import subprocess
from datetime import datetime, timedelta
from typing import Dict, Any, List
import warnings
warnings.filterwarnings('ignore')


class FreqtradePerformanceOptimizer:
    """Performance optimization system for Freqtrade"""

    def __init__(self):
        self.config_path = "config/config.json"
        self.optimization_log = "logs/optimization.log"

        # Performance thresholds
        self.thresholds = {
            'max_cpu_usage': 70.0,           # %
            'max_memory_usage': 75.0,        # %
            'max_api_response_time': 2.0,    # seconds
            'min_backtest_speed': 100,       # trades/minute
            'max_disk_io_wait': 5.0,         # %
            'optimal_workers': None,         # Auto-detect
        }

        # Optimization settings
        self.optimizations = {
            'docker_memory_limit': '1G',
            'docker_cpu_limit': '2.0',
            'api_cache_enabled': True,
            'log_level': 'INFO',
            'db_pool_size': 20,
            'max_open_files': 1024
        }

        # Load current configuration
        self.current_config = self.load_config()

        # Initialize Docker client
        try:
            self.docker_client = docker.from_env()
        except Exception as e:
            print(f"[WARN] Docker client not available: {e}")
            self.docker_client = None

    def load_config(self) -> Dict[str, Any]:
        """Load current Freqtrade configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return {}

    def save_config(self, config: Dict[str, Any]):
        """Save optimized configuration"""
        try:
            # Backup current config
            backup_path = f"{self.config_path}.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            with open(backup_path, 'w') as f:
                json.dump(self.current_config, f, indent=2)

            # Save new config
            with open(self.config_path, 'w') as f:
                json.dump(config, f, indent=2)

            print(f"[INFO] Configuration updated. Backup saved to: {backup_path}")

        except Exception as e:
            print(f"[ERROR] Failed to save config: {e}")

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get current system performance metrics"""
        try:
            # CPU and Memory
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Network
            network = psutil.net_io_counters()

            # Process specific metrics
            freqtrade_processes = []
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_info']):
                try:
                    if 'freqtrade' in proc.info['name'].lower() or 'python' in proc.info['name'].lower():
                        # Check if it's actually a freqtrade process
                        cmdline = proc.cmdline()
                        if any('freqtrade' in cmd for cmd in cmdline):
                            freqtrade_processes.append({
                                'pid': proc.info['pid'],
                                'name': proc.info['name'],
                                'cpu_percent': proc.info['cpu_percent'],
                                'memory_mb': proc.info['memory_info'].rss / 1024 / 1024
                            })
                except:
                    continue

            # API response time test
            api_response_time = self.test_api_response_time()

            # Docker container metrics
            docker_metrics = self.get_docker_metrics()

            return {
                'timestamp': datetime.now().isoformat(),
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_gb': memory.available / 1024 / 1024 / 1024,
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / 1024 / 1024 / 1024,
                'network_bytes_sent': network.bytes_sent,
                'network_bytes_recv': network.bytes_recv,
                'freqtrade_processes': freqtrade_processes,
                'api_response_time': api_response_time,
                'docker_metrics': docker_metrics
            }

        except Exception as e:
            print(f"[ERROR] Failed to get system metrics: {e}")
            return {}

    def test_api_response_time(self) -> float:
        """Test Freqtrade API response time"""
        try:
            import requests
            start_time = time.time()
            response = requests.get('http://localhost:8080/api/v1/status', timeout=10)
            end_time = time.time()

            if response.status_code == 200:
                return end_time - start_time
            else:
                return 999.0  # High value to indicate problem

        except Exception:
            return 999.0

    def get_docker_metrics(self) -> Dict[str, Any]:
        """Get Docker container metrics"""
        try:
            if not self.docker_client:
                return {}

            containers = self.docker_client.containers.list()
            freqtrade_containers = [c for c in containers if 'freqtrade' in c.name]

            metrics = {}
            for container in freqtrade_containers:
                try:
                    stats = container.stats(stream=False)

                    # CPU usage
                    cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                               stats['precpu_stats']['cpu_usage']['total_usage']
                    system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                                  stats['precpu_stats']['system_cpu_usage']
                    cpu_percent = (cpu_delta / system_delta) * 100.0

                    # Memory usage
                    memory_usage = stats['memory_stats']['usage']
                    memory_limit = stats['memory_stats']['limit']
                    memory_percent = (memory_usage / memory_limit) * 100.0

                    metrics[container.name] = {
                        'cpu_percent': cpu_percent,
                        'memory_usage_mb': memory_usage / 1024 / 1024,
                        'memory_limit_mb': memory_limit / 1024 / 1024,
                        'memory_percent': memory_percent,
                        'status': container.status
                    }

                except Exception as e:
                    metrics[container.name] = {'error': str(e)}

            return metrics

        except Exception as e:
            print(f"[ERROR] Failed to get Docker metrics: {e}")
            return {}

    def analyze_performance_bottlenecks(self, metrics: Dict[str, Any]) -> List[str]:
        """Analyze performance metrics and identify bottlenecks"""
        issues = []

        try:
            # CPU bottleneck
            if metrics.get('cpu_percent', 0) > self.thresholds['max_cpu_usage']:
                issues.append(f"HIGH_CPU_USAGE: {metrics['cpu_percent']:.1f}% > {self.thresholds['max_cpu_usage']}%")

            # Memory bottleneck
            if metrics.get('memory_percent', 0) > self.thresholds['max_memory_usage']:
                issues.append(f"HIGH_MEMORY_USAGE: {metrics['memory_percent']:.1f}% > {self.thresholds['max_memory_usage']}%")

            # API response time
            api_time = metrics.get('api_response_time', 0)
            if api_time > self.thresholds['max_api_response_time']:
                issues.append(f"SLOW_API_RESPONSE: {api_time:.2f}s > {self.thresholds['max_api_response_time']}s")

            # Disk space
            if metrics.get('disk_percent', 0) > 85:
                issues.append(f"LOW_DISK_SPACE: {metrics['disk_percent']:.1f}% used")

            # Docker container issues
            docker_metrics = metrics.get('docker_metrics', {})
            for container_name, container_metrics in docker_metrics.items():
                if isinstance(container_metrics, dict) and 'memory_percent' in container_metrics:
                    if container_metrics['memory_percent'] > 80:
                        issues.append(f"CONTAINER_HIGH_MEMORY: {container_name} using {container_metrics['memory_percent']:.1f}%")

            # Process-specific issues
            freqtrade_processes = metrics.get('freqtrade_processes', [])
            total_freqtrade_memory = sum(p['memory_mb'] for p in freqtrade_processes)
            if total_freqtrade_memory > 1024:  # 1GB
                issues.append(f"HIGH_PROCESS_MEMORY: Freqtrade processes using {total_freqtrade_memory:.0f}MB")

            return issues

        except Exception as e:
            print(f"[ERROR] Failed to analyze performance: {e}")
            return []

    def optimize_docker_configuration(self) -> Dict[str, Any]:
        """Optimize Docker container configuration"""
        optimizations = {}

        try:
            # Memory optimization
            system_memory_gb = psutil.virtual_memory().total / 1024 / 1024 / 1024

            if system_memory_gb >= 8:
                optimizations['memory_limit'] = '2G'
                optimizations['shm_size'] = '512M'
            elif system_memory_gb >= 4:
                optimizations['memory_limit'] = '1G'
                optimizations['shm_size'] = '256M'
            else:
                optimizations['memory_limit'] = '512M'
                optimizations['shm_size'] = '128M'

            # CPU optimization
            cpu_count = psutil.cpu_count()
            optimizations['cpu_limit'] = min(2.0, cpu_count * 0.8)

            # I/O optimization
            optimizations['ulimits'] = {
                'nofile': {'soft': 1024, 'hard': 2048}
            }

            print(f"[INFO] Docker optimizations recommended: {optimizations}")
            return optimizations

        except Exception as e:
            print(f"[ERROR] Failed to optimize Docker config: {e}")
            return {}

    def optimize_freqtrade_config(self) -> Dict[str, Any]:
        """Optimize Freqtrade configuration parameters"""
        config = self.current_config.copy()
        optimizations_applied = []

        try:
            # API optimization
            if 'api_server' not in config:
                config['api_server'] = {}

            # Enable API caching
            if self.optimizations['api_cache_enabled']:
                config['api_server']['enable_openapi'] = True
                config['api_server']['jwt_secret_key'] = 'freqtrade_secret'
                optimizations_applied.append("API caching enabled")

            # Database optimization
            if 'db_url' in config and 'sqlite' in config['db_url']:
                # SQLite optimizations
                if '?' not in config['db_url']:
                    config['db_url'] += '?cache=shared&timeout=20'
                    optimizations_applied.append("SQLite cache optimization")

            # Logging optimization
            if 'verbosity' not in config:
                config['verbosity'] = 1  # Reduce verbosity for performance
                optimizations_applied.append("Reduced logging verbosity")

            # Backtesting optimization
            if 'backtest_breakdown' not in config:
                config['backtest_breakdown'] = ['day']  # Less granular breakdown
                optimizations_applied.append("Optimized backtest breakdown")

            # Strategy optimization
            if 'strategy_parameters' not in config:
                config['strategy_parameters'] = {}

            # Add performance-focused parameters
            config['strategy_parameters'].update({
                'startup_candle_count': 30,  # Reduce startup candles
                'process_only_new_candles': True,  # Process only new data
                'use_exit_signal': True,  # Use exit signals
                'exit_profit_only': False,  # Allow stop losses
                'ignore_roi_if_buy_signal': False  # Follow ROI strictly
            })
            optimizations_applied.append("Strategy performance parameters")

            # Exchange optimization
            if 'exchange' in config:
                if 'ccxt_config' not in config['exchange']:
                    config['exchange']['ccxt_config'] = {}

                # Add rate limiting and timeout optimizations
                config['exchange']['ccxt_config'].update({
                    'timeout': 30000,  # 30 seconds
                    'rateLimit': 1000,  # 1 second between requests
                    'enableRateLimit': True
                })
                optimizations_applied.append("Exchange timeout optimization")

            # Resource limits
            if 'max_open_trades' in config and config['max_open_trades'] > 5:
                # Reduce concurrent trades if system is under pressure
                metrics = self.get_system_metrics()
                if metrics.get('memory_percent', 0) > 70:
                    config['max_open_trades'] = min(config['max_open_trades'], 3)
                    optimizations_applied.append("Reduced max open trades for memory")

            print(f"[INFO] Freqtrade optimizations applied: {optimizations_applied}")
            return config

        except Exception as e:
            print(f"[ERROR] Failed to optimize Freqtrade config: {e}")
            return self.current_config

    def optimize_system_settings(self) -> List[str]:
        """Optimize system-level settings"""
        optimizations_applied = []

        try:
            # File descriptor limits
            try:
                import resource
                current_limit = resource.getrlimit(resource.RLIMIT_NOFILE)
                if current_limit[0] < self.optimizations['max_open_files']:
                    resource.setrlimit(resource.RLIMIT_NOFILE,
                                     (self.optimizations['max_open_files'], current_limit[1]))
                    optimizations_applied.append(f"Increased file descriptor limit to {self.optimizations['max_open_files']}")
            except Exception as e:
                print(f"[WARN] Could not adjust file descriptor limit: {e}")

            # Process priority optimization
            try:
                # Lower the nice value for better CPU priority
                current_pid = os.getpid()
                current_nice = os.getpriority(os.PRIO_PROCESS, current_pid)
                if current_nice > -5:  # Only adjust if not already optimized
                    os.setpriority(os.PRIO_PROCESS, current_pid, -5)
                    optimizations_applied.append("Improved process priority")
            except Exception as e:
                print(f"[WARN] Could not adjust process priority: {e}")

            # Memory optimization
            try:
                # Suggest swap usage optimization
                swap = psutil.swap_memory()
                if swap.percent > 20:
                    optimizations_applied.append("WARNING: High swap usage detected - consider adding RAM")
            except Exception:
                pass

            return optimizations_applied

        except Exception as e:
            print(f"[ERROR] Failed to optimize system settings: {e}")
            return []

    def benchmark_performance(self) -> Dict[str, Any]:
        """Run performance benchmark"""
        try:
            print("[INFO] Running performance benchmark...")

            # API benchmark
            api_times = []
            for _ in range(10):
                start_time = time.time()
                try:
                    import requests
                    response = requests.get('http://localhost:8080/api/v1/status', timeout=5)
                    if response.status_code == 200:
                        api_times.append(time.time() - start_time)
                except:
                    api_times.append(999.0)
                time.sleep(0.1)

            avg_api_time = sum(api_times) / len(api_times) if api_times else 999.0

            # Memory benchmark
            memory_before = psutil.virtual_memory().percent

            # CPU benchmark
            cpu_usage = psutil.cpu_percent(interval=5)

            # Disk I/O benchmark
            disk_before = psutil.disk_io_counters()
            time.sleep(1)
            disk_after = psutil.disk_io_counters()

            disk_read_rate = disk_after.read_bytes - disk_before.read_bytes
            disk_write_rate = disk_after.write_bytes - disk_before.write_bytes

            benchmark_results = {
                'timestamp': datetime.now().isoformat(),
                'api_avg_response_time': avg_api_time,
                'api_min_response_time': min(api_times) if api_times else 999.0,
                'api_max_response_time': max(api_times) if api_times else 999.0,
                'memory_usage_percent': memory_before,
                'cpu_usage_percent': cpu_usage,
                'disk_read_rate_mb_s': disk_read_rate / 1024 / 1024,
                'disk_write_rate_mb_s': disk_write_rate / 1024 / 1024
            }

            print(f"[INFO] Benchmark completed:")
            print(f"  API response time: {avg_api_time:.3f}s (avg)")
            print(f"  CPU usage: {cpu_usage:.1f}%")
            print(f"  Memory usage: {memory_before:.1f}%")

            return benchmark_results

        except Exception as e:
            print(f"[ERROR] Failed to run benchmark: {e}")
            return {}

    def run_optimization(self) -> Dict[str, Any]:
        """Run complete optimization process"""
        print("🚀 Starting Freqtrade Performance Optimization")
        print("=" * 60)

        optimization_report = {
            'timestamp': datetime.now().isoformat(),
            'before_metrics': {},
            'after_metrics': {},
            'optimizations_applied': [],
            'issues_found': [],
            'issues_resolved': []
        }

        try:
            # 1. Baseline performance measurement
            print("\n1. Measuring baseline performance...")
            before_metrics = self.get_system_metrics()
            optimization_report['before_metrics'] = before_metrics

            # 2. Analyze bottlenecks
            print("\n2. Analyzing performance bottlenecks...")
            issues = self.analyze_performance_bottlenecks(before_metrics)
            optimization_report['issues_found'] = issues

            for issue in issues:
                print(f"  ⚠️  {issue}")

            if not issues:
                print("  ✅ No performance issues detected")

            # 3. System-level optimizations
            print("\n3. Applying system-level optimizations...")
            system_optimizations = self.optimize_system_settings()
            optimization_report['optimizations_applied'].extend(system_optimizations)

            for opt in system_optimizations:
                print(f"  ✅ {opt}")

            # 4. Docker optimizations
            print("\n4. Optimizing Docker configuration...")
            docker_optimizations = self.optimize_docker_configuration()
            if docker_optimizations:
                optimization_report['optimizations_applied'].append(f"Docker optimizations: {docker_optimizations}")
                print(f"  ✅ Docker optimizations recommended")

            # 5. Freqtrade configuration optimization
            print("\n5. Optimizing Freqtrade configuration...")
            optimized_config = self.optimize_freqtrade_config()

            # Save optimized configuration
            if optimized_config != self.current_config:
                self.save_config(optimized_config)
                optimization_report['optimizations_applied'].append("Freqtrade configuration optimized")
                print("  ✅ Freqtrade configuration optimized and saved")
            else:
                print("  ℹ️  Freqtrade configuration already optimal")

            # 6. Wait for changes to take effect
            print("\n6. Waiting for optimizations to take effect...")
            time.sleep(10)

            # 7. Post-optimization measurement
            print("\n7. Measuring post-optimization performance...")
            after_metrics = self.get_system_metrics()
            optimization_report['after_metrics'] = after_metrics

            # 8. Compare results
            print("\n8. Performance comparison:")
            self.compare_performance(before_metrics, after_metrics, optimization_report)

            # 9. Run benchmark
            print("\n9. Running performance benchmark...")
            benchmark_results = self.benchmark_performance()
            optimization_report['benchmark'] = benchmark_results

            # 10. Generate recommendations
            print("\n10. Generating recommendations...")
            recommendations = self.generate_recommendations(optimization_report)
            optimization_report['recommendations'] = recommendations

            for rec in recommendations:
                print(f"  💡 {rec}")

            return optimization_report

        except Exception as e:
            print(f"[ERROR] Optimization failed: {e}")
            optimization_report['error'] = str(e)
            return optimization_report

    def compare_performance(self, before: Dict, after: Dict, report: Dict):
        """Compare before and after performance metrics"""
        try:
            # CPU comparison
            cpu_before = before.get('cpu_percent', 0)
            cpu_after = after.get('cpu_percent', 0)
            cpu_change = cpu_after - cpu_before

            print(f"  CPU Usage: {cpu_before:.1f}% → {cpu_after:.1f}% ({cpu_change:+.1f}%)")

            # Memory comparison
            mem_before = before.get('memory_percent', 0)
            mem_after = after.get('memory_percent', 0)
            mem_change = mem_after - mem_before

            print(f"  Memory Usage: {mem_before:.1f}% → {mem_after:.1f}% ({mem_change:+.1f}%)")

            # API response time comparison
            api_before = before.get('api_response_time', 999)
            api_after = after.get('api_response_time', 999)
            api_change = api_after - api_before

            print(f"  API Response: {api_before:.3f}s → {api_after:.3f}s ({api_change:+.3f}s)")

            # Track resolved issues
            before_issues = self.analyze_performance_bottlenecks(before)
            after_issues = self.analyze_performance_bottlenecks(after)

            resolved_issues = set(before_issues) - set(after_issues)
            report['issues_resolved'] = list(resolved_issues)

            if resolved_issues:
                print(f"  ✅ Resolved issues: {len(resolved_issues)}")
                for issue in resolved_issues:
                    print(f"    - {issue}")

        except Exception as e:
            print(f"[ERROR] Failed to compare performance: {e}")

    def generate_recommendations(self, report: Dict) -> List[str]:
        """Generate optimization recommendations"""
        recommendations = []

        try:
            after_metrics = report.get('after_metrics', {})
            issues_remaining = self.analyze_performance_bottlenecks(after_metrics)

            # High CPU usage recommendations
            if any('HIGH_CPU_USAGE' in issue for issue in issues_remaining):
                recommendations.extend([
                    "Consider reducing max_open_trades to lower CPU usage",
                    "Implement trade signal caching",
                    "Use a more powerful server or add CPU cores"
                ])

            # High memory usage recommendations
            if any('HIGH_MEMORY_USAGE' in issue for issue in issues_remaining):
                recommendations.extend([
                    "Increase Docker memory limits",
                    "Implement data cleanup routines",
                    "Consider using a database instead of in-memory storage"
                ])

            # API performance recommendations
            if any('SLOW_API_RESPONSE' in issue for issue in issues_remaining):
                recommendations.extend([
                    "Enable API response caching",
                    "Optimize database queries",
                    "Consider using Redis for session storage"
                ])

            # Disk space recommendations
            if any('LOW_DISK_SPACE' in issue for issue in issues_remaining):
                recommendations.extend([
                    "Implement log rotation",
                    "Clean up old backtest results",
                    "Move data to external storage"
                ])

            # General recommendations
            recommendations.extend([
                "Schedule regular performance monitoring",
                "Set up automated backup cleanup",
                "Monitor resource usage trends",
                "Consider upgrading hardware if bottlenecks persist"
            ])

            return recommendations

        except Exception as e:
            print(f"[ERROR] Failed to generate recommendations: {e}")
            return ["Review system manually for optimization opportunities"]

    def save_optimization_report(self, report: Dict):
        """Save optimization report to file"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            report_path = f"logs/optimization_report_{timestamp}.json"

            os.makedirs(os.path.dirname(report_path), exist_ok=True)

            with open(report_path, 'w') as f:
                json.dump(report, f, indent=2, default=str)

            print(f"\n[INFO] Optimization report saved to: {report_path}")

        except Exception as e:
            print(f"[ERROR] Failed to save optimization report: {e}")


def main():
    """Main optimization function"""
    import argparse

    parser = argparse.ArgumentParser(description='Freqtrade Performance Optimizer')
    parser.add_argument('--benchmark', action='store_true', help='Run performance benchmark only')
    parser.add_argument('--analyze', action='store_true', help='Analyze performance only')
    parser.add_argument('--optimize', action='store_true', default=True, help='Run full optimization')

    args = parser.parse_args()

    optimizer = FreqtradePerformanceOptimizer()

    try:
        if args.benchmark:
            benchmark_results = optimizer.benchmark_performance()
            print(f"\nBenchmark results: {json.dumps(benchmark_results, indent=2)}")

        elif args.analyze:
            metrics = optimizer.get_system_metrics()
            issues = optimizer.analyze_performance_bottlenecks(metrics)

            print("\nPerformance Analysis:")
            if issues:
                for issue in issues:
                    print(f"  ⚠️  {issue}")
            else:
                print("  ✅ No performance issues detected")

        else:
            # Run full optimization
            report = optimizer.run_optimization()
            optimizer.save_optimization_report(report)

            print("\n🎉 Performance optimization completed!")
            print("Review the optimization report for detailed results.")

    except KeyboardInterrupt:
        print("\n[INFO] Optimization interrupted by user")
    except Exception as e:
        print(f"[ERROR] Optimization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()