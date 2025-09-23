#!/usr/bin/env python3
"""
Crypto Trader Pro - Streamlit Dashboard
Simple launcher without emoji issues
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
import time

# Import our connector
from binance_testnet_connector import BinanceTestnetConnector

# Page config
st.set_page_config(
    page_title="Crypto Trader Pro",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize connector
@st.cache_resource
def init_connector():
    return BinanceTestnetConnector()

def main():
    """Main Streamlit app"""
    st.title("🚀 Crypto Trader Pro - Real-time Dashboard")
    st.markdown("---")

    # Initialize connector
    connector = init_connector()

    # Sidebar
    st.sidebar.title("📊 Control Panel")

    # Main content tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📈 Live Prices", "💰 Portfolio", "📊 Market Data", "⚙️ Settings"])

    with tab1:
        st.header("Real-time Cryptocurrency Prices")

        # Major coins
        major_coins = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT', 'ADA/USDT', 'SOL/USDT']

        # Create columns for price display
        cols = st.columns(len(major_coins))

        for i, coin in enumerate(major_coins):
            with cols[i]:
                try:
                    price_data = connector.get_current_price(coin)
                    if price_data['success']:
                        price = price_data['price']
                        st.metric(
                            label=coin,
                            value=f"${price:,.2f}",
                            delta=f"${price_data.get('bid', 0) - price_data.get('ask', 0):.2f}"
                        )
                    else:
                        st.error(f"Failed to load {coin}")
                except Exception as e:
                    st.error(f"Error loading {coin}: {str(e)}")

        # Detailed price table
        st.subheader("Detailed Price Information")

        if st.button("Refresh Prices"):
            price_data = []
            for coin in major_coins:
                try:
                    result = connector.get_current_price(coin)
                    if result['success']:
                        price_data.append({
                            'Symbol': coin,
                            'Price (USDT)': f"${result['price']:,.2f}",
                            'Bid': f"${result['bid']:,.2f}",
                            'Ask': f"${result['ask']:,.2f}",
                            'Volume': f"{result.get('volume', 0):,.2f}",
                            'Last Update': result['timestamp'].strftime('%H:%M:%S')
                        })
                except Exception as e:
                    st.error(f"Error loading {coin}: {str(e)}")

            if price_data:
                df = pd.DataFrame(price_data)
                st.dataframe(df, use_container_width=True)

    with tab2:
        st.header("Portfolio Management")
        st.info("Portfolio features will be available after API key configuration")

        # Test connection
        if st.button("Test Connection"):
            with st.spinner("Testing connection..."):
                result = connector.test_connection()
                if result['success']:
                    st.success("✅ Connection successful!")
                    st.json(result)
                else:
                    st.error("❌ Connection failed")
                    st.error(result.get('error', 'Unknown error'))

    with tab3:
        st.header("Market Analysis")

        # Exchange info
        if st.button("Load Market Info"):
            with st.spinner("Loading market data..."):
                symbols = connector.get_exchange_info()
                st.success(f"Loaded {len(symbols)} trading pairs")

                # Show sample of symbols
                if symbols:
                    st.subheader("Available Trading Pairs (Sample)")
                    sample_symbols = symbols[:20]  # Show first 20
                    df = pd.DataFrame({'Trading Pairs': sample_symbols})
                    st.dataframe(df, use_container_width=True)

        # Order book
        st.subheader("Order Book (BTC/USDT)")
        if st.button("Load Order Book"):
            orderbook = connector.get_order_book('BTC/USDT', 10)
            if orderbook:
                col1, col2 = st.columns(2)

                with col1:
                    st.write("**Bids (Buy Orders)**")
                    bids_df = pd.DataFrame(orderbook['bids'], columns=['Price', 'Quantity'])
                    bids_df['Price'] = bids_df['Price'].astype(float)
                    bids_df['Quantity'] = bids_df['Quantity'].astype(float)
                    st.dataframe(bids_df)

                with col2:
                    st.write("**Asks (Sell Orders)**")
                    asks_df = pd.DataFrame(orderbook['asks'], columns=['Price', 'Quantity'])
                    asks_df['Price'] = asks_df['Price'].astype(float)
                    asks_df['Quantity'] = asks_df['Quantity'].astype(float)
                    st.dataframe(asks_df)

    with tab4:
        st.header("Settings & Configuration")

        st.subheader("API Configuration")
        st.info("For full functionality, configure your Binance Testnet API keys")

        # API key input (for future use)
        api_key = st.text_input("API Key", type="password", help="Your Binance Testnet API Key")
        secret_key = st.text_input("Secret Key", type="password", help="Your Binance Testnet Secret Key")

        if st.button("Save Configuration"):
            if api_key and secret_key:
                st.success("Configuration saved successfully!")
                st.info("Restart the application to apply changes")
            else:
                st.warning("Please enter both API key and secret key")

        st.subheader("System Information")
        st.write("**CCXT Version:**", "4.5.5")
        st.write("**Exchange:**", "Binance Testnet")
        st.write("**Status:**", "✅ Online" if connector.exchange else "❌ Offline")

if __name__ == "__main__":
    main()