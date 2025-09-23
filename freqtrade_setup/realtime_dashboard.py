#!/usr/bin/env python3
"""
Real-time Freqtrade Monitoring Dashboard
Streamlit-based dashboard for real-time monitoring of Freqtrade performance
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import requests
import sqlite3
import json
import time
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')


class FreqtradeDashboard:
    """Real-time Freqtrade monitoring dashboard"""

    def __init__(self):
        self.api_url = "http://localhost:8080/api/v1"
        self.db_path = "user_data/monitoring.db"
        self.refresh_interval = 30  # seconds

    def get_freqtrade_data(self):
        """Fetch current Freqtrade data"""
        try:
            # Get status
            status_response = requests.get(f"{self.api_url}/status", timeout=10)
            status_data = status_response.json() if status_response.status_code == 200 else {}

            # Get profit
            profit_response = requests.get(f"{self.api_url}/profit", timeout=10)
            profit_data = profit_response.json() if profit_response.status_code == 200 else {}

            # Get balance
            balance_response = requests.get(f"{self.api_url}/balance", timeout=10)
            balance_data = balance_response.json() if balance_response.status_code == 200 else {}

            # Get open trades
            trades_response = requests.get(f"{self.api_url}/trades", timeout=10)
            trades_data = trades_response.json() if trades_response.status_code == 200 else []

            # Get performance
            performance_response = requests.get(f"{self.api_url}/performance", timeout=10)
            performance_data = performance_response.json() if performance_response.status_code == 200 else []

            return {
                'status': status_data,
                'profit': profit_data,
                'balance': balance_data,
                'trades': trades_data,
                'performance': performance_data,
                'connected': True
            }

        except Exception as e:
            st.error(f"Failed to connect to Freqtrade API: {e}")
            return {
                'status': {},
                'profit': {},
                'balance': {},
                'trades': [],
                'performance': [],
                'connected': False
            }

    def get_historical_data(self, days=7):
        """Get historical performance data from monitoring database"""
        try:
            conn = sqlite3.connect(self.db_path)

            # Performance metrics
            perf_df = pd.read_sql_query('''
                SELECT * FROM performance_metrics
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp
            '''.format(days), conn)

            # System metrics
            system_df = pd.read_sql_query('''
                SELECT * FROM system_metrics
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp
            '''.format(days), conn)

            # Recent alerts
            alerts_df = pd.read_sql_query('''
                SELECT * FROM alerts
                WHERE timestamp >= datetime('now', '-{} days')
                ORDER BY timestamp DESC
            '''.format(days), conn)

            conn.close()

            return {
                'performance': perf_df,
                'system': system_df,
                'alerts': alerts_df
            }

        except Exception as e:
            st.warning(f"Could not load historical data: {e}")
            return {
                'performance': pd.DataFrame(),
                'system': pd.DataFrame(),
                'alerts': pd.DataFrame()
            }

    def render_header(self, data):
        """Render dashboard header with key metrics"""
        st.title("🚀 Freqtrade Real-time Dashboard")

        # Connection status
        if data['connected']:
            st.success("✅ Connected to Freqtrade API")
        else:
            st.error("❌ Freqtrade API Connection Failed")
            return

        # Key metrics in columns
        col1, col2, col3, col4, col5 = st.columns(5)

        with col1:
            total_profit = data['profit'].get('profit_total', 0)
            st.metric(
                "Total Profit",
                f"{total_profit:.2f}%",
                delta=f"{data['profit'].get('profit_today', 0):.2f}% today"
            )

        with col2:
            balance = data['balance'].get('total', 0)
            st.metric(
                "Balance",
                f"{balance:.2f} USDT",
                delta=f"{data['profit'].get('profit_total_abs', 0):.2f} USDT"
            )

        with col3:
            open_trades = len(data['trades'])
            max_trades = data['status'].get('max_open_trades', 3)
            st.metric(
                "Open Trades",
                f"{open_trades}/{max_trades}",
                delta=f"{((open_trades/max_trades)*100):.0f}% utilization"
            )

        with col4:
            strategy = data['status'].get('strategy', 'Unknown')
            st.metric(
                "Strategy",
                strategy,
                delta="Active" if data['status'].get('state') == 'RUNNING' else "Stopped"
            )

        with col5:
            uptime = data['status'].get('uptime', 0) / 3600  # Convert to hours
            st.metric(
                "Uptime",
                f"{uptime:.1f}h",
                delta="Running" if data['status'].get('state') == 'RUNNING' else "Stopped"
            )

    def render_profit_chart(self, historical_data):
        """Render profit evolution chart"""
        st.subheader("📈 Profit Evolution")

        if historical_data['performance'].empty:
            st.info("No historical data available")
            return

        df = historical_data['performance'].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Create profit chart
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=("Total Profit (%)", "Daily Profit (%)"),
            vertical_spacing=0.1
        )

        # Total profit
        fig.add_trace(
            go.Scatter(
                x=df['timestamp'],
                y=df['total_profit'],
                mode='lines+markers',
                name='Total Profit',
                line=dict(color='green', width=2),
                marker=dict(size=4)
            ),
            row=1, col=1
        )

        # Daily profit
        colors = ['green' if x >= 0 else 'red' for x in df['daily_profit']]
        fig.add_trace(
            go.Bar(
                x=df['timestamp'],
                y=df['daily_profit'],
                name='Daily Profit',
                marker=dict(color=colors)
            ),
            row=2, col=1
        )

        fig.update_layout(
            height=500,
            title_text="Performance Over Time",
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)

    def render_trades_table(self, data):
        """Render current open trades table"""
        st.subheader("💼 Open Trades")

        trades = data['trades']
        if not trades:
            st.info("No open trades")
            return

        # Convert to DataFrame
        trades_df = pd.DataFrame(trades)

        # Format for display
        display_columns = [
            'pair', 'open_date', 'amount', 'open_rate',
            'current_rate', 'profit_pct', 'profit_abs'
        ]

        available_columns = [col for col in display_columns if col in trades_df.columns]
        if available_columns:
            display_df = trades_df[available_columns].copy()

            # Format columns
            if 'open_date' in display_df.columns:
                display_df['open_date'] = pd.to_datetime(display_df['open_date']).dt.strftime('%Y-%m-%d %H:%M')

            if 'profit_pct' in display_df.columns:
                display_df['profit_pct'] = display_df['profit_pct'].apply(lambda x: f"{x:.2f}%")

            if 'profit_abs' in display_df.columns:
                display_df['profit_abs'] = display_df['profit_abs'].apply(lambda x: f"{x:.2f}")

            # Color code profitable vs losing trades
            def highlight_profit(row):
                if 'profit_abs' in row and isinstance(row['profit_abs'], str):
                    try:
                        profit = float(row['profit_abs'])
                        if profit > 0:
                            return ['background-color: #d4edda'] * len(row)
                        elif profit < 0:
                            return ['background-color: #f8d7da'] * len(row)
                    except:
                        pass
                return [''] * len(row)

            styled_df = display_df.style.apply(highlight_profit, axis=1)
            st.dataframe(styled_df, use_container_width=True)

    def render_performance_summary(self, data):
        """Render performance summary"""
        st.subheader("📊 Performance Summary")

        performance = data['performance']
        if not performance:
            st.info("No performance data available")
            return

        # Create performance metrics
        col1, col2 = st.columns(2)

        with col1:
            st.write("**Top Performing Pairs:**")
            top_pairs = sorted(performance, key=lambda x: x.get('profit', 0), reverse=True)[:5]

            for i, pair_data in enumerate(top_pairs, 1):
                pair = pair_data.get('pair', 'Unknown')
                profit = pair_data.get('profit', 0)
                count = pair_data.get('count', 0)
                st.write(f"{i}. {pair}: {profit:.2f}% ({count} trades)")

        with col2:
            st.write("**Trading Statistics:**")
            total_trades = sum(p.get('count', 0) for p in performance)
            profitable_pairs = len([p for p in performance if p.get('profit', 0) > 0])
            total_pairs = len(performance)

            st.write(f"Total Trades: {total_trades}")
            st.write(f"Profitable Pairs: {profitable_pairs}/{total_pairs}")
            if total_pairs > 0:
                win_rate = (profitable_pairs / total_pairs) * 100
                st.write(f"Pair Win Rate: {win_rate:.1f}%")

    def render_system_health(self, historical_data):
        """Render system health metrics"""
        st.subheader("⚙️ System Health")

        if historical_data['system'].empty:
            st.info("No system metrics available")
            return

        df = historical_data['system'].copy()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        # Get latest metrics
        latest = df.iloc[-1] if not df.empty else {}

        col1, col2, col3 = st.columns(3)

        with col1:
            cpu_usage = latest.get('cpu_percent', 0)
            color = 'red' if cpu_usage > 80 else 'orange' if cpu_usage > 60 else 'green'
            st.metric("CPU Usage", f"{cpu_usage:.1f}%")

        with col2:
            memory_usage = latest.get('memory_percent', 0)
            color = 'red' if memory_usage > 80 else 'orange' if memory_usage > 60 else 'green'
            st.metric("Memory Usage", f"{memory_usage:.1f}%")

        with col3:
            disk_usage = latest.get('disk_usage_percent', 0)
            color = 'red' if disk_usage > 85 else 'orange' if disk_usage > 70 else 'green'
            st.metric("Disk Usage", f"{disk_usage:.1f}%")

        # System metrics chart
        if len(df) > 1:
            fig = go.Figure()

            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['cpu_percent'],
                mode='lines',
                name='CPU %',
                line=dict(color='blue')
            ))

            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['memory_percent'],
                mode='lines',
                name='Memory %',
                line=dict(color='red')
            ))

            fig.add_trace(go.Scatter(
                x=df['timestamp'],
                y=df['disk_usage_percent'],
                mode='lines',
                name='Disk %',
                line=dict(color='green')
            ))

            fig.update_layout(
                title="System Resource Usage",
                xaxis_title="Time",
                yaxis_title="Usage (%)",
                height=300
            )

            st.plotly_chart(fig, use_container_width=True)

    def render_alerts(self, historical_data):
        """Render recent alerts"""
        st.subheader("🚨 Recent Alerts")

        alerts_df = historical_data['alerts']
        if alerts_df.empty:
            st.success("No recent alerts")
            return

        # Display recent alerts
        for _, alert in alerts_df.head(10).iterrows():
            severity = alert['severity']
            message = alert['message']
            timestamp = alert['timestamp']

            if severity == 'CRITICAL':
                st.error(f"🔴 **{severity}** - {timestamp}\n\n{message}")
            elif severity == 'WARNING':
                st.warning(f"🟡 **{severity}** - {timestamp}\n\n{message}")
            else:
                st.info(f"🔵 **{severity}** - {timestamp}\n\n{message}")

    def render_configuration(self, data):
        """Render current configuration"""
        with st.expander("⚙️ Configuration"):
            status = data['status']

            col1, col2 = st.columns(2)

            with col1:
                st.write("**Trading Configuration:**")
                st.write(f"Strategy: {status.get('strategy', 'Unknown')}")
                st.write(f"Max Open Trades: {status.get('max_open_trades', 'Unknown')}")
                st.write(f"Stake Amount: {status.get('stake_amount', 'Unknown')}")
                st.write(f"Dry Run: {status.get('dry_run', 'Unknown')}")

            with col2:
                st.write("**Exchange Configuration:**")
                st.write(f"Exchange: {status.get('exchange', 'Unknown')}")
                st.write(f"Trading Mode: {status.get('trading_mode', 'Unknown')}")
                st.write(f"State: {status.get('state', 'Unknown')}")

    def run_dashboard(self):
        """Main dashboard function"""
        st.set_page_config(
            page_title="Freqtrade Dashboard",
            page_icon="🚀",
            layout="wide",
            initial_sidebar_state="collapsed"
        )

        # Auto-refresh
        if st.button("🔄 Refresh"):
            st.experimental_rerun()

        # Get current data
        current_data = self.get_freqtrade_data()

        # Get historical data
        historical_data = self.get_historical_data(days=7)

        # Render sections
        self.render_header(current_data)

        st.divider()

        # Main content in tabs
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📈 Performance", "💼 Trades", "⚙️ System", "🚨 Alerts", "⚙️ Config"
        ])

        with tab1:
            self.render_profit_chart(historical_data)
            self.render_performance_summary(current_data)

        with tab2:
            self.render_trades_table(current_data)

        with tab3:
            self.render_system_health(historical_data)

        with tab4:
            self.render_alerts(historical_data)

        with tab5:
            self.render_configuration(current_data)

        # Auto-refresh footer
        st.divider()
        st.caption(f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Auto-refresh: {self.refresh_interval}s")

        # Auto-refresh mechanism
        time.sleep(self.refresh_interval)
        st.experimental_rerun()


def main():
    """Main function"""
    dashboard = FreqtradeDashboard()
    dashboard.run_dashboard()


if __name__ == "__main__":
    main()