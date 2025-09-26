/**
 * Dashboard page component
 */

import React from 'react';
import { Row, Col, Card, Statistic, Typography, Space, Tag, Button, Alert } from 'antd';
import {
  DollarCircleOutlined,
  RiseOutlined,
  FallOutlined,
  PieChartOutlined,
  LineChartOutlined,
  SettingOutlined,
  WarningOutlined,
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../stores/authStore';
import { formatCurrency, formatPercentage, formatDateTime } from '../utils/formatters';
import { binanceApi } from '../services/binanceApi';
import { binanceFuturesApi } from '../services/binanceFuturesApi';

const { Title, Text } = Typography;

export const DashboardPage: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  // Fetch live account data
  const { data: accountInfo, isLoading: loadingAccount } = useQuery({
    queryKey: ['account-info'],
    queryFn: () => binanceApi.getAccountInfo(),
    enabled: !!user?.binance_api_key,
    refetchInterval: 30000,
  });

  // Fetch futures account data
  const { data: futuresAccount, isLoading: loadingFutures } = useQuery({
    queryKey: ['futures-account'],
    queryFn: () => binanceFuturesApi.getFuturesAccountInfo(),
    enabled: !!user?.binance_api_key,
    refetchInterval: 30000,
  });

  // Fetch current positions
  const { data: positions } = useQuery({
    queryKey: ['futures-positions'],
    queryFn: () => binanceFuturesApi.getPositions(),
    enabled: !!user?.binance_api_key,
    refetchInterval: 10000,
  });

  // Fetch current prices for calculations
  const { data: priceData } = useQuery({
    queryKey: ['ticker-prices'],
    queryFn: () => binanceApi.getTickerPrices(),
    enabled: !!user?.binance_api_key,
    refetchInterval: 5000,
  });

  // Calculate portfolio stats from real data
  const calculatePortfolioStats = () => {
    let totalValue = 0;
    let spotValue = 0;
    let futuresValue = 0;

    // Spot portfolio value
    if (accountInfo?.success && accountInfo.data?.balances && priceData?.success) {
      accountInfo.data.balances.forEach(balance => {
        const totalAmount = balance.free + balance.locked;
        if (totalAmount > 0) {
          if (balance.asset === 'USDT' || balance.asset === 'BUSD') {
            spotValue += totalAmount;
          } else if (priceData.data) {
            const symbol = `${balance.asset}USDT`;
            const ticker = Array.isArray(priceData.data)
              ? priceData.data.find(t => t.symbol === symbol)
              : null;
            if (ticker) {
              spotValue += totalAmount * ticker.price;
            }
          }
        }
      });
    }

    // Futures portfolio value
    if (futuresAccount?.success && futuresAccount.data) {
      futuresValue = futuresAccount.data.total_wallet_balance || 0;
    }

    totalValue = spotValue + futuresValue;

    return {
      totalValue,
      spotValue,
      futuresValue,
      todayChange: futuresAccount?.data?.total_unrealized_pnl || 0,
      todayChangePercent: totalValue > 0 ? ((futuresAccount?.data?.total_unrealized_pnl || 0) / totalValue) * 100 : 0,
    };
  };

  const portfolioStats = calculatePortfolioStats();
  const activePositions = positions?.success ? positions.data?.filter(p => Math.abs(p.position_amt || 0) > 0).length || 0 : 0;

  const needsApiSetup = !user?.binance_api_key;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="!mb-1">
            Welcome back, {user?.full_name || user?.username}!
          </Title>
          <Text type="secondary">
            Here's what's happening with your portfolio today.
          </Text>
        </div>

        <Tag color="red" className="text-sm font-bold">
          🔴 LIVE TRADING MODE
        </Tag>
      </div>

      {/* LIVE Trading Warning */}
      <Alert
        message="⚠️ LIVE TRADING MODE ACTIVE"
        description="This system is connected to LIVE Binance trading with REAL MONEY. All trades execute with actual funds."
        type="error"
        icon={<WarningOutlined />}
        showIcon
        style={{ marginBottom: 16, fontWeight: '500' }}
      />

      {/* API Setup Alert */}
      {needsApiSetup && (
        <Alert
          message="LIVE API Setup Required"
          description="Connect your LIVE Binance API keys to start real money trading."
          type="warning"
          action={
            <Button
              size="small"
              type="primary"
              icon={<SettingOutlined />}
              onClick={() => navigate('/settings')}
            >
              Setup LIVE API Keys
            </Button>
          }
          closable
        />
      )}

      {/* Portfolio Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Portfolio Value (LIVE)"
              value={portfolioStats.totalValue}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarCircleOutlined />}
              loading={loadingAccount || loadingFutures}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Unrealized P&L (LIVE)"
              value={portfolioStats.todayChange}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={
                portfolioStats.todayChange >= 0 ? (
                  <RiseOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <FallOutlined style={{ color: '#ff4d4f' }} />
                )
              }
              valueStyle={{
                color: portfolioStats.todayChange >= 0 ? '#52c41a' : '#ff4d4f'
              }}
              loading={loadingFutures}
            />
            <div className="mt-1 text-xs text-gray-500">
              {formatPercentage(portfolioStats.todayChangePercent)}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Spot Portfolio (LIVE)"
              value={portfolioStats.spotValue}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<PieChartOutlined />}
              loading={loadingAccount}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Active Positions (LIVE)"
              value={activePositions}
              prefix={<LineChartOutlined />}
              loading={loadingFutures}
            />
          </Card>
        </Col>
      </Row>

      {/* Content Grid */}
      <Row gutter={[16, 16]}>
        {/* Live Account Status */}
        <Col xs={24} lg={12}>
          <Card title="🔴 LIVE Account Status" className="h-full">
            {accountInfo?.success && accountInfo.data ? (
              <Space direction="vertical" size="middle" className="w-full">
                <div className="flex items-center justify-between">
                  <span>Spot Trading</span>
                  <Tag color={accountInfo.data.can_trade ? 'green' : 'red'}>
                    {accountInfo.data.can_trade ? '✅ Enabled' : '❌ Disabled'}
                  </Tag>
                </div>
                <div className="flex items-center justify-between">
                  <span>Account Type</span>
                  <span className="font-medium">{accountInfo.data.account_type || 'N/A'}</span>
                </div>
                {futuresAccount?.success && futuresAccount.data && (
                  <>
                    <div className="flex items-center justify-between">
                      <span>Futures Balance</span>
                      <span className="font-medium">
                        {formatCurrency(futuresAccount.data.total_wallet_balance || 0)}
                      </span>
                    </div>
                    <div className="flex items-center justify-between">
                      <span>Available Balance</span>
                      <span className="font-medium">
                        {formatCurrency(futuresAccount.data.available_balance || 0)}
                      </span>
                    </div>
                  </>
                )}
              </Space>
            ) : (
              <div className="text-center py-8 text-gray-500">
                {needsApiSetup ? 'Configure LIVE API keys to view account status' : 'Loading account data...'}
              </div>
            )}
          </Card>
        </Col>

        {/* Live Positions */}
        <Col xs={24} lg={12}>
          <Card title="🔴 LIVE Positions" className="h-full">
            {positions?.success && positions.data && positions.data.length > 0 ? (
              <Space direction="vertical" size="middle" className="w-full">
                {positions.data
                  .filter(p => Math.abs(p.position_amt || 0) > 0)
                  .slice(0, 5)
                  .map((position, index) => (
                    <div key={index} className="flex items-center justify-between">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-medium">{position.symbol}</span>
                          <Tag color={position.side === 'LONG' ? 'green' : 'red'}>
                            {position.side}
                          </Tag>
                        </div>
                        <div className="text-xs text-gray-500">
                          {Math.abs(position.position_amt || 0).toFixed(4)} @ {(position.entry_price || 0).toFixed(2)}
                        </div>
                      </div>
                      <div className="text-right">
                        <div className={`font-medium ${(position.unrealized_pnl || 0) >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                          {formatCurrency(position.unrealized_pnl || 0)}
                        </div>
                        <div className="text-xs text-gray-500">
                          {(position.percentage || 0).toFixed(2)}%
                        </div>
                      </div>
                    </div>
                  ))
                }
                {activePositions === 0 && (
                  <div className="text-center py-4 text-gray-500">
                    No active positions
                  </div>
                )}
              </Space>
            ) : (
              <div className="text-center py-8 text-gray-500">
                {needsApiSetup ? 'Configure LIVE API keys to view positions' : 'Loading positions...'}
              </div>
            )}
          </Card>
        </Col>
      </Row>

      {/* Quick Actions */}
      <Card title="Quick Actions">
        <Row gutter={[16, 16]}>
          <Col>
            <Button type="primary" size="large">
              Start Trading
            </Button>
          </Col>
          <Col>
            <Button size="large">
              View Portfolio
            </Button>
          </Col>
          <Col>
            <Button size="large">
              Market Analysis
            </Button>
          </Col>
          <Col>
            <Button size="large" icon={<SettingOutlined />}>
              Settings
            </Button>
          </Col>
        </Row>
      </Card>
    </div>
  );
};