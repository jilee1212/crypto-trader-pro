# 🚀 Freqtrade Operations Manual

## 📋 Overview

This manual covers the complete operation of the Freqtrade trading system integrated with Crypto Trader Pro. It includes startup procedures, monitoring, troubleshooting, and maintenance tasks.

### System Architecture

```
Freqtrade System Components:
├── 🐳 Docker Containers
│   ├── freqtrade-trader (Main trading bot)
│   └── freqtrade-ui (Web interface)
├── ⚙️  PM2 Process Management
│   ├── freqtrade-monitor (Performance monitoring)
│   ├── freqtrade-backup (Automated backups)
│   ├── freqtrade-health (Health checking)
│   └── freqtrade-bridge (Integration bridge)
├── 📊 Monitoring & Dashboards
│   ├── Real-time dashboard (Port 8083)
│   ├── Freqtrade UI (Port 8081)
│   └── Integration bridge API (Port 8082)
└── 🔗 Integration with Crypto Trader Pro
    ├── Shared notifications (Email/Telegram)
    ├── Unified backup system
    └── Performance monitoring
```

## 🚀 Startup Procedures

### 1. System Startup

```bash
# Complete system startup
cd /opt/crypto-trader/freqtrade

# Start all services
pm2 start ecosystem.config.js

# Verify services
pm2 status
```

### 2. Individual Service Management

```bash
# Start specific services
pm2 start freqtrade-trader
pm2 start freqtrade-ui
pm2 start freqtrade-monitor
pm2 start freqtrade-backup
pm2 start freqtrade-bridge

# Check service status
pm2 show freqtrade-trader

# View logs
pm2 logs freqtrade-trader
```

### 3. Docker Container Management

```bash
# Start Freqtrade containers
docker-compose up -d

# Check container status
docker-compose ps

# View container logs
docker-compose logs -f freqtrade

# Restart containers
docker-compose restart
```

## 📊 Monitoring & Health Checks

### 1. Real-time Monitoring

**Access Points:**
- **Freqtrade UI**: http://localhost:8081
- **Real-time Dashboard**: http://localhost:8083
- **Integration Bridge API**: http://localhost:8082

**Health Check Commands:**
```bash
# System health overview
python3 freqtrade_monitor.py

# Performance analysis
python3 performance_optimizer.py --analyze

# API status check
curl http://localhost:8080/api/v1/status | jq '.'

# Integration bridge status
curl http://localhost:8082/status | jq '.'
```

### 2. Performance Metrics

**Key Metrics to Monitor:**

| Metric | Normal Range | Warning | Critical |
|--------|--------------|---------|----------|
| CPU Usage | < 60% | 60-80% | > 80% |
| Memory Usage | < 70% | 70-85% | > 85% |
| API Response Time | < 2s | 2-5s | > 5s |
| Open Trades | 0-3 | 3-5 | > 5 |
| Daily Profit | -2% to +5% | < -2% | < -5% |

### 3. Automated Monitoring

**PM2 Monitoring:**
```bash
# Monitor all processes
pm2 monit

# Check restart count
pm2 show freqtrade-trader

# Reset restart counters
pm2 reset freqtrade-trader
```

**Health Checker:**
```bash
# Manual health check
python3 health_checker.py

# View health history
cat logs/health-checker-combined.log | tail -50
```

## ⚠️ Troubleshooting Guide

### 1. Common Issues

#### Freqtrade API Not Responding

**Symptoms:**
- Dashboard shows "API Connection Failed"
- curl commands timeout
- PM2 shows freqtrade-trader as errored

**Solutions:**
```bash
# Check container status
docker-compose ps

# Restart Freqtrade container
docker-compose restart freqtrade

# Check logs for errors
docker-compose logs freqtrade | tail -50

# Restart PM2 process
pm2 restart freqtrade-trader
```

#### High Memory Usage

**Symptoms:**
- System becomes slow
- Memory usage > 85%
- Containers getting killed

**Solutions:**
```bash
# Check memory usage
free -h

# Optimize performance
python3 performance_optimizer.py

# Restart memory-heavy processes
pm2 restart freqtrade-trader freqtrade-ui

# Clean up docker resources
docker system prune -f
```

#### Trading Stopped

**Symptoms:**
- No new trades opening
- Strategy shows as inactive
- Error messages in logs

