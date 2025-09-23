#!/usr/bin/env python3
"""
Freqtrade Performance Monitor
Real-time monitoring of Freqtrade performance and system health
"""

import sys
import os
import time
import json
import requests
import psutil
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import warnings
warnings.filterwarnings('ignore')

# Email and Telegram integration
try:
    import smtplib
    from email.mime.text import MimeText
    from email.mime.multipart import MimeMultipart
    EMAIL_AVAILABLE = True
except ImportError:
    EMAIL_AVAILABLE = False

try:
    import telegram
    TELEGRAM_AVAILABLE = True
except ImportError:
    TELEGRAM_AVAILABLE = False


class FreqtradeMonitor:
    """Monitor Freqtrade performance and system health"""

    def __init__(self):
        self.config_path = "config/config.json"
        self.api_url = "http://localhost:8080/api/v1"
        self.db_path = "user_data/monitoring.db"

        # Load configuration
        self.config = self.load_config()

        # Initialize database
        self.init_database()

        # Alert thresholds
        self.thresholds = {
            'max_drawdown_warning': 5.0,      # %
            'max_drawdown_critical': 8.0,     # %
            'min_profit_warning': -2.0,       # %
            'min_profit_critical': -5.0,      # %
            'max_cpu_usage': 80.0,            # %
            'max_memory_usage': 80.0,         # %
            'max_disk_usage': 85.0,           # %
            'api_timeout': 30,                # seconds
            'max_consecutive_losses': 5,
            'min_win_rate': 40.0              # %
        }

        # Alert history (to prevent spam)
        self.alert_history = {}
        self.alert_cooldown = 1800  # 30 minutes

    def load_config(self):
        """Load Freqtrade configuration"""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"[ERROR] Failed to load config: {e}")
            return {}

    def init_database(self):
        """Initialize monitoring database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Performance metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS performance_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    total_profit REAL,
                    daily_profit REAL,
                    total_trades INTEGER,
                    open_trades INTEGER,
                    win_rate REAL,
                    avg_profit_per_trade REAL,
                    max_drawdown REAL,
                    sharpe_ratio REAL,
                    balance REAL,
                    available_balance REAL
                )
            ''')

            # System metrics table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS system_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    cpu_percent REAL,
                    memory_percent REAL,
                    disk_usage_percent REAL,
                    freqtrade_memory_mb REAL,
                    api_response_time REAL,
                    docker_containers_running INTEGER,
                    uptime_hours REAL
                )
            ''')

            # Alerts table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    alert_type TEXT,
                    severity TEXT,
                    message TEXT,
                    resolved BOOLEAN DEFAULT FALSE,
                    acknowledged BOOLEAN DEFAULT FALSE
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[ERROR] Failed to initialize database: {e}")

    def get_freqtrade_status(self) -> Optional[Dict[str, Any]]:
        """Get current Freqtrade status via API"""
        try:
            start_time = time.time()
            response = requests.get(
                f"{self.api_url}/status",
                timeout=self.thresholds['api_timeout']
            )
            api_response_time = time.time() - start_time

            if response.status_code == 200:
                data = response.json()
                data['api_response_time'] = api_response_time
                return data
            else:
                self.log_alert('API_ERROR', 'WARNING', f"API returned status {response.status_code}")
                return None

        except requests.exceptions.Timeout:
            self.log_alert('API_TIMEOUT', 'CRITICAL', f"API timeout after {self.thresholds['api_timeout']}s")
            return None
        except Exception as e:
            self.log_alert('API_CONNECTION', 'CRITICAL', f"Failed to connect to Freqtrade API: {e}")
            return None

    def get_freqtrade_profit(self) -> Optional[Dict[str, Any]]:
        """Get profit information"""
        try:
            response = requests.get(f"{self.api_url}/profit", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get profit data: {e}")
            return None

    def get_freqtrade_performance(self) -> Optional[Dict[str, Any]]:
        """Get performance metrics"""
        try:
            response = requests.get(f"{self.api_url}/performance", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get performance data: {e}")
            return None

    def get_open_trades(self) -> Optional[Dict[str, Any]]:
        """Get currently open trades"""
        try:
            response = requests.get(f"{self.api_url}/trades", timeout=30)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            print(f"[ERROR] Failed to get trades data: {e}")
            return None

    def get_system_metrics(self) -> Dict[str, Any]:
        """Get system resource usage"""
        try:
            # Basic system metrics
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')

            # Docker container check
            docker_containers = 0
            try:
                import docker
                client = docker.from_env()
                containers = client.containers.list()
                docker_containers = len([c for c in containers if 'freqtrade' in c.name])
            except:
                docker_containers = 0

            # Freqtrade process memory
            freqtrade_memory = 0
            for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
                try:
                    if 'freqtrade' in proc.info['name'].lower():
                        freqtrade_memory += proc.info['memory_info'].rss / 1024 / 1024  # MB
                except:
                    continue

            # System uptime
            uptime_seconds = time.time() - psutil.boot_time()
            uptime_hours = uptime_seconds / 3600

            return {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'disk_usage_percent': disk.percent,
                'freqtrade_memory_mb': freqtrade_memory,
                'docker_containers_running': docker_containers,
                'uptime_hours': uptime_hours
            }

        except Exception as e:
            print(f"[ERROR] Failed to get system metrics: {e}")
            return {}

    def analyze_performance(self, status_data: Dict, profit_data: Dict, performance_data: Dict) -> Dict[str, Any]:
        """Analyze performance and detect issues"""
        analysis = {
            'alerts': [],
            'warnings': [],
            'status': 'OK'
        }

        try:
            # Extract key metrics
            total_profit = profit_data.get('profit_total_abs', 0)
            total_profit_pct = profit_data.get('profit_total', 0)
            open_trades = len(status_data.get('open_trades', []))

            # Calculate win rate
            trades = performance_data if performance_data else []
            if trades and len(trades) > 0:
                profitable_trades = len([t for t in trades if t.get('profit', 0) > 0])
                win_rate = (profitable_trades / len(trades)) * 100
            else:
                win_rate = 0

            # Check profit thresholds
            if total_profit_pct <= self.thresholds['min_profit_critical']:
                analysis['alerts'].append(f"CRITICAL: Total profit at {total_profit_pct:.2f}% (below {self.thresholds['min_profit_critical']}%)")
                analysis['status'] = 'CRITICAL'
            elif total_profit_pct <= self.thresholds['min_profit_warning']:
                analysis['warnings'].append(f"WARNING: Total profit at {total_profit_pct:.2f}% (below {self.thresholds['min_profit_warning']}%)")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Check win rate
            if win_rate < self.thresholds['min_win_rate'] and len(trades) >= 10:
                analysis['warnings'].append(f"WARNING: Win rate at {win_rate:.1f}% (below {self.thresholds['min_win_rate']}%)")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Check for too many open trades
            max_open_trades = self.config.get('max_open_trades', 3)
            if open_trades >= max_open_trades:
                analysis['warnings'].append(f"WARNING: Maximum open trades reached ({open_trades}/{max_open_trades})")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Check consecutive losses
            if trades and len(trades) >= 5:
                recent_trades = sorted(trades, key=lambda x: x.get('close_date', ''), reverse=True)[:5]
                consecutive_losses = 0
                for trade in recent_trades:
                    if trade.get('profit', 0) < 0:
                        consecutive_losses += 1
                    else:
                        break

                if consecutive_losses >= self.thresholds['max_consecutive_losses']:
                    analysis['alerts'].append(f"CRITICAL: {consecutive_losses} consecutive losses detected")
                    analysis['status'] = 'CRITICAL'
                elif consecutive_losses >= 3:
                    analysis['warnings'].append(f"WARNING: {consecutive_losses} consecutive losses")
                    if analysis['status'] == 'OK':
                        analysis['status'] = 'WARNING'

            return analysis

        except Exception as e:
            print(f"[ERROR] Failed to analyze performance: {e}")
            return analysis

    def analyze_system_health(self, system_metrics: Dict) -> Dict[str, Any]:
        """Analyze system health"""
        analysis = {
            'alerts': [],
            'warnings': [],
            'status': 'OK'
        }

        try:
            # CPU usage
            cpu_percent = system_metrics.get('cpu_percent', 0)
            if cpu_percent >= self.thresholds['max_cpu_usage']:
                analysis['alerts'].append(f"HIGH CPU USAGE: {cpu_percent:.1f}%")
                analysis['status'] = 'CRITICAL'
            elif cpu_percent >= self.thresholds['max_cpu_usage'] * 0.8:
                analysis['warnings'].append(f"Elevated CPU usage: {cpu_percent:.1f}%")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Memory usage
            memory_percent = system_metrics.get('memory_percent', 0)
            if memory_percent >= self.thresholds['max_memory_usage']:
                analysis['alerts'].append(f"HIGH MEMORY USAGE: {memory_percent:.1f}%")
                analysis['status'] = 'CRITICAL'
            elif memory_percent >= self.thresholds['max_memory_usage'] * 0.8:
                analysis['warnings'].append(f"Elevated memory usage: {memory_percent:.1f}%")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Disk usage
            disk_percent = system_metrics.get('disk_usage_percent', 0)
            if disk_percent >= self.thresholds['max_disk_usage']:
                analysis['alerts'].append(f"HIGH DISK USAGE: {disk_percent:.1f}%")
                analysis['status'] = 'CRITICAL'
            elif disk_percent >= self.thresholds['max_disk_usage'] * 0.8:
                analysis['warnings'].append(f"Elevated disk usage: {disk_percent:.1f}%")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            # Docker containers
            containers_running = system_metrics.get('docker_containers_running', 0)
            if containers_running < 2:  # Should have at least freqtrade + UI
                analysis['warnings'].append(f"Only {containers_running} Freqtrade containers running")
                if analysis['status'] == 'OK':
                    analysis['status'] = 'WARNING'

            return analysis

        except Exception as e:
            print(f"[ERROR] Failed to analyze system health: {e}")
            return analysis

    def log_alert(self, alert_type: str, severity: str, message: str):
        """Log alert to database and send notifications"""
        try:
            # Check alert cooldown
            alert_key = f"{alert_type}_{severity}"
            current_time = datetime.now()

            if alert_key in self.alert_history:
                last_alert_time = self.alert_history[alert_key]
                time_diff = (current_time - last_alert_time).total_seconds()
                if time_diff < self.alert_cooldown:
                    return  # Skip duplicate alert

            # Update alert history
            self.alert_history[alert_key] = current_time

            # Log to database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO alerts (alert_type, severity, message)
                VALUES (?, ?, ?)
            ''', (alert_type, severity, message))
            conn.commit()
            conn.close()

            # Send notifications
            self.send_alert_notification(alert_type, severity, message)

            print(f"[{severity}] {alert_type}: {message}")

        except Exception as e:
            print(f"[ERROR] Failed to log alert: {e}")

    def send_alert_notification(self, alert_type: str, severity: str, message: str):
        """Send alert notifications via configured channels"""
        try:
            subject = f"Freqtrade {severity}: {alert_type}"
            body = f"""
