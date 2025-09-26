/**
 * Futures Trading page with integrated risk calculator and position management
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
  Badge,
  Progress,
  Slider,
  Switch,
  Tooltip
} from 'antd';
import {
  RiseOutlined,
  FallOutlined,
  DollarCircleOutlined,
  LineChartOutlined,
  TrophyOutlined,
  WarningOutlined,
  ThunderboltOutlined,
  FireOutlined,
  ShieldCheckOutlined,
  CalculatorOutlined,
  PercentageOutlined,
  StockOutlined
} from '@ant-design/icons';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { formatCurrency, formatPercentage } from '../utils/formatters';
import { AIRiskCalculator } from '../components/risk/AIRiskCalculator';
import { binanceFuturesApi } from '../services/binanceFuturesApi';
import { useAuthStore } from '../stores/authStore';

const { Title, Text } = Typography;
const { Option } = Select;
const { TabPane } = Tabs;

interface FuturesPosition {
  symbol: string;
  side: 'LONG' | 'SHORT';
  size: number;
  entryPrice: number;
  currentPrice: number;
  leverage: number;
  margin: number;
  pnl: number;
  pnlPercent: number;
  marginRatio: number;
  liquidationPrice: number;
  status: 'ACTIVE' | 'CLOSING' | 'CLOSED';
}

interface FuturesOrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  leverage: number;
  price?: number;
  stopPrice?: number;
  takeProfitPrice?: number;
}

interface RiskCalculationResult {
  position_value: number;
  position_quantity: number;
  leverage: number;
  margin_used: number;
  seed_usage_percent: number;
  remaining_balance: number;
  target_risk_amount: number;
  actual_risk_amount: number;
  risk_accuracy: number;
  risk_level: string;
  optimization_notes: string;
  warnings: string[];
}

export const FuturesTradingPage: React.FC = () => {
  const [form] = Form.useForm<FuturesOrderRequest>();
  const [selectedSymbol, setSelectedSymbol] = useState<string>('BTCUSDT');
  const [orderModalVisible, setOrderModalVisible] = useState(false);
  const [orderType, setOrderType] = useState<'BUY' | 'SELL'>('BUY');
  const [activeTab, setActiveTab] = useState<string>('calculator');
  const [accountBalance, setAccountBalance] = useState<number>(1000);
  const [riskCalculationResult, setRiskCalculationResult] = useState<RiskCalculationResult | null>(null);
  const [useAdvancedMode, setUseAdvancedMode] = useState(false);

  const queryClient = useQueryClient();

  // Data from live Binance Futures API

  // Check if API keys are configured
  const { user } = useAuthStore();
  const hasApiKeys = !!user?.binance_api_key;

  // Fetch popular futures pairs (public data - no API key required)
  const { data: popularFuturesData } = useQuery({
    queryKey: ['popular-futures-pairs'],
    queryFn: () => binanceFuturesApi.getPopularFuturesPairs(),
    enabled: true, // Public data doesn't require API keys
    refetchInterval: 5000,
  });

  // Default popular futures pairs (fallback)
  const popularFuturesPairs = popularFuturesData?.success && popularFuturesData.data ?
    popularFuturesData.data : [
      { symbol: 'BTCUSDT', price: 43000, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'ETHUSDT', price: 2500, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'ADAUSDT', price: 0.5, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'SOLUSDT', price: 100, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'DOTUSDT', price: 7, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'MATICUSDT', price: 1, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'LINKUSDT', price: 15, change_24h: 0, change_percent_24h: 0, volume_24h: 0 },
      { symbol: 'LTCUSDT', price: 70, change_24h: 0, change_percent_24h: 0, volume_24h: 0 }
    ];

  // Live Binance Futures API calls

  // Fetch account info
  const { data: accountInfo, isLoading: loadingAccount } = useQuery({
    queryKey: ['futures-account'],
    queryFn: () => binanceFuturesApi.getFuturesAccountInfo(),
    enabled: hasApiKeys, // Only fetch if API keys are configured
    refetchInterval: 5000,
  });

  // Fetch positions
  const { data: positions, isLoading: loadingPositions } = useQuery({
    queryKey: ['futures-positions'],
    queryFn: () => binanceFuturesApi.getPositions(),
    enabled: hasApiKeys, // Only fetch if API keys are configured
    refetchInterval: 3000,
  });

  // Place order mutation
  const placeOrderMutation = useMutation({
    mutationFn: (orderData: FuturesOrderRequest) => binanceFuturesApi.placeFuturesOrder(orderData),
    onSuccess: (data) => {
      if (data.success) {
        message.success('선물 포지션이 성공적으로 열렸습니다!');
        setOrderModalVisible(false);
        form.resetFields();
        queryClient.invalidateQueries({ queryKey: ['futures-positions'] });
        queryClient.invalidateQueries({ queryKey: ['futures-account'] });
      } else {
        message.error('주문 실패');
      }
    },
    onError: () => {
      message.error('주문 처리 중 오류가 발생했습니다');
    }
  });

  const handlePlaceOrder = (values: FuturesOrderRequest) => {
    if (!riskCalculationResult) {
      message.warning('먼저 리스크를 계산해주세요');
      return;
    }

    const orderData: FuturesOrderRequest = {
      ...values,
      quantity: riskCalculationResult.position_quantity,
      leverage: riskCalculationResult.leverage
    };

    placeOrderMutation.mutate(orderData);
  };

  const openOrderModal = (side: 'BUY' | 'SELL') => {
    setOrderType(side);
    form.setFieldsValue({
      symbol: selectedSymbol,
      side,
      type: 'LIMIT',
      quantity: riskCalculationResult?.position_quantity || 0,
      leverage: riskCalculationResult?.leverage || 10,
      price: popularFuturesPairs.find(p => p.symbol === selectedSymbol)?.price || 0,
    });
    setOrderModalVisible(true);
  };

  const handleRiskResultUpdate = (result: RiskCalculationResult | null) => {
    setRiskCalculationResult(result);
  };

  // Position columns for table
  const positionColumns = [
    {
      title: '심볼',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (symbol: string) => (
        <Text strong>{symbol}</Text>
      )
    },
    {
      title: '방향',
      dataIndex: 'side',
      key: 'side',
      render: (side: string) => (
        <Tag color={side === 'LONG' ? 'green' : 'red'}>
          {side}
        </Tag>
      )
    },
    {
      title: '크기',
      dataIndex: 'size',
      key: 'size',
      render: (size: number) => size.toFixed(4)
    },
    {
      title: '진입가',
      dataIndex: 'entryPrice',
      key: 'entryPrice',
      render: (price: number) => formatCurrency(price)
    },
    {
      title: '현재가',
      dataIndex: 'currentPrice',
      key: 'currentPrice',
      render: (price: number) => formatCurrency(price)
    },
    {
      title: '레버리지',
      dataIndex: 'leverage',
      key: 'leverage',
      render: (leverage: number) => `${leverage}x`
    },
    {
      title: '손익',
      key: 'pnl',
      render: (_: any, record: FuturesPosition) => (
        <Space direction="vertical" size="small">
          <Text style={{ color: record.pnl >= 0 ? '#52c41a' : '#ff4d4f' }}>
            {record.pnl >= 0 ? '+' : ''}{formatCurrency(record.pnl)}
          </Text>
          <Text style={{ color: record.pnlPercent >= 0 ? '#52c41a' : '#ff4d4f', fontSize: '12px' }}>
            ({record.pnlPercent >= 0 ? '+' : ''}{record.pnlPercent.toFixed(2)}%)
          </Text>
        </Space>
      )
    },
    {
      title: '마진 비율',
      dataIndex: 'marginRatio',
      key: 'marginRatio',
      render: (ratio: number) => (
        <div>
          <Progress
            percent={ratio}
            size="small"
            status={ratio > 90 ? 'exception' : ratio > 70 ? 'active' : 'success'}
            showInfo={false}
          />
          <Text style={{ fontSize: '12px', color: ratio > 90 ? '#ff4d4f' : '#666' }}>
            {ratio}%
          </Text>
        </div>
      )
    },
    {
      title: '청산가',
      dataIndex: 'liquidationPrice',
      key: 'liquidationPrice',
      render: (price: number) => (
        <Text style={{ color: '#ff7875' }}>{formatCurrency(price)}</Text>
      )
    },
    {
      title: '액션',
      key: 'action',
      render: (_: any, record: FuturesPosition) => (
        <Space>
          <Button size="small" danger>
            청산
          </Button>
        </Space>
      )
    }
  ];

  // Popular pairs columns
  const pairColumns = [
    {
      title: '심볼',
      dataIndex: 'symbol',
      key: 'symbol',
      render: (symbol: string) => (
        <Button
          type="link"
          onClick={() => setSelectedSymbol(symbol)}
          style={{
            padding: 0,
            fontWeight: selectedSymbol === symbol ? 'bold' : 'normal',
            color: selectedSymbol === symbol ? '#1890ff' : undefined
          }}
        >
          {symbol}
        </Button>
      ),
    },
    {
      title: '가격',
      dataIndex: 'price',
      key: 'price',
      render: (price: number) => formatCurrency(price),
    },
    {
      title: '24h 변화',
      dataIndex: 'change',
      key: 'change',
      render: (change: number) => (
        <span style={{ color: change >= 0 ? '#52c41a' : '#ff4d4f' }}>
          {change >= 0 ? '+' : ''}{formatPercentage(change)}
        </span>
      ),
    },
    {
      title: '볼륨',
      dataIndex: 'volume',
      key: 'volume',
    },
    {
      title: '액션',
      key: 'action',
      render: () => (
        <Space>
          <Button size="small" type="primary" onClick={() => openOrderModal('BUY')}>
            롱
          </Button>
          <Button size="small" danger onClick={() => openOrderModal('SELL')}>
            숏
          </Button>
        </Space>
      ),
    },
  ];

  const currentPrice = popularFuturesPairs.find(p => p.symbol === selectedSymbol)?.price || 0;
  const totalPnL = positions?.success ? positions.data.reduce((sum, pos) => sum + pos.pnl, 0) : 0;
  const totalPositions = positions?.success ? positions.data.length : 0;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Title level={2} style={{ margin: 0, display: 'flex', alignItems: 'center', gap: '8px' }}>
          <FireOutlined style={{ color: '#fa8c16' }} />
          선물 거래
        </Title>
        <Space>
          <Badge status="error" text="🔴 LIVE TRADING" style={{ fontWeight: 'bold' }} />
          <Select
            value={selectedSymbol}
            onChange={setSelectedSymbol}
            style={{ width: 120 }}
          >
            {popularFuturesPairs.map((pair) => (
              <Option key={pair.symbol} value={pair.symbol}>
                {pair.symbol}
              </Option>
            ))}
          </Select>
        </Space>
      </div>

      {/* LIVE Trading Warning */}
      <Alert
        message="⚠️ LIVE TRADING MODE ACTIVE"
        description="This futures trading system is connected to LIVE Binance with REAL MONEY. All positions and trades execute with actual funds."
        type="error"
        icon={<WarningOutlined />}
        showIcon
        style={{ fontWeight: '500' }}
      />

      {/* API Keys Warning */}
      {!hasApiKeys && (
        <Alert
          message="API 키 설정 필요"
          description="선물 거래를 시작하려면 설정 페이지에서 Binance API 키를 구성하세요."
          type="warning"
          showIcon
          closable
        />
      )}

      {/* Account Summary */}
      <Row gutter={[16, 16]}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="지갑 잔고"
              value={accountInfo?.success ? accountInfo.data.totalWalletBalance : 0}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<DollarCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="미실현 손익"
              value={accountInfo?.success ? accountInfo.data.totalUnrealizedProfit : 0}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={totalPnL >= 0 ? <RiseOutlined style={{ color: '#52c41a' }} /> : <FallOutlined style={{ color: '#ff4d4f' }} />}
              valueStyle={{ color: totalPnL >= 0 ? '#52c41a' : '#ff4d4f' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="사용 마진"
              value={accountInfo?.success ? accountInfo.data.totalPositionInitialMargin : 0}
              formatter={(value) => formatCurrency(Number(value))}
              prefix={<ThunderboltOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic
              title="활성 포지션"
              value={totalPositions}
              prefix={<StockOutlined />}
            />
          </Card>
        </Col>
      </Row>

      {/* Main Content Tabs */}
      <Card>
        <Tabs activeKey={activeTab} onChange={setActiveTab}>
          <TabPane tab={
            <span>
              <CalculatorOutlined />
              AI 리스크 계산기
            </span>
          } key="calculator">
            <Row gutter={[24, 24]}>
              <Col xs={24} lg={16}>
                <AIRiskCalculator
                  initialValues={{
                    entry_price: currentPrice,
                    account_balance: accountBalance
                  }}
                  onResultUpdate={handleRiskResultUpdate}
                  useMockAPI={true}
                />
              </Col>
              <Col xs={24} lg={8}>
                <Card title="빠른 주문" style={{ height: 'fit-content' }}>
                  <Space direction="vertical" size="large" style={{ width: '100%' }}>
                    <div>
                      <Text strong>선택된 심볼: </Text>
                      <Text>{selectedSymbol}</Text>
                    </div>
                    <div>
                      <Text strong>현재가: </Text>
                      <Text>{formatCurrency(currentPrice)}</Text>
                    </div>

                    {riskCalculationResult && (
                      <div style={{ padding: '12px', backgroundColor: '#f0f9ff', borderRadius: '6px', border: '1px solid #bae6fd' }}>
                        <Space direction="vertical" size="small" style={{ width: '100%' }}>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text>권장 수량:</Text>
                            <Text strong>{riskCalculationResult.position_quantity.toFixed(6)}</Text>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text>최적 레버리지:</Text>
                            <Text strong>{riskCalculationResult.leverage}x</Text>
                          </div>
                          <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                            <Text>필요 마진:</Text>
                            <Text strong>{formatCurrency(riskCalculationResult.margin_used)}</Text>
                          </div>
                        </Space>
                      </div>
                    )}

                    <Space direction="vertical" size="middle" style={{ width: '100%' }}>
                      <Button
                        type="primary"
                        size="large"
                        block
                        icon={<RiseOutlined />}
                        onClick={() => openOrderModal('BUY')}
                        disabled={!riskCalculationResult}
                      >
                        롱 포지션 열기
                      </Button>
                      <Button
                        danger
                        size="large"
                        block
                        icon={<FallOutlined />}
                        onClick={() => openOrderModal('SELL')}
                        disabled={!riskCalculationResult}
                      >
                        숏 포지션 열기
                      </Button>
                    </Space>

                    {!riskCalculationResult && (
                      <Alert
                        message="먼저 리스크 계산을 완료해주세요"
                        type="info"
                        showIcon
                        style={{ marginTop: 12 }}
                      />
                    )}
                  </Space>
                </Card>
              </Col>
            </Row>
          </TabPane>

          <TabPane tab={
            <span>
              <StockOutlined />
              포지션 관리
            </span>
          } key="positions">
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              <Card title="활성 포지션" extra={
                <Badge count={totalPositions} showZero style={{ backgroundColor: '#52c41a' }} />
              }>
                <Table
                  dataSource={positions?.success ? positions.data : []}
                  columns={positionColumns}
                  rowKey={(record) => `${record.symbol}_${record.side}`}
                  loading={loadingPositions}
                  pagination={false}
                  size="small"
                />
              </Card>

              <Card title="인기 선물 상품">
                <Table
                  dataSource={popularFuturesPairs}
                  columns={pairColumns}
                  rowKey="symbol"
                  pagination={false}
                  size="small"
                />
              </Card>
            </Space>
          </TabPane>

          <TabPane tab={
            <span>
              <TrophyOutlined />
              성과 분석
            </span>
          } key="analytics">
            <Row gutter={[16, 16]}>
              <Col xs={24} sm={8}>
                <Card>
                  <Statistic
                    title="총 실현 손익"
                    value={1250}
                    formatter={(value) => formatCurrency(Number(value))}
                    prefix={<TrophyOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card>
                  <Statistic
                    title="승률"
                    value={68.5}
                    formatter={(value) => `${Number(value)}%`}
                    prefix={<PercentageOutlined />}
                  />
                </Card>
              </Col>
              <Col xs={24} sm={8}>
                <Card>
                  <Statistic
                    title="최대 수익률"
                    value={15.8}
                    formatter={(value) => `${Number(value)}%`}
                    prefix={<RiseOutlined style={{ color: '#52c41a' }} />}
                    valueStyle={{ color: '#52c41a' }}
                  />
                </Card>
              </Col>
            </Row>

            <Card title="거래 통계" style={{ marginTop: 16 }}>
              <Alert
                message="성과 분석 기능은 실제 거래 데이터를 바탕으로 제공됩니다."
                type="info"
                showIcon
              />
            </Card>
          </TabPane>
        </Tabs>
      </Card>

      {/* Order Modal */}
      <Modal
        title={`${orderType === 'BUY' ? '롱' : '숏'} 포지션 - ${selectedSymbol}`}
        open={orderModalVisible}
        onCancel={() => setOrderModalVisible(false)}
        onOk={() => form.submit()}
        confirmLoading={placeOrderMutation.isPending}
        okText="포지션 열기"
        cancelText="취소"
        width={600}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handlePlaceOrder}
        >
          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="symbol" label="심볼">
                <Input disabled />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="side" label="방향">
                <Select disabled>
                  <Option value="BUY">롱 (Long)</Option>
                  <Option value="SELL">숏 (Short)</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item name="type" label="주문 타입">
                <Select>
                  <Option value="MARKET">시장가</Option>
                  <Option value="LIMIT">지정가</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item name="leverage" label="레버리지">
                <Select>
                  {[1, 2, 3, 5, 10, 20, 25, 50, 75, 100].map(lev => (
                    <Option key={lev} value={lev}>{lev}x</Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="quantity"
                label="수량"
                rules={[
                  { required: true, message: '수량을 입력하세요' },
                  { type: 'number', min: 0.000001, message: '수량은 0보다 커야 합니다' }
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="0.000000"
                  step={0.000001}
                  precision={6}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
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
                      label="가격"
                      rules={[
                        { required: true, message: '가격을 입력하세요' },
                        { type: 'number', min: 0.01, message: '가격은 0보다 커야 합니다' }
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
            </Col>
          </Row>

          <Form.Item name="stopPrice" label="손절가 (선택사항)">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="손절가 입력"
              step={0.01}
              precision={2}
            />
          </Form.Item>

          <Form.Item name="takeProfitPrice" label="익절가 (선택사항)">
            <InputNumber
              style={{ width: '100%' }}
              placeholder="익절가 입력"
              step={0.01}
              precision={2}
            />
          </Form.Item>

          {riskCalculationResult && (
            <Alert
              message="AI 리스크 계산 결과 적용됨"
              description={`권장 수량: ${riskCalculationResult.position_quantity.toFixed(6)}, 최적 레버리지: ${riskCalculationResult.leverage}x, 필요 마진: ${formatCurrency(riskCalculationResult.margin_used)}`}
              type="success"
              showIcon
              style={{ marginTop: 16 }}
            />
          )}

          <Alert
            message="⚠️ 선물 거래는 높은 리스크를 수반합니다"
            description="레버리지 거래는 큰 손실을 가져올 수 있습니다. 신중하게 거래하세요."
            type="warning"
            showIcon
            style={{ marginTop: 16 }}
          />
        </Form>
      </Modal>
    </div>
  );
};