**Solutions:**
```bash
# Check Freqtrade status
curl http://localhost:8080/api/v1/status

# Check strategy logs
docker-compose logs freqtrade | grep -i error

# Verify API keys
./setup_api_keys.sh

# Test strategy
docker-compose exec freqtrade freqtrade test-strategy \
    --strategy MultiIndicatorStrategy \
    --config /freqtrade/config/config.json
```

#### Database Issues

**Symptoms:**
- Error messages about database locks
- Performance degradation
- Missing trade data

**Solutions:**
```bash
# Check database file
ls -la user_data/tradesv3.dryrun.sqlite

# Backup database
python3 freqtrade_backup.py --type full

# Optimize database
docker-compose exec freqtrade freqtrade optimize-database
```

### 2. Emergency Procedures

#### Complete System Stop

```bash
# Stop all trading immediately
pm2 stop freqtrade-trader

# Stop all containers
docker-compose down

# Stop all PM2 processes
pm2 stop all
```

#### Emergency Backup

```bash
# Create emergency backup
python3 freqtrade_backup.py --type full

# Backup to external location
tar -czf emergency_backup_$(date +%Y%m%d_%H%M%S).tar.gz \
    config/ user_data/ logs/
```

#### Recovery from Backup

```bash
# Stop all services
pm2 stop all
docker-compose down

# Restore from backup
python3 freqtrade_backup.py --restore /path/to/backup.tar.gz

# Restart services
docker-compose up -d
pm2 start ecosystem.config.js
```

## 🔧 Maintenance Tasks

### 1. Daily Maintenance

**Automated (via PM2):**
- Performance monitoring every 5 minutes
- Health checks every minute
- Integration bridge monitoring continuous

**Manual (if needed):**
```bash
# Check system status
pm2 status && docker-compose ps

# Review overnight performance
python3 freqtrade_monitor.py --daily-report

# Check for errors
grep -i error logs/*.log | tail -20
```

### 2. Weekly Maintenance

```bash
# Performance optimization
python3 performance_optimizer.py

# Clean up old logs
find logs/ -name "*.log" -mtime +7 -delete

# Update system packages (if needed)
sudo apt update && sudo apt upgrade

# Verify backup integrity
python3 freqtrade_backup.py --list
```

### 3. Monthly Maintenance

```bash
# Full system backup
python3 freqtrade_backup.py --type full

# Strategy performance review
python3 strategy_analyzer.py --report

# System resource analysis
python3 performance_optimizer.py --benchmark

# Clean up old backups
python3 freqtrade_backup.py --cleanup

# Database optimization
docker-compose exec freqtrade freqtrade optimize-database
```

## 📈 Performance Tuning

### 1. Strategy Optimization

```bash
# Run hyperparameter optimization
python3 run_hyperopt.py --sequence --epochs 300

# Compare strategy performance
python3 strategy_analyzer.py \
    --strategies RSIStrategy AITradingStrategy MultiIndicatorStrategy

# Backtest with optimized parameters
docker-compose exec freqtrade freqtrade backtesting \
    --config /freqtrade/config/config.json \
    --strategy MultiIndicatorStrategy \
    --timerange 20241101-20241222
```

### 2. System Performance

```bash
# Run performance analysis
python3 performance_optimizer.py --analyze

# Apply optimizations
python3 performance_optimizer.py --optimize

# Monitor results
pm2 monit
```

### 3. Resource Optimization

**Docker Resource Limits:**
```yaml
# In docker-compose.yml
services:
  freqtrade:
    deploy:
      resources:
        limits:
          memory: 1G
          cpus: '2.0'
        reservations:
          memory: 512M
          cpus: '1.0'
```

**PM2 Resource Monitoring:**
```bash
# Set memory restart threshold
pm2 start ecosystem.config.js --max-memory-restart 1G

# Monitor resource usage
pm2 show freqtrade-trader
```

## 🔔 Notification Management

### 1. Configure Notifications

**Email Configuration:**
```json
{
  "email": {
    "enabled": true,
    "smtp_server": "smtp.gmail.com",
    "smtp_port": 587,
    "username": "your-email@gmail.com",
    "password": "your-app-password",
    "from": "your-email@gmail.com",
    "to": "alerts@yourdomain.com"
  }
}
```

**Telegram Configuration:**
```json
{
  "telegram": {
    "enabled": true,
    "token": "your-bot-token",
    "chat_id": "your-chat-id"
  }
}
```