Freqtrade Monitoring Alert

Severity: {severity}
Type: {alert_type}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}

Message: {message}

System: Freqtrade Trading Bot
Host: {os.uname().nodename if hasattr(os, 'uname') else 'Unknown'}

This is an automated alert from the Freqtrade monitoring system.
"""

            # Send email notification (if configured)
            self.send_email_alert(subject, body)

            # Send Telegram notification (if configured)
            self.send_telegram_alert(f"{subject}\n\n{message}")

        except Exception as e:
            print(f"[ERROR] Failed to send notifications: {e}")

    def send_email_alert(self, subject: str, body: str):
        """Send email alert"""
        try:
            if not EMAIL_AVAILABLE:
                return

            # Email configuration (should be loaded from config)
            smtp_config = self.config.get('email', {})
            if not smtp_config.get('enabled', False):
                return

            msg = MimeMultipart()
            msg['From'] = smtp_config.get('from')
            msg['To'] = smtp_config.get('to')
            msg['Subject'] = subject
            msg.attach(MimeText(body, 'plain'))

            server = smtplib.SMTP(smtp_config.get('smtp_server'), smtp_config.get('smtp_port', 587))
            server.starttls()
            server.login(smtp_config.get('username'), smtp_config.get('password'))
            server.send_message(msg)
            server.quit()

        except Exception as e:
            print(f"[ERROR] Failed to send email: {e}")

    def send_telegram_alert(self, message: str):
        """Send Telegram alert"""
        try:
            if not TELEGRAM_AVAILABLE:
                return

            # Telegram configuration
            telegram_config = self.config.get('telegram', {})
            if not telegram_config.get('enabled', False):
                return

            bot = telegram.Bot(token=telegram_config.get('token'))
            bot.send_message(
                chat_id=telegram_config.get('chat_id'),
                text=message,
                parse_mode='Markdown'
            )

        except Exception as e:
            print(f"[ERROR] Failed to send Telegram message: {e}")

    def save_metrics(self, status_data: Dict, profit_data: Dict, system_metrics: Dict):
        """Save metrics to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Performance metrics
            total_profit = profit_data.get('profit_total', 0)
            daily_profit = profit_data.get('profit_today', 0)
            open_trades = len(status_data.get('open_trades', []))

            cursor.execute('''
                INSERT INTO performance_metrics (
                    total_profit, daily_profit, open_trades, balance, available_balance
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                total_profit,
                daily_profit,
                open_trades,
                profit_data.get('starting_balance', 0),
                profit_data.get('available_balance', 0)
            ))

            # System metrics
            cursor.execute('''
                INSERT INTO system_metrics (
                    cpu_percent, memory_percent, disk_usage_percent,
                    freqtrade_memory_mb, api_response_time, docker_containers_running, uptime_hours
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                system_metrics.get('cpu_percent', 0),
                system_metrics.get('memory_percent', 0),
                system_metrics.get('disk_usage_percent', 0),
                system_metrics.get('freqtrade_memory_mb', 0),
                status_data.get('api_response_time', 0),
                system_metrics.get('docker_containers_running', 0),
                system_metrics.get('uptime_hours', 0)
            ))

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[ERROR] Failed to save metrics: {e}")

    def run_monitoring_cycle(self):
        """Run a single monitoring cycle"""
        print(f"[INFO] Starting monitoring cycle at {datetime.now()}")

        # Get Freqtrade data
        status_data = self.get_freqtrade_status()
        profit_data = self.get_freqtrade_profit()
        performance_data = self.get_freqtrade_performance()

        # Get system metrics
        system_metrics = self.get_system_metrics()

        if not status_data:
            self.log_alert('FREQTRADE_DOWN', 'CRITICAL', 'Freqtrade API is not responding')
            return False

        # Analyze performance
        if profit_data:
            perf_analysis = self.analyze_performance(status_data, profit_data, performance_data)

            # Send alerts
            for alert in perf_analysis['alerts']:
                self.log_alert('PERFORMANCE', 'CRITICAL', alert)
            for warning in perf_analysis['warnings']:
                self.log_alert('PERFORMANCE', 'WARNING', warning)

        # Analyze system health
        system_analysis = self.analyze_system_health(system_metrics)

        # Send system alerts
        for alert in system_analysis['alerts']:
            self.log_alert('SYSTEM', 'CRITICAL', alert)
        for warning in system_analysis['warnings']:
            self.log_alert('SYSTEM', 'WARNING', warning)

        # Save metrics
        if profit_data:
            self.save_metrics(status_data, profit_data, system_metrics)

        print(f"[INFO] Monitoring cycle completed")
        return True

    def generate_daily_report(self):
        """Generate daily performance report"""
        try:
            print("[INFO] Generating daily report...")

            # Get today's metrics
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Performance summary
            cursor.execute('''
                SELECT * FROM performance_metrics
                WHERE date(timestamp) = date('now')
                ORDER BY timestamp DESC
                LIMIT 1
            ''')
            latest_perf = cursor.fetchone()

            # System health summary
            cursor.execute('''
                SELECT AVG(cpu_percent), AVG(memory_percent), AVG(disk_usage_percent)
                FROM system_metrics
                WHERE date(timestamp) = date('now')
            ''')
            avg_system = cursor.fetchone()

            # Alert summary
            cursor.execute('''
                SELECT severity, COUNT(*) FROM alerts
                WHERE date(timestamp) = date('now')
                GROUP BY severity
            ''')
            alert_counts = cursor.fetchall()

            conn.close()

            # Create report
            report = f"""
📊 Freqtrade Daily Report - {datetime.now().strftime('%Y-%m-%d')}

💰 Performance:
- Total Profit: {latest_perf[2] if latest_perf else 0:.2f}%
- Daily Profit: {latest_perf[3] if latest_perf else 0:.2f}%
- Open Trades: {latest_perf[5] if latest_perf else 0}

⚙️  System Health:
- Avg CPU: {avg_system[0] if avg_system else 0:.1f}%
- Avg Memory: {avg_system[1] if avg_system else 0:.1f}%
- Avg Disk: {avg_system[2] if avg_system else 0:.1f}%

🚨 Alerts Today:
"""
            for severity, count in alert_counts:
                report += f"- {severity}: {count}\n"

            if not alert_counts:
                report += "- No alerts today ✅\n"

            report += f"\nGenerated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}"

            # Send report
            self.send_email_alert("Freqtrade Daily Report", report)
            self.send_telegram_alert(report)

            print("[INFO] Daily report sent")

        except Exception as e:
            print(f"[ERROR] Failed to generate daily report: {e}")


def main():
    """Main monitoring function"""
    monitor = FreqtradeMonitor()

    # Check if this is a daily report run
    if len(sys.argv) > 1 and sys.argv[1] == '--daily-report':
        monitor.generate_daily_report()
        return

    # Run monitoring cycle
    success = monitor.run_monitoring_cycle()

    if not success:
        print("[ERROR] Monitoring cycle failed")
        sys.exit(1)

    print("[INFO] Monitoring completed successfully")


if __name__ == "__main__":
    main()