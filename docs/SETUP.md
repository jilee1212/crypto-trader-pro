# Crypto Trader Pro - Setup Guide

**🎉 Phase 1-4 완료: 24시간 무인 자동매매 시스템 + 고급 기능 100% 구축 완료**

This guide will help you safely set up and configure Crypto Trader Pro for educational and research purposes.

## ⚠️ Critical Security Warning

**NEVER start with live trading or real API keys!**

- This software is for educational purposes only
- Always begin with testnet/paper trading
- Cryptocurrency trading involves substantial risk
- Test thoroughly before considering any live implementation

## Step 1: Environment Setup

### 1.1 Python Requirements
```bash
# Check Python version (3.8+ required)
python --version

# Create virtual environment (recommended)
python -m venv crypto-trader-env
source crypto-trader-env/bin/activate  # Linux/Mac
# or
crypto-trader-env\Scripts\activate     # Windows
```

### 1.2 Install Dependencies (Phase 4 Complete)
```bash
# Install all dependencies (includes Phase 4 additions)
pip install -r requirements.txt

# Verify core installations
python -c "import ccxt; print('CCXT version:', ccxt.__version__)"
python -c "import sqlalchemy; print('SQLAlchemy version:', sqlalchemy.__version__)"
python -c "import streamlit; print('Streamlit version:', streamlit.__version__)"

# Initialize database (Phase 1-4 system)
cd database
python init_database.py --reset
```

## Step 2: Quick Start (Phase 4 System)

### 2.1 Run the Complete System
```bash
# Start the main web platform
streamlit run main_platform.py

# In a separate terminal, start the background trading bot
python trading_engine/background_trader.py

# In another terminal, start the backup scheduler
python backup_scheduler.py
```

### 2.2 First-Time Setup
1. **Register**: http://localhost:8501 에서 계정 생성
2. **API 설정**: 사이드바 → API 설정 → Binance 테스트넷 키 입력
3. **거래 설정**: 계좌 잔고, 리스크 비율, 거래 모드 설정
4. **AI 신호**: AI 신호 탭에서 실시간 신호 생성 및 확인

### 2.3 Phase 4 System Configuration

#### Notification System Setup (알림 시스템)
```json
# notification_config.json 수정
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_username": "your_email@gmail.com",
    "smtp_password": "your_app_password"
  },
  "telegram": {
    "enabled": true,
    "bot_token": "your_telegram_bot_token"
  }
}
```

#### Backup System Setup (백업 시스템)
```json
# backup_config.json 자동 생성됨
{
  "enabled": true,
  "auto_backup_enabled": true,
  "retention_days": 30
}
```

## Step 3: Advanced Configuration (Legacy)

### 3.1 Create Configuration Files
```bash
# Copy configuration templates
cp config/config.json.example config/config.json
cp .env.template .env
```

### 3.2 Edit Environment Variables (.env)
```bash
# Open .env file and configure (START WITH TESTNET!)
TRADING_MODE=testnet
BINANCE_API_KEY=your_testnet_api_key
BINANCE_API_SECRET=your_testnet_secret
LOG_LEVEL=INFO
```

### 2.3 Configure Main Settings (config/config.json)
Key settings to modify:
```json
{
  "exchange": {
    "testnet": true,  // KEEP TRUE initially!
    "name": "binance"
  },
  "trading": {
    "max_risk_per_trade": 0.01,  // Very conservative
    "daily_loss_limit": 0.02,
    "currencies": ["BTC/USDT"]   // Start with one pair
  }
}
```

## Step 3: Getting API Keys

### 3.1 Binance Testnet (RECOMMENDED START)
1. Visit https://testnet.binance.vision/
2. Login with GitHub account
3. Generate API keys
4. ⚠️ These are testnet keys - safe for learning

### 3.2 Binance Live (ONLY AFTER EXTENSIVE TESTING)
1. Visit https://www.binance.com/
2. Complete account verification
3. Enable 2FA
4. Create API keys with trading permissions
5. **Start with small amounts only!**