### 2. Notification Types

**Automatic Notifications:**
- Trade opened/closed
- Performance alerts (profit/loss thresholds)
- System health issues
- Daily performance reports

**Manual Notifications:**
```bash
# Send test notification
curl -X POST http://localhost:8082/notify \
  -H "Content-Type: application/json" \
  -d '{
    "type": "TEST",
    "subject": "Test Notification",
    "message": "System test message"
  }'
```

## 🔐 Security Considerations

### 1. API Key Management

```bash
# Rotate API keys regularly
./setup_api_keys.sh

# Verify permissions
docker-compose exec freqtrade freqtrade test-pairlist

# Check API key restrictions
curl -H "Authorization: Bearer your-jwt-token" \
     http://localhost:8080/api/v1/status
```

### 2. Access Control

**Network Security:**
- Freqtrade API: localhost only (port 8080)
- Freqtrade UI: localhost only (port 8081)
- Integration Bridge: localhost only (port 8082)

**File Permissions:**
```bash
# Secure configuration files
chmod 600 config/config.json
chmod 600 user_data/*.db

# Secure backup files
chmod 700 backups/
```

### 3. Monitoring Security

```bash
# Check for unauthorized access
grep -i "unauthorized\|forbidden" logs/*.log

# Monitor failed authentication
grep -i "auth" logs/*.log | grep -i "fail"

# Review API access patterns
grep "GET\|POST" logs/freqtrade-*.log | tail -50
```

## 📊 Reporting and Analysis

### 1. Performance Reports

**Daily Report:**
```bash
# Generate daily report
python3 freqtrade_monitor.py --daily-report

# View via dashboard
http://localhost:8083
```

**Monthly Analysis:**
```bash
# Comprehensive analysis
python3 strategy_analyzer.py --report \
    --timerange 20241101-20241130

# Performance comparison
python3 backtest_comparison.py \
    --timerange 20241101-20241130
```

### 2. Risk Analysis

**Risk Metrics:**
- Maximum drawdown
- Sharpe ratio
- Win rate
- Average trade duration
- Profit factor

**Risk Monitoring:**
```bash
# Check current risk exposure
curl http://localhost:8080/api/v1/trades | jq '.[] | .profit_pct'

# Analyze historical risk
python3 strategy_analyzer.py --analyze-risk
```

## 🆘 Emergency Contacts and Procedures

### 1. Emergency Shutdown

**Immediate Actions:**
1. Stop all trading: `pm2 stop freqtrade-trader`
2. Close open positions manually via UI
3. Create emergency backup
4. Document the incident

### 2. Incident Response

**Steps:**
1. **Assess**: Determine severity and impact
2. **Contain**: Stop trading if necessary
3. **Investigate**: Check logs and metrics
4. **Resolve**: Apply fixes and test
5. **Document**: Record incident and resolution

### 3. Support Resources

**Documentation:**
- Freqtrade Official Docs: https://www.freqtrade.io/
- Crypto Trader Pro GitHub: https://github.com/jilee1212/crypto-trader-pro

**Log Locations:**
- PM2 Logs: `~/.pm2/logs/`
- Freqtrade Logs: `logs/`
- Docker Logs: `docker-compose logs`

**Configuration Files:**
- Main Config: `config/config.json`
- PM2 Config: `ecosystem.config.js`
- Docker Config: `docker-compose.yml`

## ✅ Daily Operations Checklist

### Morning Checklist
- [ ] Check PM2 process status
- [ ] Verify Docker containers running
- [ ] Review overnight trades and performance
- [ ] Check for any critical alerts
- [ ] Verify API connectivity

### Evening Checklist
- [ ] Review daily performance
- [ ] Check system resource usage
- [ ] Verify backup completion
- [ ] Review any errors or warnings
- [ ] Check notification delivery

### Weekly Checklist
- [ ] Run performance optimization
- [ ] Review strategy performance
- [ ] Clean up old logs
- [ ] Verify backup integrity
- [ ] Update system documentation

---

## 📞 Support and Escalation

For technical issues:
1. Check this operations manual
2. Review logs for error messages
3. Consult Freqtrade documentation
4. Check GitHub issues for similar problems

**Remember**: Always backup before making configuration changes!

---

*Last Updated: 2025-09-23*
*Version: 1.0*