module.exports = {
  apps: [
    // Freqtrade Main Trading Bot
    {
      name: 'freqtrade-trader',
      script: 'docker-compose',
      args: 'exec -T freqtrade freqtrade trade --config /freqtrade/config/config.json --strategy MultiIndicatorStrategy',
      interpreter: 'none',
      cwd: '/opt/crypto-trader/freqtrade',

      // Auto restart configuration
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 4000,

      // Error handling
      error_file: './logs/freqtrade-trader-error.log',
      out_file: './logs/freqtrade-trader-out.log',
      log_file: './logs/freqtrade-trader-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource monitoring
      max_memory_restart: '1G',
      node_args: '--max-old-space-size=1024',

      // Environment
      env: {
        NODE_ENV: 'production',
        FREQTRADE_ENV: 'production',
        TZ: 'UTC'
      },

      // Health check
      health_check_grace_period: 3000,
      health_check_fatal_exceptions: true,

      // Instance control
      instances: 1,
      exec_mode: 'fork',

      // Monitoring
      monitoring: true,
      pmx: true
    },

    // Freqtrade Web UI
    {
      name: 'freqtrade-ui',
      script: 'docker-compose',
      args: 'exec -T freqtrade-ui freqtrade trade --config /freqtrade/config/config.json --strategy MultiIndicatorStrategy',
      interpreter: 'none',
      cwd: '/opt/crypto-trader/freqtrade',

      // Auto restart configuration
      autorestart: true,
      max_restarts: 5,
      min_uptime: '10s',
      restart_delay: 4000,

      // Logging
      error_file: './logs/freqtrade-ui-error.log',
      out_file: './logs/freqtrade-ui-out.log',
      log_file: './logs/freqtrade-ui-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '512M',

      // Environment
      env: {
        NODE_ENV: 'production',
        FREQTRADE_UI_PORT: '8081',
        TZ: 'UTC'
      },

      // Instance control
      instances: 1,
      exec_mode: 'fork'
    },

    // Freqtrade Performance Monitor
    {
      name: 'freqtrade-monitor',
      script: './freqtrade_monitor.py',
      interpreter: 'python3',
      cwd: '/opt/crypto-trader/freqtrade',

      // Schedule: Run every 5 minutes
      cron_restart: '*/5 * * * *',
      autorestart: false,

      // Logging
      error_file: './logs/freqtrade-monitor-error.log',
      out_file: './logs/freqtrade-monitor-out.log',
      log_file: './logs/freqtrade-monitor-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '256M',

      // Environment
      env: {
        PYTHONPATH: '/opt/crypto-trader/freqtrade',
        MONITOR_INTERVAL: '300',
        TZ: 'UTC'
      }
    },

    // Freqtrade Backup Service
    {
      name: 'freqtrade-backup',
      script: './freqtrade_backup.py',
      interpreter: 'python3',
      cwd: '/opt/crypto-trader/freqtrade',

      // Schedule: Run daily at 2:30 AM
      cron_restart: '30 2 * * *',
      autorestart: false,

      // Logging
      error_file: './logs/freqtrade-backup-error.log',
      out_file: './logs/freqtrade-backup-out.log',
      log_file: './logs/freqtrade-backup-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '512M',

      // Environment
      env: {
        PYTHONPATH: '/opt/crypto-trader/freqtrade',
        BACKUP_RETENTION_DAYS: '30',
        TZ: 'UTC'
      }
    },

    // System Health Checker
    {
      name: 'freqtrade-health',
      script: './health_checker.py',
      interpreter: 'python3',
      cwd: '/opt/crypto-trader/freqtrade',

      // Run every minute
      cron_restart: '* * * * *',
      autorestart: false,

      // Logging
      error_file: './logs/health-checker-error.log',
      out_file: './logs/health-checker-out.log',
      log_file: './logs/health-checker-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '128M',

      // Environment
      env: {
        PYTHONPATH: '/opt/crypto-trader/freqtrade',
        HEALTH_CHECK_INTERVAL: '60',
        TZ: 'UTC'
      }
    },

    // Integration Bridge (connects with existing crypto-trader system)
    {
      name: 'freqtrade-bridge',
      script: './integration_bridge.py',
      interpreter: 'python3',
      cwd: '/opt/crypto-trader/freqtrade',

      // Keep alive
      autorestart: true,
      max_restarts: 10,
      min_uptime: '10s',
      restart_delay: 5000,

      // Logging
      error_file: './logs/freqtrade-bridge-error.log',
      out_file: './logs/freqtrade-bridge-out.log',
      log_file: './logs/freqtrade-bridge-combined.log',
      log_date_format: 'YYYY-MM-DD HH:mm:ss Z',

      // Resource limits
      max_memory_restart: '256M',

      // Environment
      env: {
        PYTHONPATH: '/opt/crypto-trader/freqtrade',
        BRIDGE_PORT: '8082',
        CRYPTO_TRADER_API: 'http://localhost:8501',
        TZ: 'UTC'
      },

      // Instance control
      instances: 1,
      exec_mode: 'fork'
    }
  ],

  // Deployment configuration
  deploy: {
    production: {
      user: 'linuxuser',
      host: '141.164.42.93',
      ref: 'origin/main',
      repo: 'https://github.com/jilee1212/crypto-trader-pro.git',
      path: '/opt/crypto-trader/freqtrade',
      'post-deploy': 'npm install && pm2 reload ecosystem.config.js --env production',
      env: {
        NODE_ENV: 'production'
      }
    }
  },

  // Global PM2 settings
  global: {
    // Log rotation
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    error_file: './logs/pm2-error.log',
    out_file: './logs/pm2-out.log',

    // Clustering
    instances: 'max',
    exec_mode: 'cluster',

    // Auto restart
    autorestart: true,
    watch: false,
    max_memory_restart: '1G',

    // Environment
    env: {
      NODE_ENV: 'production',
      TZ: 'UTC'
    }
  }
};