/**
 * Trading page component
 */

import React, { useState, useEffect } from 'react';
import {
  Row,
  Col,
  Card,
  Table,
  Button,
  Select,
  Input,
  Form,
  Alert,
  Statistic,
  Typography,
  Space,
  Tag,
  Modal,
  InputNumber,
  message,
  Tabs,
  Badge
} from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  DollarCircleOutlined,
  LineChartOutlined,
  ShoppingCartOutlined,
  StopOutlined,
  WifiOutlined,
  DisconnectOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { binanceApi, TickerData, OrderRequest, OrderInfo } from '../services/binanceApi';
import { formatCurrency, formatPercentage } from '../utils/formatters';
import { websocketService, TickerUpdate } from '../services/websocket';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;
const { Option } = Select;

interface TradingFormData {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  price?: number;
}

export const TradingPage: React.FC = () => {
  const [form] = Form.useForm<TradingFormData>();
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [orderModalVisible, setOrderModalVisible] = useState(false);
  const [orderType, setOrderType] = useState<'BUY' | 'SELL'>('BUY');
  const [realTimeData, setRealTimeData] = useState<Map<string, TickerUpdate>>(new Map());
  const [wsConnected, setWsConnected] = useState(false);
  const queryClient = useQueryClient();

  // Check if API keys are configured
  const { user } = useAuthStore();
  const hasApiKeys = !!user?.binance_api_key;

  // Fetch popular trading pairs (public data - no API key required)
  const { data: popularPairs, isLoading: loadingPairs } = useQuery({
    queryKey: ['popular-pairs'],
    queryFn: () => binanceApi.getPopularPairs(),
    enabled: true, // Public data doesn't require API keys
    refetchInterval: 30000, // Refresh every 30 seconds
  });

  // Fetch 24hr ticker data
  const { data: tickerData, isLoading: loadingTicker } = useQuery({
    queryKey: ['24hr-ticker'],
    queryFn: () => binanceApi.get24hrTicker(),
    enabled: hasApiKeys,
    refetchInterval: 5000, // Refresh every 5 seconds
  });

  // Fetch open orders
  const { data: openOrders, isLoading: loadingOrders } = useQuery({
    queryKey: ['open-orders'],
    queryFn: () => binanceApi.getOpenOrders(),
    enabled: hasApiKeys,
    refetchInterval: 10000, // Refresh every 10 seconds
  });

  // Place order mutation
  const placeOrderMutation = useMutation({
    mutationFn: (orderData: OrderRequest) => binanceApi.placeOrder(orderData),
    onSuccess: (data) => {
      if (data.success) {
        message.success('Order placed successfully!');
        setOrderModalVisible(false);
        form.resetFields();
        queryClient.invalidateQueries({ queryKey: ['open-orders'] });
        queryClient.invalidateQueries({ queryKey: ['account-info'] });
      } else {
        message.error(data.error || 'Failed to place order');
      }
    },
    onError: (error) => {
      message.error('Failed to place order');
      console.error('Order placement error:', error);
    }
  });

  // Cancel order mutation
  const cancelOrderMutation = useMutation({
    mutationFn: ({ symbol, orderId }: { symbol: string; orderId: number }) =>
      binanceApi.cancelOrder(symbol, orderId),
    onSuccess: (data) => {
      if (data.success) {
        message.success('Order cancelled successfully!');
        queryClient.invalidateQueries({ queryKey: ['open-orders'] });
      } else {
        message.error(data.error || 'Failed to cancel order');
      }
    },
    onError: (error) => {
      message.error('Failed to cancel order');
      console.error('Order cancellation error:', error);
    }
  });

  // WebSocket connection effect
  useEffect(() => {
    // Subscribe to popular symbols for real-time updates
    const popularSymbols = ['BTCUSDT', 'ETHUSDT', 'BNBUSDT', 'ADAUSDT', 'DOTUSDT', 'XRPUSDT'];

    const unsubscribe = websocketService.subscribeToSymbols(
      popularSymbols,
      (update: TickerUpdate) => {
        setRealTimeData(prev => {
          const newMap = new Map(prev);
          newMap.set(update.symbol, update);
          return newMap;
        });
      }
    );

    // Monitor connection status
    const checkConnection = () => {
      setWsConnected(websocketService.isConnected());
    };

    const connectionInterval = setInterval(checkConnection, 1000);

    // Initial connection attempt
    websocketService.connect();

    return () => {
      unsubscribe();
      clearInterval(connectionInterval);
    };
  }, []);

  const handlePlaceOrder = (values: TradingFormData) => {
    const orderData: OrderRequest = {
      symbol: values.symbol,
      side: values.side,
      type: values.type,
      quantity: values.quantity,
      ...(values.type === 'LIMIT' && { price: values.price }),
    };

    placeOrderMutation.mutate(orderData);
  };

  const handleCancelOrder = (symbol: string, orderId: number) => {
    cancelOrderMutation.mutate({ symbol, orderId });
  };

  const openOrderModal = (side: 'BUY' | 'SELL') => {
    setOrderType(side);
    form.setFieldsValue({
      symbol: selectedSymbol,
      side,
      type: 'LIMIT',
      quantity: 0,
      price: 0,
    });
    setOrderModalVisible(true);
  };

  // Get enhanced data combining API and WebSocket
  const getEnhancedPairData = () => {
    if (!popularPairs?.success || !popularPairs.data) {
      return [];
    }

    return popularPairs.data.map(pair => {
      const wsData = realTimeData.get(pair.symbol);
      return {
        ...pair,
        // Use WebSocket data if available, otherwise use API data
        price: wsData?.price || pair.price,
        change_percent_24h: wsData?.priceChangePercent || pair.change_percent_24h || 0,
        volume_24h: wsData?.volume || pair.volume_24h,
        isRealTime: !!wsData
      };
    });
  };

  // Table columns for popular pairs
  const pairColumns = [
    {
      title: 'Symbol',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (symbol: string, record: any) => (
        <Space>
          <Button
            type="link"
            onClick={() => setSelectedSymbol(symbol)}
            style={{ padding: 0, fontWeight: selectedSymbol === symbol ? 'bold' : 'normal' }}
          >
            {symbol}
          </Button>
          {record.isRealTime && (
            <Badge
              status="success"
              text=""
              style={{ marginLeft: 4 }}
              title="Real-time data"
            />
          )}
        </Space>
      ),
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => formatCurrency(price),
    },
    {
      title: '24h Change',
      key: 'change',
      render: (_: any, record: any) => {
        const change = record.change_percent_24h || 0;
        return (
          <span style={{ color: change >= 0 ? '#52c41a' : '#ff4d4f' }}>
            {change >= 0 ? '+' : ''}{formatPercentage(change)}
          </span>
        );
      },
    },
    {
      title: 'Volume',
      dataIndex: 'volume_24h',
      key: 'volume_24h',
      render: (volume: number) => volume ? formatCurrency(volume) : '-',
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: TickerData) => (
        <Space>
          <Button size="small" type="primary" onClick={() => openOrderModal('BUY')}>
            Buy
          </Button>
          <Button size="small" onClick={() => openOrderModal('SELL')}>
            Sell
          </Button>
        </Space>
      ),
    },
  ];

  // Table columns for open orders
  const orderColumns = [
    {
      title: 'Symbol',
      dataIndex: 'symbol',
      key: 'symbol',
    },
    {
      title: 'Side',
      dataIndex: 'side',
      key: 'side',
      render: (side: string) => (
        <Tag color={side === 'BUY' ? 'green' : 'red'}>
          {side}
        </Tag>
      ),
    },
    {
      title: 'Type',
      dataIndex: 'type',
      key: 'type',
    },
    {
      title: 'Quantity',
      dataIndex: 'quantity',
      key: 'quantity',
      render: (quantity: any) => {
        const numQuantity = typeof quantity === 'number' ? quantity : parseFloat(quantity) || 0;
        return numQuantity.toFixed(6);
      },
    },
    {
      title: 'Price',
      dataIndex: 'price',
      key: 'price',
      render: (price: any) => {
        if (!price) return 'Market';
        const numPrice = typeof price === 'number' ? price : parseFloat(price) || 0;
        return formatCurrency(numPrice);
      },
    },
    {
      title: 'Filled',
      dataIndex: 'executed_qty',
      key: 'executed_qty',
      render: (executed: any) => {
        const numExecuted = typeof executed === 'number' ? executed : parseFloat(executed) || 0;
        return numExecuted.toFixed(6);
      },
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Tag color={status === 'FILLED' ? 'green' : status === 'CANCELLED' ? 'red' : 'blue'}>
          {status}
        </Tag>
      ),
    },
    {
      title: 'Action',
      key: 'action',
      render: (_: any, record: OrderInfo) => (
        <Button
          size="small"
          danger
          onClick={() => handleCancelOrder(record.symbol, record.order_id)}
          disabled={record.status === 'FILLED' || record.status === 'CANCELLED'}
          loading={cancelOrderMutation.isPending}
        >
          Cancel
        </Button>
      ),
    },
  ];

  // Get current price from WebSocket if available, otherwise from API
  const getCurrentPrice = () => {
    const wsData = realTimeData.get(selectedSymbol);
    if (wsData) {
      return wsData.price;
    }

    return tickerData?.success && tickerData.data
      ? tickerData.data.find(t => t.symbol === selectedSymbol)?.price || 0
      : 0;
  };

  const currentPrice = getCurrentPrice();
  const selectedWsData = realTimeData.get(selectedSymbol);

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title level={2} style={{ margin: 0 }}>
          Trading
        </Title>
        <Space>
          <Badge
            status={wsConnected ? 'success' : 'error'}
            text={
              <span style={{ fontSize: '12px' }}>
                {wsConnected ? 'Live' : 'Offline'}
              </span>
            }
          />
          <Select
            value={selectedSymbol}
            onChange={setSelectedSymbol}
            style={{ width: 120 }}
            loading={loadingPairs}
          >
            {popularPairs?.success && popularPairs.data?.map((pair) => (
              <Option key={pair.symbol} value={pair.symbol}>
                {pair.symbol}
              </Option>
            ))}
          </Select>
          <Space>
            <Text strong>{formatCurrency(currentPrice)}</Text>
            {selectedWsData && (
              <Badge
                status="success"
                title="Real-time price"
              />
            )}
          </Space>
        </Space>
      </div>

      {/* Quick Stats */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="Current Price"
              value={currentPrice}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="24h Change"
              value={tickerData?.success && tickerData.data
                ? tickerData.data.find(t => t.symbol === selectedSymbol)?.change_percent_24h || 0
                : 0}
              formatter={(value) => formatPercentage(Number(value))}
              prefix={
                (tickerData?.success && tickerData.data
                  ? tickerData.data.find(t => t.symbol === selectedSymbol)?.change_percent_24h || 0
                  : 0) >= 0
                ? <RiseOutlined style={{ color: '#52c41a' }} />
                : <FallOutlined style={{ color: '#ff4d4f' }} />
              }
              valueStyle={{
                color: (tickerData?.success && tickerData.data
                  ? tickerData.data.find(t => t.symbol === selectedSymbol)?.change_percent_24h || 0
                  : 0) >= 0 ? '#52c41a' : '#ff4d4f'
              }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card>
            <Statistic
              title="24h Volume"
              value={tickerData?.success && tickerData.data
                ? tickerData.data.find(t => t.symbol === selectedSymbol)?.volume_24h || 0
                : 0}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<LineChartOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Trading Interface */}
      <Row gutter={[16, 16]}>
        {/* Market Data */}
        <Col xs={24} lg={16}>
          <Card title="Popular Trading Pairs" className="h-full">
            <Table
              dataSource={getEnhancedPairData()}
              columns={pairColumns}
              rowKey="symbol"
              loading={loadingPairs}
              pagination={{ pageSize: 10 }}
              size="small"
              locale={{
                emptyText: 'No trading pairs available'
              }}
            />
          </Card>
        </Col>

        {/* Quick Order */}
        <Col xs={24} lg={8}>
          <Card title="Quick Order" className="h-full">
            <Space direction="vertical" size="large" className="w-full">
              <div>
                <Text strong>Symbol: </Text>
                <Text>{selectedSymbol}</Text>
              </div>
              <div>
                <Text strong>Price: </Text>
                <Text>{formatCurrency(currentPrice)}</Text>
              </div>
              <Space direction="vertical" size="middle" className="w-full">
                <Button
                  type="primary"
                  size="large"
                  block
                  icon={<ShoppingCartOutlined />}
                  onClick={() => openOrderModal('BUY')}
                >
                  Buy {selectedSymbol.replace('USDT', '')}
                </Button>
                <Button
                  danger
                  size="large"
                  block
                  icon={<StopOutlined />}
                  onClick={() => openOrderModal('SELL')}
                >
                  Sell {selectedSymbol.replace('USDT', '')}
                </Button>
              </Space>
            </Space>
          </Card>
        </Col>
      </Row>

      {/* Open Orders */}
      <Card title="Open Orders">
        <Table
          dataSource={openOrders?.success ? openOrders.data : []}
          columns={orderColumns}
          rowKey="order_id"
          loading={loadingOrders}
          pagination={{ pageSize: 10 }}
        />
      </Card>

      {/* Order Modal */}
      <Modal
        title={`${orderType} ${selectedSymbol}`}
        open={orderModalVisible}
        onCancel={() => setOrderModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={placeOrderMutation.isPending}
        okText="Place Order"
        cancelText="Cancel"
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handlePlaceOrder}
          initialValues={{
            symbol: selectedSymbol,
            side: orderType,
            type: 'LIMIT',
            quantity: 0,
            price: currentPrice,
          }}
        >
          <Form.Item name="symbol" label="Symbol">
            <Input disabled />
          </Form.Item>

          <Form.Item name="side" label="Side">
            <Select disabled>
              <Option value="BUY">BUY</Option>
              <Option value="SELL">SELL</Option>
            </Select>
          </Form.Item>

          <Form.Item name="type" label="Order Type">
            <Select>
              <Option value="MARKET">Market</Option>
              <Option value="LIMIT">Limit</Option>
            </Select>
          </Form.Item>

          <Form.Item
            name="quantity"
            label="Quantity"
            rules={[
              { required: true, message: 'Please enter quantity' },
              { type: 'number', min: 0.000001, message: 'Quantity must be greater than 0' }
            ]}
          >
            <InputNumber
              style={{ width: '100%' }}
              placeholder="0.000000"
              step={0.000001}
              precision={6}
            />
          </Form.Item>

          <Form.Item
            noStyle
            shouldUpdate={(prevValues, currentValues) =>
              prevValues.type !== currentValues.type
            }
          >
            {({ getFieldValue }) =>
              getFieldValue('type') === 'LIMIT' && (
                <Form.Item
                  name="price"
                  label="Price"
                  rules={[
                    { required: true, message: 'Please enter price' },
                    { type: 'number', min: 0.01, message: 'Price must be greater than 0' }
                  ]}
                >
                  <InputNumber
                    style={{ width: '100%' }}
                    placeholder="0.00"
                    step={0.01}
                    precision={2}
                  />
                </Form.Item>
              )
            }
          </Form.Item>

{/* Removed test mode alert - LIVE TRADING ONLY */}
        </Form>
      </Modal>
    </div>
  );
};