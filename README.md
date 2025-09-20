# Crypto Trader Pro

A professional cryptocurrency trading bot infrastructure with advanced data collection, arbitrage detection, and risk management capabilities. Built with Python for educational purposes and algorithmic trading research.

**⚠️ IMPORTANT DISCLAIMER: This software is for educational and research purposes only. Cryptocurrency trading involves substantial risk of loss. Always test thoroughly on testnets before any live trading. Never trade with funds you cannot afford to lose.**

## Project Structure

```
crypto-trader-pro/
├── data/                    # Market data storage and management
│   ├── __init__.py         # Data module initialization
│   ├── database.py         # SQLite database management
│   ├── collector.py        # Real-time data collection system
│   └── scheduler.py        # Intelligent scheduling system
├── strategies/              # Trading strategy modules (future)
├── backtesting/            # Backtesting system and analysis (future)
├── live_trading/           # Live trading execution modules (future)
├── utils/                  # Utility functions and helpers
│   ├── __init__.py         # Utils module initialization
│   ├── exceptions.py       # Custom exception handling system
│   ├── market_data.py      # Advanced market data collection with rate limiting
│   ├── arbitrage_scanner.py # Multi-exchange arbitrage opportunity detection
│   └── validation_helpers.py # Input validation and sanitization
├── config/                 # Configuration files
│   ├── __init__.py         # Config module initialization
│   ├── config.json         # Trading parameters and settings
│   ├── logging_config.py   # Advanced logging configuration
│   └── .env.template       # Environment variables template
├── logs/                   # Log files (gitignored)
├── CLAUDE.md              # Development guidelines and coding standards
├── README.md
├── requirements.txt       # Python dependencies
├── main.py                # Main application runner with CLI interface
├── test_market_data.py    # Market data API test suite
├── test_data_collection.py # Data collection integration tests
├── final_integration_test.py # Complete system integration test suite
└── .gitignore
```

## Features

### ✅ Implemented (Core Infrastructure Complete)
- **🔄 Advanced Market Data Collection**: Binance API with advanced rate limiting and burst protection
- **🔍 Multi-Exchange Arbitrage Scanner**: Real-time opportunity detection across Binance, Coinbase, Kraken
- **🗄️ Professional Database Management**: SQLite with connection pooling, transactions, and auto-optimization
- **📡 Real-time Data Collection**: Multi-threaded collection with intelligent scheduling and gap filling
- **⏰ Market-Aware Scheduling**: Dynamic frequency adjustment based on market conditions
- **🛡️ Bulletproof Error Handling**: Custom exception system with recursion-safe retry logic
- **📊 Comprehensive Data Validation**: Flexible validation for production and testing environments
- **⚡ Advanced Performance Features**: Multi-window rate limiting, TTL caching, resource monitoring
- **🔍 Professional Logging System**: Multi-level logging with rotation and specialized loggers
- **⚙️ Complete Configuration Management**: JSON config + environment variables + dynamic adjustment
- **🧪 Comprehensive Testing Framework**: 22+ tests across 6 categories with system readiness scoring
- **🔐 Enterprise Security**: API key management, input sanitization, comprehensive .gitignore
- **📦 Production-Ready Package**: Complete Python package with proper imports and CLI interface
- **🖥️ CLI Management Interface**: Full application runner with real-time dashboard and graceful shutdown

### 🔨 Core Components

#### Database Management (`data/database.py`)
- **CryptoDatabaseManager**: Complete SQLite database management
- **Connection Pooling**: Optimized database connections (max 5)
- **Transaction Safety**: Atomic operations with rollback support
- **Data Integrity**: UNIQUE constraints and validation checks
- **Auto-cleanup**: Scheduled old data removal and optimization
- **Backup System**: Automated database backup functionality

#### Real-time Data Collection (`data/collector.py`)
- **RealTimeDataCollector**: Multi-threaded data collection orchestrator
- **Parallel Processing**: ThreadPoolExecutor for concurrent symbol collection
- **Gap Detection**: Automatic missing data identification and filling
- **Performance Tracking**: Real-time statistics and success rates
- **Memory Management**: Resource monitoring and usage optimization
- **Error Recovery**: Consecutive failure tracking and backoff strategies

