// PM2 Ecosystem Configuration for Crypto Trader Pro
// 24시간 무인 자동매매 시스템 - Phase 4 완료 (알림 시스템 + 백업 시스템)

module.exports = {
  apps: [
    {
      name: 'crypto-trader-web',
      script: 'streamlit',
      args: 'run main_platform.py --server.port 8501 --server.headless true',
      cwd: '/opt/crypto-trader/crypto-trader-pro/',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '1G',
      restart_delay: 5000,
      max_restarts: 10,
      min_uptime: '10s',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/opt/crypto-trader/crypto-trader-pro',
        STREAMLIT_SERVER_HEADLESS: 'true',
        STREAMLIT_SERVER_ENABLE_CORS: 'false',
        STREAMLIT_BROWSER_GATHER_USAGE_STATS: 'false'
      },
      error_file: '/opt/crypto-trader/logs/crypto-trader-web-error.log',
      out_file: '/opt/crypto-trader/logs/crypto-trader-web-out.log',
      log_file: '/opt/crypto-trader/logs/crypto-trader-web.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },
    {
      name: 'crypto-trader-bot',
      script: 'python',
      args: 'trading_engine/background_trader.py',
      cwd: '/opt/crypto-trader/crypto-trader-pro/',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '512M',
      restart_delay: 10000,
      max_restarts: 5,
      min_uptime: '30s',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/opt/crypto-trader/crypto-trader-pro'
      },
      error_file: '/opt/crypto-trader/logs/crypto-trader-bot-error.log',
      out_file: '/opt/crypto-trader/logs/crypto-trader-bot-out.log',
      log_file: '/opt/crypto-trader/logs/crypto-trader-bot.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    },
    {
      name: 'crypto-trader-backup',
      script: 'python',
      args: 'backup_scheduler.py',
      cwd: '/opt/crypto-trader/crypto-trader-pro/',
      instances: 1,
      autorestart: true,
      watch: false,
      max_memory_restart: '256M',
      restart_delay: 30000,
      max_restarts: 3,
      min_uptime: '60s',
      env: {
        NODE_ENV: 'production',
        PYTHONPATH: '/opt/crypto-trader/crypto-trader-pro'
      },
      error_file: '/opt/crypto-trader/logs/crypto-trader-backup-error.log',
      out_file: '/opt/crypto-trader/logs/crypto-trader-backup-out.log',
      log_file: '/opt/crypto-trader/logs/crypto-trader-backup.log',
      time: true,
      log_date_format: 'YYYY-MM-DD HH:mm:ss',
      merge_logs: true
    }
  ],

  // 배포 설정
  deploy: {
    production: {
      user: 'crypto-trader',
      host: ['nosignup.kr'],
      ref: 'origin/main',
      repo: 'https://github.com/jilee1212/crypto-trader-pro.git',
      path: '/opt/crypto-trader',
      'pre-deploy-local': '',
      'post-deploy': 'cd crypto-trader-pro && pip install -r requirements.txt && pm2 reload ecosystem.config.js --env production',
      'pre-setup': 'mkdir -p /opt/crypto-trader/logs'
    }
  }
};