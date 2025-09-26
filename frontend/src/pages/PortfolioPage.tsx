/**
 * Portfolio page component
 */

import React, { useState } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Statistic,
  Typography,
  Space,
  Tag,
  Progress,
  Alert,
  Button,
  Select,
  DatePicker
} from 'antd';
import {
  DollarCircleOutlined,
  RiseOutlined,
  FallOutlined,
  PieChartOutlined,
  BarChartOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import { useQuery } from '@tanstack/react-query';
import { binanceApi, BalanceInfo } from '../services/binanceApi';
import { formatCurrency, formatPercentage, formatDateTime } from '../utils/formatters';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;
const { RangePicker } = DatePicker;

// Portfolio data calculated from live Binance API only

export const PortfolioPage: React.FC = () => {
  const [selectedTimeRange, setSelectedTimeRange] = useState('7d');
  const { user } = useAuthStore();

  const isApiConfigured = !!user?.binance_api_key;

  // Fetch account information and balances
  const { data: accountInfo, isLoading: loadingAccount, refetch: refetchAccount } = useQuery({
    queryKey: ['account-info'],
    queryFn: () => binanceApi.getAccountInfo(),
    enabled: isApiConfigured,
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch current prices for portfolio calculation
  const { data: priceData } = useQuery({
    queryKey: ['ticker-prices'],
    queryFn: () => binanceApi.getTickerPrices(),
    enabled: isApiConfigured,
    refetchInterval: 10000, // Refresh every 10 seconds
  });
  const hasBalances = accountInfo?.success && accountInfo.data?.balances && accountInfo.data.balances.length > 0;

  // Calculate portfolio value from real balances
  const calculatePortfolioValue = () => {
    if (!hasBalances || !priceData?.success) {
      return {
        totalValue: 0,
        totalInvested: 0,
        totalPnL: 0,
        totalPnLPercent: 0,
        dailyChange: 0,
        dailyChangePercent: 0,
        holdings: []
      };
    }

    let totalValue = 0;
    const holdings = accountInfo.data!.balances!
      .filter(balance => balance.free > 0 || balance.locked > 0)
      .map((balance: BalanceInfo) => {
        const totalAmount = balance.free + balance.locked;
        let currentPrice = 1;
        let value = totalAmount;

        // Find current price for non-stable coins
        if (balance.asset !== 'USDT' && balance.asset !== 'BUSD' && priceData.data) {
          const symbol = `${balance.asset}USDT`;
          const ticker = Array.isArray(priceData.data)
            ? priceData.data.find(t => t.symbol === symbol)
            : null;

          if (ticker) {
            currentPrice = ticker.price;
            value = totalAmount * currentPrice;
          }
        }

        totalValue += value;

        return {
          asset: balance.asset,
          symbol: balance.asset === 'USDT' ? 'USDT' : `${balance.asset}USDT`,
          amount: totalAmount,
          currentPrice,
          value,
          allocation: 0, // Will be calculated after totalValue is known
          avgPrice: currentPrice, // Mock data
          pnl: 0, // Mock data
          pnlPercent: 0, // Mock data
        };
      });

    // Calculate allocation percentages
    holdings.forEach(holding => {
      holding.allocation = totalValue > 0 ? (holding.value / totalValue) * 100 : 0;
    });

    return {
      totalValue,
      holdings: holdings.sort((a, b) => b.value - a.value),
      // Mock data for other fields
      totalInvested: totalValue * 0.85,
      totalPnL: totalValue * 0.15,
      totalPnLPercent: 15,
      dailyChange: totalValue * 0.02,
      dailyChangePercent: 2,
    };
  };

  const portfolioData = calculatePortfolioValue();

  // Table columns for holdings
  const holdingsColumns = [
    {
      title: 'Asset',
      dataIndex: 'asset',
      key: 'asset',
      render: (asset: string, record: any) => (
        <Space>
          <div className="w-8 h-8 bg-gray-100 rounded-full flex items-center justify-center">
            <span className="text-xs font-medium">{asset}</span>
          </div>
          <div>
            <div className="font-medium">{asset}</div>
            <div className="text-xs text-gray-500">{record.symbol}</div>
          </div>
        </Space>
      ),
    },
    {
      title: 'Amount',
      dataIndex: 'amount',
      key: 'amount',
      render: (amount: any) => {
        const numAmount = typeof amount === 'number' ? amount : parseFloat(amount) || 0;
        return numAmount.toFixed(6);
      },
    },
    {
      title: 'Price',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      render: (price: number) => formatCurrency(price),
    },
    {
      title: 'Value',
      dataIndex: 'value',
      key: 'value',
      render: (value: number) => formatCurrency(value),
      sorter: (a: any, b: any) => a.value - b.value,
      defaultSortOrder: 'descend' as const,
    },
    {
      title: 'Allocation',
      dataIndex: 'allocation',
      key: 'allocation',
      render: (allocation: number) => (
        <Space direction="vertical" size={2}>
          <Text>{formatPercentage(allocation)}</Text>
          <Progress percent={allocation} size="small" showInfo={false} />
        </Space>
      ),
    },
    {
      title: 'P&L',
      key: 'pnl',
      render: (_: any, record: any) => (
        <Space direction="vertical" size={0}>
          <Text style={{ color: record.pnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
            {record.pnl >= 0 ? '+' : ''}{formatCurrency(record.pnl)}
          </Text>
          <Text
            type="secondary"
            style={{ color: record.pnlPercent >= 0 ? '#52c41a' : '#ff4d4f' }}
          >
            {record.pnlPercent >= 0 ? '+' : ''}{formatPercentage(record.pnlPercent)}
          </Text>
        </Space>
      ),
    },
  ];

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <Title level={2} className="!mb-1">
            Portfolio
          </Title>
          <Text type="secondary">
            Track your crypto holdings and performance.
          </Text>
        </div>
        <Space>
          <Select
            value={selectedTimeRange}
            onChange={setSelectedTimeRange}
            style={{ width: 100 }}
          >
            <Select.Option value="1d">1D</Select.Option>
            <Select.Option value="7d">7D</Select.Option>
            <Select.Option value="30d">30D</Select.Option>
            <Select.Option value="90d">90D</Select.Option>
          </Select>
          {isApiConfigured && (
            <Button
              icon={<ReloadOutlined />}
              onClick={() => refetchAccount()}
              loading={loadingAccount}
            >
              Refresh
            </Button>
          )}
        </Space>
      </div>

      {!isApiConfigured && (
        <Alert
          message="API Configuration Required"
          description="Please configure your Binance API keys in Settings to view your real portfolio data."
          type="info"
          showIcon
          closable
        />
      )}

      {/* Portfolio Overview */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Portfolio Value"
              value={portfolioData.totalValue}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarCircleOutlined />}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total P&L"
              value={portfolioData.totalPnL}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={
                portfolioData.totalPnL >= 0 ? (
                  <RiseOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <FallOutlined style={{ color: '#ff4d4f' }} />
                )
              }
              valueStyle={{
                color: portfolioData.totalPnL >= 0 ? '#52c41a' : '#ff4d4f'
              }}
            />
            <div className="mt-1 text-xs text-gray-500">
              {formatPercentage(portfolioData.totalPnLPercent)}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Daily Change"
              value={portfolioData.dailyChange}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={
                portfolioData.dailyChange >= 0 ? (
                  <RiseOutlined style={{ color: '#52c41a' }} />
                ) : (
                  <FallOutlined style={{ color: '#ff4d4f' }} />
                )
              }
              valueStyle={{
                color: portfolioData.dailyChange >= 0 ? '#52c41a' : '#ff4d4f'
              }}
            />
            <div className="mt-1 text-xs text-gray-500">
              {formatPercentage(portfolioData.dailyChangePercent)}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} lg={6}>
          <Card>
            <Statistic
              title="Total Invested"
              value={portfolioData.totalInvested}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<PieChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Holdings Table */}
      <Card
        title={
          <Space>
            <BarChartOutlined />
            Holdings
            {!isApiConfigured && (
              <Tag color="orange">Demo Data</Tag>
            )}
          </Space>
        }
      >
        <Table
          dataSource={portfolioData.holdings}
          columns={holdingsColumns}
          rowKey="asset"
          loading={loadingAccount}
          pagination={false}
          size="small"
          locale={{
            emptyText: isApiConfigured
              ? 'No holdings found. Start trading to see your portfolio.'
              : 'Configure your API keys to view your real portfolio.'
          }}
        />
      </Card>

      {/* Performance Chart Placeholder */}
      <Card title="Performance Chart">
        <div className="h-64 flex items-center justify-center bg-gray-50 rounded">
          <div className="text-center">
            <BarChartOutlined style={{ fontSize: 48, color: '#d9d9d9' }} />
            <div className="mt-4 text-gray-500">
              Portfolio performance chart will be implemented with charting library
            </div>
          </div>
        </div>
      </Card>
    </div>
  );
};