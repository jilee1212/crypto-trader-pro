// Risk Management Types for Futures Trading
// AI 기반 리스크 관리 타입 정의

export interface RiskCalculationRequest {
  entry_price: number;
  stop_loss_price: number;
  risk_percentage: number;
  account_balance?: number;
}

export interface RiskCalculationResponse {
  // 기본 정보
  position_value: number;
  position_quantity: number;
  leverage: number;
  seed_usage_percent: number;
  margin_used: number;

  // 배율 정보
  actual_multiplier: number;
  target_multiplier: number;

  // 리스크 정보
  target_risk_amount: number;
  actual_risk_amount: number;
  risk_accuracy: number;
  risk_percentage: number;

  // 가격 정보
  entry_price: number;
  stop_loss_price: number;
  price_diff_percent: number;

  // 계좌 정보
  account_balance: number;
  remaining_balance: number;

  // 최적화 정보
  optimization_notes: string;
  is_optimal: boolean;

  // 경고 및 상태
  warnings: string[];
  risk_level: 'VERY_LOW' | 'LOW' | 'MEDIUM' | 'HIGH';
}

export interface PositionRiskAssessment {
  symbol: string;
  risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  margin_ratio: number;
  liquidation_distance: number;
  pnl_percent: number;
  alerts: string[];
  requires_action: boolean;
}

export interface PortfolioRiskAssessment {
  portfolio_risk_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  total_balance: number;
  total_unrealized_pnl: number;
  portfolio_pnl_percent: number;
  overall_margin_ratio: number;
  position_count: number;
  critical_positions: number;
  high_risk_positions: number;
  position_risks: PositionRiskAssessment[];
  requires_immediate_action: boolean;
  recommendation: string;
}

export interface OptimalStopData {
  leverage: number;
  stop_loss_price: number;
  price_diff_percent: number;
}

export interface OptimalStopLossRequest {
  entry_price: number;
  risk_percentage: number;
  account_balance: number;
  min_leverage: number;
  max_leverage: number;
}

export interface OptimalStopLossResponse {
  entry_price: number;
  optimal_stops: OptimalStopData[];
  risk_amount: number;
  risk_percentage: number;
}

export interface LeverageOptions {
  available_leverages: number[];
  recommended_max: number;
  safety_max: number;
  risk_levels: {
    VERY_LOW: number[];
    LOW: number[];
    MEDIUM: number[];
    HIGH: number[];
    VERY_HIGH: number[];
  };
}

export interface RiskPreset {
  risk_percentage: number;
  max_leverage: number;
  description: string;
}

export interface RiskPresets {
  conservative: RiskPreset;
  moderate: RiskPreset;
  aggressive: RiskPreset;
  high_risk: RiskPreset;
}

export interface MultiScenarioRequest {
  entry_price: number;
  stop_loss_prices: number[];
  risk_percentage: number;
  account_balance: number;
}

export interface MultiScenarioResponse {
  entry_price: number;
  scenarios: Record<string, RiskCalculationResponse>;
  account_balance: number;
  risk_percentage: number;
}

// AI Signal Types
export interface FuturesAISignal {
  symbol: string;
  action: 'LONG' | 'SHORT' | 'CLOSE';
  entry_price: number;
  stop_loss_price: number;
  take_profit_price?: number;
  confidence: number;
  reasoning: string;
  risk_reward_ratio?: number;
}

export interface AutoTradingRequest {
  signal: FuturesAISignal;
  risk_percentage: number;
  max_leverage: number;
  enable_stop_loss: boolean;
  enable_take_profit: boolean;
}

// UI State Types
export interface RiskCalculatorState {
  entryPrice: string;
  stopLossPrice: string;
  riskPercentage: number;
  accountBalance: string;
  isCalculating: boolean;
  result: RiskCalculationResponse | null;
  error: string | null;
}

export interface PortfolioMonitorState {
  isLoading: boolean;
  assessment: PortfolioRiskAssessment | null;
  lastUpdate: string | null;
  error: string | null;
}

// Validation Types
export interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}