#### Intelligent Scheduling (`data/scheduler.py`)
- **DataCollectionScheduler**: Market-aware task scheduling system
- **Schedule Management**:
  - 1-minute data: Every 1 minute
  - 5-minute data: Every 5 minutes
  - 15-minute data: Every 15 minutes
  - Real-time prices: Every 30 seconds
  - Maintenance: Daily at midnight
- **Resource Monitoring**: CPU, memory, and disk usage tracking
- **Market Hours**: Reduced activity during low-volume periods
- **Dynamic Adjustment**: Frequency scaling based on market conditions

#### Advanced Market Data System (`utils/market_data.py`)
- **MarketDataCollector**: Professional-grade Binance API interaction
- **Advanced Rate Limiting**: Multi-window control (per second + per minute) with burst protection
- **Recursion-Safe Retry Logic**: Loop-based retries with exponential backoff, zero recursion risk
- **Intelligent Caching**: TTL-based caching with performance statistics and hit rate monitoring
- **Dynamic Rate Configuration**: Runtime adjustment of API limits for different exchange profiles
- **Data Normalization**: Handles missing fields, alternative names, and exchange-specific formats
- **Comprehensive Validation**: Pre-flight checks with strict/lenient modes for production/testing

#### Multi-Exchange Arbitrage Scanner (`utils/arbitrage_scanner.py`)
- **ArbitrageScanner**: Real-time opportunity detection across multiple exchanges
- **Multi-Exchange Support**: Binance, Coinbase, Kraken with unified price comparison
- **Fee-Inclusive Calculations**: Real profit calculations including maker/taker fees
- **Risk Assessment**: Automatic risk level evaluation (low/medium/high)
- **Execution Time Estimation**: Realistic trade completion time predictions
- **Concurrent Price Fetching**: ThreadPoolExecutor for efficient multi-exchange data collection
- **Profit Filtering**: Configurable minimum profit thresholds (default: 0.5%+)

#### Exception Handling (`utils/exceptions.py`)
```python
# 10+ Custom Exception Types
- APIConnectionError      # Network/connection issues
- InvalidSymbolError      # Wrong trading symbols
- RateLimitError         # API call limits exceeded
- DataValidationError    # Invalid input parameters
- NetworkTimeoutError    # Request timeouts
- TradingError          # Order placement failures
- RiskManagementError   # Risk limit violations
```

#### Validation System (`utils/validation_helpers.py`)
- Symbol format validation (BASE/QUOTE)
- Price/amount validation with sanity checks
- OHLCV candlestick data integrity validation
- Orderbook structure validation
- Input sanitization to prevent injection attacks

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd crypto-trader-pro
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration**
   ```bash
   # Copy configuration template
   cp config/config.json.example config/config.json

   # Copy environment template
   cp .env.template .env

   # Edit .env with your API keys (TESTNET ONLY initially!)
   ```

4. **⚠️ SECURITY SETUP - CRITICAL**
   - **NEVER use live API keys initially**
   - Start with Binance testnet: https://testnet.binance.vision/
   - Set `TRADING_MODE=testnet` in .env
   - Verify .env is in .gitignore (it should be)
   - Only use small amounts when moving to live trading

## Quick Start

### 1. Test Market Data Connection
```bash
python test_market_data.py
```
Expected output: 15 tests with colored success/failure indicators

### 2. Test Data Collection System
```bash
python test_data_collection.py
```
Expected output: 10 integration tests with database verification and performance metrics

### 3. Run Complete System Integration Test
```bash
python final_integration_test.py
```
Expected output: 22+ comprehensive tests across 6 categories with system readiness scoring (0-100%)

### 4. Start the Full Application
```bash
python main.py
```
CLI interface with multiple operation modes:
- Real-time data collection dashboard
- System diagnostics and monitoring
- Interactive trading console
- Arbitrage opportunity scanner
- Database management interface

### 5. Basic Usage Example
```python
from utils.market_data import MarketDataCollector

# Initialize collector (testnet by default)
collector = MarketDataCollector(testnet=True)

# Test connection
if collector.test_connection():
    print("✅ Connected to Binance API")

# Get current Bitcoin price
price = collector.get_current_price("BTC/USDT")
print(f"💰 BTC Price: ${price:,.2f}")

# Get 24h statistics
ticker = collector.get_24h_ticker("BTC/USDT")
print(f"📈 24h Change: {ticker['percentage']:.2f}%")

# Get recent candlestick data
candles = collector.get_klines("BTC/USDT", interval="5m", limit=100)
print(f"📊 Retrieved {len(candles)} 5-minute candles")
```