### 3.3 API Key Security Checklist
- [ ] Keys are in .env file (not config.json)
- [ ] .env is in .gitignore
- [ ] Never share or commit API keys
- [ ] Use testnet keys initially
- [ ] Enable IP restrictions when possible
- [ ] Set minimal required permissions

## Step 4: Initial Testing

### 4.1 Run Basic Tests
```bash
# Test market data connection
python test_market_data.py

# Test data collection system
python test_data_collection.py

# Run complete integration tests
python final_integration_test.py
```

### 4.2 Start Basic Application
```bash
# Start the main application
python main.py

# Select option 2: System Diagnostics
# Verify all systems are working
```

## Step 5: Understanding the System

### 5.1 Data Collection
- The system collects market data automatically
- Database stores OHLCV data, prices, and metadata
- Scheduling system manages data collection frequency

### 5.2 Arbitrage Scanner
- Monitors price differences across exchanges
- Calculates potential profits including fees
- **For research purposes only - not automated trading**

### 5.3 Risk Management
- Multiple safety mechanisms built-in
- Position limits and loss limits
- Emergency stop functionality

## Step 6: Educational Usage

### 6.1 Recommended Learning Path
1. **Week 1**: Run market data collection, understand data flow
2. **Week 2**: Experiment with arbitrage scanner, analyze opportunities
3. **Week 3**: Modify parameters, understand risk management
4. **Week 4**: Develop custom strategies (future development)

### 6.2 Safe Experimentation
- Always use testnet for experimentation
- Study the code to understand logic
- Modify parameters gradually
- Document your observations

## Step 7: Advanced Configuration

### 7.1 Database Management
```bash
# Database automatically created at data/crypto_data.db
# Backup important data regularly
cp data/crypto_data.db data/backup_$(date +%Y%m%d).db
```

### 7.2 Logging Configuration
```bash
# Logs are stored in logs/ directory
# Adjust log levels in .env file
LOG_LEVEL=DEBUG  # For detailed debugging
LOG_LEVEL=INFO   # For normal operation
LOG_LEVEL=ERROR  # For errors only
```

### 7.3 Performance Tuning
```bash
# Adjust rate limiting in .env
RATE_LIMIT_CALLS_PER_SECOND=5   # Conservative
RATE_LIMIT_CALLS_PER_MINUTE=300 # Conservative

# Adjust resource limits
MAX_CPU_PERCENT=70
MAX_MEMORY_PERCENT=80
```

## Common Issues and Solutions

### Issue: API Connection Errors
**Solution**:
- Verify API keys are correct
- Check internet connection
- Ensure testnet=true for testnet keys
- Check exchange status

### Issue: Database Errors
**Solution**:
- Ensure data/ directory exists
- Check disk space
- Verify SQLite is available
- Check file permissions

### Issue: Rate Limiting Errors
**Solution**:
- Reduce API call frequency
- Increase delays between calls
- Use testnet for development
- Check exchange rate limits

### Issue: Import Errors
**Solution**:
- Verify virtual environment is activated
- Reinstall requirements: `pip install -r requirements.txt`
- Check Python version compatibility

## Security Best Practices

### File Security
- Never commit .env files
- Keep config.json generic (no secrets)
- Regularly update .gitignore
- Use secure file permissions

### API Security
- Start with testnet always
- Use minimal API permissions
- Enable IP restrictions
- Rotate keys regularly
- Monitor API usage

### Trading Security
- Never risk more than you can afford to lose
- Start with very small amounts
- Use stop-losses
- Monitor positions constantly
- Have emergency procedures

## Next Steps

After successful setup:

1. **Study the code** - Understand how each component works
2. **Analyze data** - Look at collected market data and patterns
3. **Research strategies** - Study RSI and arbitrage concepts
4. **Paper trading** - Simulate trades without real money
5. **Contribute** - Improve the codebase with your insights

## Getting Help

- Review code comments and documentation
- Check GitHub issues for common problems
- Study test files for usage examples
- Analyze log files for detailed information

## Legal and Ethical Considerations

- This software is for educational purposes only
- Comply with local financial regulations
- Respect exchange terms of service
- Use responsibly and ethically
- No guarantees of profitability
- Past performance doesn't predict future results

Remember: The goal is learning and research, not guaranteed profits!