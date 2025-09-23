#!/usr/bin/env python3
"""
Integration Bridge between Freqtrade and Crypto Trader Pro
Connects Freqtrade with existing notification and monitoring systems
"""

import sys
import os
import time
import json
import requests
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import asyncio
import aiohttp
from threading import Thread
import warnings
warnings.filterwarnings('ignore')

# FastAPI for web interface
try:
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    import uvicorn
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False

# Telegram and Email integration
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


class FreqtradeIntegrationBridge:
    """Bridge between Freqtrade and existing Crypto Trader Pro system"""

    def __init__(self):
        self.freqtrade_api = "http://localhost:8080/api/v1"
        self.crypto_trader_api = "http://localhost:8501"
        self.bridge_port = 8082

        # Database for integration tracking
        self.db_path = "user_data/integration.db"
        self.init_database()

        # Load configuration
        self.config = self.load_config()

        # Notification settings
        self.email_config = self.config.get('email', {})
        self.telegram_config = self.config.get('telegram', {})

        # State tracking
        self.last_trade_count = 0
        self.last_balance = 0.0
        self.last_profit = 0.0
        self.notification_cooldown = {}

        # FastAPI app
        if FASTAPI_AVAILABLE:
            self.app = FastAPI(title="Freqtrade Integration Bridge")
            self.setup_api_routes()

    def load_config(self):
        """Load configuration from multiple sources"""
        try:
            # Try to load Freqtrade config
            with open("config/config.json", 'r') as f:
                freqtrade_config = json.load(f)

            # Try to load crypto-trader config
            crypto_trader_config = {}
            try:
                with open("../config.json", 'r') as f:
                    crypto_trader_config = json.load(f)
            except:
                pass

            # Merge configurations
            config = {
                'freqtrade': freqtrade_config,
                'crypto_trader': crypto_trader_config,
                'email': freqtrade_config.get('email', crypto_trader_config.get('email', {})),
                'telegram': freqtrade_config.get('telegram', crypto_trader_config.get('telegram', {}))
            }

            return config

        except Exception as e:
            print(f"[ERROR] Failed to load configuration: {e}")
            return {}

    def init_database(self):
        """Initialize integration database"""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # Integration events table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS integration_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT,
                    source TEXT,
                    data TEXT,
                    processed BOOLEAN DEFAULT FALSE
                )
            ''')

            # Notification log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    notification_type TEXT,
                    channel TEXT,
                    subject TEXT,
                    message TEXT,
                    success BOOLEAN,
                    error_message TEXT
                )
            ''')

            # Sync status table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sync_status (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    freqtrade_status TEXT,
                    crypto_trader_status TEXT,
                    sync_issues TEXT
                )
            ''')

            conn.commit()
            conn.close()

        except Exception as e:
            print(f"[ERROR] Failed to initialize database: {e}")

    def setup_api_routes(self):
        """Setup FastAPI routes for integration API"""
        if not FASTAPI_AVAILABLE:
            return

        # Enable CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.get("/")
        async def root():
            return {"status": "Freqtrade Integration Bridge", "version": "1.0"}

        @self.app.get("/status")
        async def get_status():
            """Get integration bridge status"""
            return {
                "freqtrade_connected": await self.check_freqtrade_connection(),
                "crypto_trader_connected": await self.check_crypto_trader_connection(),
                "notifications_enabled": self.email_config.get('enabled', False) or self.telegram_config.get('enabled', False),
                "last_sync": datetime.now().isoformat()
            }

        @self.app.get("/sync")
        async def sync_data():
            """Manually trigger data synchronization"""
            try:
                await self.sync_with_crypto_trader()
                return {"status": "success", "message": "Data synchronization completed"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.post("/notify")
        async def send_notification(notification: dict):
            """Send custom notification"""
            try:
                await self.send_notification(
                    notification.get('type', 'INFO'),
                    notification.get('subject', 'Manual Notification'),
                    notification.get('message', '')
                )
                return {"status": "success", "message": "Notification sent"}
            except Exception as e:
                raise HTTPException(status_code=500, detail=str(e))

    async def check_freqtrade_connection(self) -> bool:
        """Check Freqtrade API connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.freqtrade_api}/status", timeout=10) as response:
                    return response.status == 200
        except:
            return False

    async def check_crypto_trader_connection(self) -> bool:
        """Check Crypto Trader Pro connection"""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f"{self.crypto_trader_api}/health", timeout=10) as response:
                    return response.status == 200
        except:
            return False

    async def get_freqtrade_data(self) -> Dict[str, Any]:
        """Get current Freqtrade data"""
        try:
            async with aiohttp.ClientSession() as session:
                # Get multiple endpoints in parallel
                tasks = [
                    session.get(f"{self.freqtrade_api}/status"),
                    session.get(f"{self.freqtrade_api}/profit"),
                    session.get(f"{self.freqtrade_api}/balance"),
                    session.get(f"{self.freqtrade_api}/trades"),
                ]

                responses = await asyncio.gather(*tasks, return_exceptions=True)

                data = {}
                if not isinstance(responses[0], Exception) and responses[0].status == 200:
                    data['status'] = await responses[0].json()

                if not isinstance(responses[1], Exception) and responses[1].status == 200:
                    data['profit'] = await responses[1].json()

                if not isinstance(responses[2], Exception) and responses[2].status == 200:
                    data['balance'] = await responses[2].json()

                if not isinstance(responses[3], Exception) and responses[3].status == 200:
                    data['trades'] = await responses[3].json()

                return data

        except Exception as e:
            print(f"[ERROR] Failed to get Freqtrade data: {e}")
            return {}

    async def sync_with_crypto_trader(self):
        """Synchronize Freqtrade data with Crypto Trader Pro"""
        try:
            # Get Freqtrade data
            freqtrade_data = await self.get_freqtrade_data()

            if not freqtrade_data:
                return False

            # Prepare data for Crypto Trader Pro format
            sync_data = {
                'timestamp': datetime.now().isoformat(),
                'source': 'freqtrade',
                'performance': {
                    'total_profit': freqtrade_data.get('profit', {}).get('profit_total', 0),
                    'daily_profit': freqtrade_data.get('profit', {}).get('profit_today', 0),
                    'balance': freqtrade_data.get('balance', {}).get('total', 0),
                    'open_trades': len(freqtrade_data.get('trades', [])),
                    'status': freqtrade_data.get('status', {}).get('state', 'UNKNOWN')
                }
            }

            # Log integration event
            self.log_integration_event('DATA_SYNC', 'freqtrade', json.dumps(sync_data))

            # Send to Crypto Trader Pro (if API available)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.crypto_trader_api}/api/external/freqtrade",
                        json=sync_data,
                        timeout=10
                    ) as response:
                        if response.status == 200:
                            print("[INFO] Data synchronized with Crypto Trader Pro")
                        else:
                            print(f"[WARN] Crypto Trader Pro API returned {response.status}")
            except Exception as e:
                print(f"[WARN] Could not sync with Crypto Trader Pro: {e}")

            return True

        except Exception as e:
            print(f"[ERROR] Failed to sync data: {e}")
            return False

    def log_integration_event(self, event_type: str, source: str, data: str):
        """Log integration event to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO integration_events (event_type, source, data)
                VALUES (?, ?, ?)
            ''', (event_type, source, data))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ERROR] Failed to log integration event: {e}")

    async def monitor_trades(self):
        """Monitor for new trades and send notifications"""
        try:
            freqtrade_data = await self.get_freqtrade_data()

            if not freqtrade_data:
                return

            # Check for new trades
            current_trade_count = len(freqtrade_data.get('trades', []))
            current_balance = freqtrade_data.get('balance', {}).get('total', 0)
            current_profit = freqtrade_data.get('profit', {}).get('profit_total', 0)

            # New trade opened
            if current_trade_count > self.last_trade_count:
                await self.send_notification(
                    'TRADE_OPENED',
                    'New Trade Opened',
                    f"Freqtrade opened a new trade. Total open trades: {current_trade_count}"
                )

            # Trade closed (trade count decreased)
            elif current_trade_count < self.last_trade_count:
                profit_change = current_profit - self.last_profit
                await self.send_notification(
                    'TRADE_CLOSED',
                    'Trade Closed',
                    f"Freqtrade closed a trade. Profit change: {profit_change:.2f}%\nTotal profit: {current_profit:.2f}%"
                )

            # Significant profit change
            profit_change = abs(current_profit - self.last_profit)
            if profit_change >= 1.0:  # 1% change threshold
                notification_type = 'PROFIT_GAIN' if current_profit > self.last_profit else 'PROFIT_LOSS'
                await self.send_notification(
                    notification_type,
                    f'Significant {"Gain" if current_profit > self.last_profit else "Loss"}',
                    f"Profit changed by {profit_change:.2f}%\nCurrent total profit: {current_profit:.2f}%"
                )

            # Update state
            self.last_trade_count = current_trade_count
            self.last_balance = current_balance
            self.last_profit = current_profit

        except Exception as e:
            print(f"[ERROR] Failed to monitor trades: {e}")

    async def send_notification(self, notification_type: str, subject: str, message: str):
        """Send notification via configured channels"""
        try:
            # Check cooldown
            cooldown_key = f"{notification_type}_{subject}"
            current_time = datetime.now()

            if cooldown_key in self.notification_cooldown:
                last_sent = self.notification_cooldown[cooldown_key]
                if (current_time - last_sent).total_seconds() < 300:  # 5 minutes cooldown
                    return

            self.notification_cooldown[cooldown_key] = current_time

            # Prepare message
            full_message = f"""
🤖 Freqtrade Notification

Type: {notification_type}
Time: {current_time.strftime('%Y-%m-%d %H:%M:%S UTC')}

{message}

---
Freqtrade Integration Bridge
"""

            # Send email
            if self.email_config.get('enabled', False):
                await self.send_email_notification(subject, full_message)

            # Send Telegram
            if self.telegram_config.get('enabled', False):
                await self.send_telegram_notification(f"*{subject}*\n\n{message}")

            # Log notification
            self.log_notification(notification_type, 'email,telegram', subject, message, True, None)

        except Exception as e:
            print(f"[ERROR] Failed to send notification: {e}")
            self.log_notification(notification_type, 'email,telegram', subject, message, False, str(e))

    async def send_email_notification(self, subject: str, message: str):
        """Send email notification"""
        try:
            if not EMAIL_AVAILABLE or not self.email_config.get('enabled', False):
                return

            msg = MimeMultipart()
            msg['From'] = self.email_config.get('from')
            msg['To'] = self.email_config.get('to')
            msg['Subject'] = f"[Freqtrade] {subject}"
            msg.attach(MimeText(message, 'plain'))

            # Run in thread to avoid blocking
            def send_email():
                try:
                    server = smtplib.SMTP(self.email_config.get('smtp_server'), self.email_config.get('smtp_port', 587))
                    server.starttls()
                    server.login(self.email_config.get('username'), self.email_config.get('password'))
                    server.send_message(msg)
                    server.quit()
                except Exception as e:
                    print(f"[ERROR] Failed to send email: {e}")

            thread = Thread(target=send_email)
            thread.start()

        except Exception as e:
            print(f"[ERROR] Email notification error: {e}")

    async def send_telegram_notification(self, message: str):
        """Send Telegram notification"""
        try:
            if not TELEGRAM_AVAILABLE or not self.telegram_config.get('enabled', False):
                return

            # Run in thread to avoid blocking
            def send_telegram():
                try:
                    bot = telegram.Bot(token=self.telegram_config.get('token'))
                    bot.send_message(
                        chat_id=self.telegram_config.get('chat_id'),
                        text=message,
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to send Telegram: {e}")

            thread = Thread(target=send_telegram)
            thread.start()

        except Exception as e:
            print(f"[ERROR] Telegram notification error: {e}")

    def log_notification(self, notification_type: str, channel: str, subject: str, message: str, success: bool, error: str):
        """Log notification to database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO notifications (notification_type, channel, subject, message, success, error_message)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (notification_type, channel, subject, message, success, error))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"[ERROR] Failed to log notification: {e}")

    async def run_monitoring_loop(self):
        """Main monitoring loop"""
        print("[INFO] Starting Freqtrade integration monitoring...")

        while True:
            try:
                # Monitor trades
                await self.monitor_trades()

                # Sync data
                await self.sync_with_crypto_trader()

                # Wait before next cycle
                await asyncio.sleep(60)  # 1 minute interval

            except Exception as e:
                print(f"[ERROR] Monitoring loop error: {e}")
                await asyncio.sleep(30)  # Wait 30 seconds on error

    def start_api_server(self):
        """Start FastAPI server"""
        if not FASTAPI_AVAILABLE:
            print("[WARN] FastAPI not available. API server disabled.")
            return

        try:
            config = uvicorn.Config(
                app=self.app,
                host="0.0.0.0",
                port=self.bridge_port,
                log_level="info"
            )
            server = uvicorn.Server(config)

            # Run server in thread
            def run_server():
                asyncio.run(server.serve())

            server_thread = Thread(target=run_server)
            server_thread.daemon = True
            server_thread.start()

            print(f"[INFO] Integration Bridge API started on port {self.bridge_port}")

        except Exception as e:
            print(f"[ERROR] Failed to start API server: {e}")

    async def run(self):
        """Main run function"""
        print("[INFO] Starting Freqtrade Integration Bridge...")

        # Start API server
        self.start_api_server()

        # Wait a moment for server to start
        await asyncio.sleep(2)

        # Send startup notification
        await self.send_notification(
            'SYSTEM_STARTUP',
            'Freqtrade Integration Bridge Started',
            'The integration bridge between Freqtrade and Crypto Trader Pro has started successfully.'
        )

        # Run monitoring loop
        await self.run_monitoring_loop()


def main():
    """Main function"""
    bridge = FreqtradeIntegrationBridge()

    try:
        asyncio.run(bridge.run())
    except KeyboardInterrupt:
        print("\n[INFO] Integration bridge stopped by user")
    except Exception as e:
        print(f"[ERROR] Integration bridge failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()