### 6. Arbitrage Scanner Example
```python
from utils.arbitrage_scanner import ArbitrageScanner

# Initialize arbitrage scanner
scanner = ArbitrageScanner(
    exchanges=['binance', 'coinbase', 'kraken'],
    min_profit_threshold=0.5,  # 0.5% minimum profit
    testnet=True
)

# Scan for arbitrage opportunities
symbols = ['BTC/USDT', 'ETH/USDT', 'BNB/USDT']
opportunities = scanner.scan_arbitrage_opportunities(symbols)

# Display profitable opportunities
for opp in opportunities:
    print(f"💰 {opp['symbol']}: Buy on {opp['buy_exchange']} "
          f"at ${opp['buy_price']}, sell on {opp['sell_exchange']} "
          f"at ${opp['sell_price']} = {opp['net_profit_percent']:.2f}% profit")
```

## Main Application (`main.py`)

The main application provides a comprehensive CLI interface for managing the entire crypto trading system:

### Application Modes
```bash
python main.py
```

**Available Operations:**
1. **🔄 Real-time Data Collection**: Start/stop continuous market data collection
2. **📊 System Diagnostics**: Health checks, performance metrics, resource monitoring
3. **💰 Interactive Trading Console**: Manual trading interface (future)
4. **🔍 Arbitrage Scanner**: Real-time arbitrage opportunity detection
5. **🗄️ Database Management**: Backup, optimization, maintenance operations
6. **⚙️ Configuration Editor**: Runtime configuration adjustment

### Real-time Dashboard Features
- **Live Market Data**: Current prices, 24h changes, volume statistics
- **System Health**: Database status, API connectivity, resource usage
- **Performance Metrics**: Cache hit rates, API call statistics, execution times
- **Active Schedules**: Next collection times, job status, failure tracking
- **Arbitrage Opportunities**: Live profit opportunities across exchanges

### Graceful Shutdown
- **CTRL+C Handling**: Clean shutdown with resource cleanup
- **Database Safety**: Ensures all transactions complete before exit
- **Thread Management**: Proper cleanup of background tasks and connections

## Configuration

### Main Configuration (`config/config.json`)
```json
{
  "exchange": {
    "name": "binance",
    "testnet": true
  },
  "trading": {
    "max_risk_per_trade": 0.02,
    "daily_loss_limit": 0.03,
    "currencies": ["BTC/USDT", "ETH/USDT", "BNB/USDT"]
  },
  "strategy": {
    "rsi_period": 14,
    "rsi_buy_threshold": 30,
    "rsi_sell_threshold": 70
  }
}
```

### Environment Variables (`.env`)
```bash
# API Keys (keep secret!)
BINANCE_API_KEY=your_api_key_here
BINANCE_API_SECRET=your_secret_here

# Telegram Notifications
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

# Trading Settings
TESTNET_MODE=true
MAX_POSITIONS=3
```

## Development Guidelines (CLAUDE.md)

Our development follows strict guidelines for professional cryptocurrency trading:

### Trading Strategy
- **Target**: 5-10% monthly returns
- **Risk Management**: Max 1-2% loss per trade
- **Approach**: RSI-based day trading + arbitrage

### Code Standards
- **Functions**: snake_case
- **Classes**: PascalCase
- **Constants**: UPPER_CASE
- **Documentation**: All functions must have docstrings
- **Error Handling**: Comprehensive exception handling required

## Testing

### Run Test Suites
```bash
# Market data API tests (15 scenarios)
python test_market_data.py

# Data collection integration tests (10 scenarios)
python test_data_collection.py

# Complete system integration test (22+ scenarios)
python final_integration_test.py
```

### Test Coverage

#### Market Data Tests (`test_market_data.py`)
- ✅ API connection testing (success/failure scenarios)
- ✅ Price data retrieval (BTC/USDT, ETH/USDT)
- ✅ Invalid symbol error handling
- ✅ 24-hour ticker data validation
- ✅ Orderbook structure verification
- ✅ Candlestick data integrity
- ✅ Cache performance testing
- ✅ Rate limiting validation
- ✅ Batch symbol processing
- ✅ Edge case validation testing

#### Data Collection Tests (`test_data_collection.py`)
- ✅ Database initialization and schema validation
- ✅ Real-time data collection with ThreadPoolExecutor
- ✅ Data validation and integrity checks
- ✅ Gap detection and missing data handling
- ✅ Performance metrics and benchmarking
- ✅ Memory usage monitoring and optimization
- ✅ Intelligent scheduling system testing
- ✅ Error recovery and consecutive failure tracking
- ✅ Resource monitoring (CPU, memory, disk usage)
- ✅ Complete integration pipeline testing

#### Complete Integration Tests (`final_integration_test.py`)
- ✅ **System Initialization** (6 tests): Configuration, logging, database setup
- ✅ **Market Data Collection** (4 tests): API connections, data retrieval, validation
- ✅ **Data Storage & Integrity** (4 tests): Database operations, validation, persistence
- ✅ **Real-time Collection** (3 tests): Multi-threaded collection, scheduling, gap filling
- ✅ **Performance & Resource** (3 tests): Rate limiting, caching, resource monitoring
- ✅ **System Integration** (2+ tests): End-to-end pipeline, configuration management
- 🎯 **System Readiness Score**: Overall system health and readiness percentage

### Performance Metrics
- **Individual Test Execution**: ~3-5 seconds per test suite
- **Complete Integration Test**: ~15-30 seconds for all 22+ tests
- **Cache Performance**: 5-10x speedup on cache hits
- **Rate Limiting**: Advanced multi-window control (10/second + 600/minute)
- **API Compliance**: Burst protection with automatic call distribution
- **Memory Usage**: <100MB for typical operation
- **System Readiness**: Automated scoring for production deployment

## Logging

### Log Files (`logs/` directory)
```
crypto_trader.log    # All activities (DEBUG+)
trading.log         # Trading-specific logs (INFO+)
errors.log          # Errors only (ERROR+)
backtesting.log     # Backtesting results
```

### Log Levels
- **DEBUG**: Development and detailed information
- **INFO**: General trading information
- **WARNING**: Attention-required situations
- **ERROR**: Error occurrences
- **CRITICAL**: System-stopping errors

### Sample Log Output
```
2024-01-20 15:30:45 | INFO | 🔄 TRADE | BTC/USDT | BUY | Amount: 0.001 | Price: 45000
2024-01-20 15:30:46 | INFO | 📊 SIGNAL | ETH/USDT | SELL | RSI: 75.5 | Overbought zone
2024-01-20 15:30:47 | WARNING | ⚠️ RISK | BNB/USDT | STOP_LOSS | Current Loss: 1.2%
```

## Security

### API Key Management
- ✅ All sensitive data in `.env` files
- ✅ Comprehensive `.gitignore` for security
- ✅ Environment variable templates provided
- ✅ No hardcoded credentials in source code

### Input Validation
- ✅ All user inputs validated and sanitized
- ✅ SQL injection prevention (though we use SQLite)
- ✅ Parameter bounds checking (prices, amounts, limits)
- ✅ Symbol format validation

## Roadmap

### ✅ Recently Completed
- [x] **Advanced Rate Limiting**: Multi-window control with burst protection
- [x] **Arbitrage Scanner**: Multi-exchange opportunity detection
- [x] **Recursion-Safe Architecture**: Complete elimination of recursion errors
- [x] **Complete CLI Interface**: Full application runner with real-time dashboard
- [x] **Comprehensive Testing**: 22+ integration tests with system readiness scoring
- [x] **Production Database**: Professional SQLite management with optimization

### 🚧 Next Phase
- [ ] **RSI Strategy Implementation**: Complete RSI-based trading algorithm
- [ ] **Risk Management System**: Position sizing and loss prevention
- [ ] **Backtesting Framework**: Historical strategy validation
- [ ] **Paper Trading Mode**: Live strategy testing without real money
- [ ] **Telegram Notifications**: Real-time alerts and trade notifications
- [ ] **Live Trading Engine**: Automated order execution and management

### 🎯 Future Features
- [ ] Machine learning price prediction
- [ ] Advanced portfolio management
- [ ] Web dashboard interface
- [ ] Mobile app notifications
- [ ] Social trading features

## Contributing

1. Follow the guidelines in `CLAUDE.md`
2. Write comprehensive tests
3. Add proper error handling
4. Include docstrings for all functions
5. Test with both testnet and small amounts on mainnet

## License

Private project - All rights reserved

---

**⚠️ Risk Disclaimer**: Cryptocurrency trading involves significant risk. Never trade with money you cannot afford to lose. This software is for educational purposes. Always test thoroughly on testnets before live trading.