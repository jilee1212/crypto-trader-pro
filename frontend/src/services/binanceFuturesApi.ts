/**
 * Binance Futures API service - USDT-M Futures Trading
 */

import { apiClient } from './api';

// Futures API Types
export interface FuturesApiKeysRequest {
  api_key: string;
  api_secret: string;
  // testnet removed - LIVE TRADING ONLY
}

export interface FuturesTestResponse {
  success: boolean;
  message?: string;
  error?: string;
  trading_mode: string; // Always "LIVE"
  can_trade?: boolean;
  can_withdraw?: boolean;
  can_deposit?: boolean;
  account_type?: string;
  total_wallet_balance?: number;
  total_unrealized_pnl?: number;
}

export interface FuturesBalance {
  asset: string;
  wallet_balance: number;
  unrealized_profit: number;
  margin_balance: number;
  available_balance: number;
  max_withdraw_amount: number;
}

export interface FuturesAccountInfo {
  success: boolean;
  data?: {
    can_trade: boolean;
    can_withdraw: boolean;
    can_deposit: boolean;
    account_type: string;
    total_wallet_balance: number;
    total_unrealized_pnl: number;
    total_margin_balance: number;
    available_balance: number;
    max_withdraw_amount: number;
    balances: FuturesBalance[];
  };
  error?: string;
}

export interface PositionInfo {
  symbol: string;
  position_amt: number;
  entry_price: number;
  mark_price: number;
  unrealized_pnl: number;
  percentage: number;
  side: 'LONG' | 'SHORT';
  leverage: number;
  margin_type: 'cross' | 'isolated';
  isolated_margin: number;
  liquidation_price?: number;
}

export interface PositionsResponse {
  success: boolean;
  data?: PositionInfo[];
  error?: string;
}

export interface FuturesTickerData {
  symbol: string;
  price_change: number;
  price_change_percent: number;
  last_price: number;
  high_price: number;
  low_price: number;
  volume: number;
  quote_volume: number;
  count: number;
  open_interest: number;
}

export interface FuturesMarketDataResponse {
  success: boolean;
  data?: FuturesTickerData[];
  error?: string;
}

export interface FuturesOrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT' | 'STOP' | 'STOP_MARKET' | 'TAKE_PROFIT' | 'TAKE_PROFIT_MARKET';
  quantity?: number;
  price?: number;
  time_in_force?: 'GTC' | 'IOC' | 'FOK' | 'GTX';
  reduce_only?: boolean;
  close_position?: boolean;
  stop_price?: number;
  working_type?: 'MARK_PRICE' | 'CONTRACT_PRICE';
}

export interface FuturesOrderInfo {
  order_id: number;
  symbol: string;
  status: string;
  type: string;
  side: string;
  quantity: number;
  price?: number;
  executed_qty: number;
  cumulative_quote_qty: number;
  time: number;
  reduce_only: boolean;
  close_position: boolean;
}

export interface FuturesOrderResponse {
  success: boolean;
  data?: FuturesOrderInfo;
  message?: string;
  error?: string;
  error_code?: number;
}

export interface LeverageRequest {
  symbol: string;
  leverage: number;
}

export interface LeverageResponse {
  success: boolean;
  data?: {
    symbol: string;
    leverage: number;
    max_notional_value: string;
  };
  error?: string;
}

export interface MarginTypeRequest {
  symbol: string;
  margin_type: 'ISOLATED' | 'CROSSED';
}

export interface MarginTypeResponse {
  success: boolean;
  data?: {
    symbol: string;
    margin_type: string;
  };
  message?: string;
  error?: string;
}

class BinanceFuturesApiService {
  /**
   * Configure Binance Futures API keys
   */
  async configureFuturesKeys(keys: FuturesApiKeysRequest): Promise<FuturesTestResponse> {
    const response = await apiClient.post<FuturesTestResponse>('/binance/futures/configure-keys', keys);
    return response.data;
  }

  /**
   * Test Futures API connection
   */
  async testFuturesConnection(): Promise<FuturesTestResponse> {
    const response = await apiClient.get<FuturesTestResponse>('/binance/futures/test-connection');
    return response.data;
  }

  /**
   * Get futures account information
   */
  async getFuturesAccountInfo(): Promise<FuturesAccountInfo> {
    const response = await apiClient.get<FuturesAccountInfo>('/binance/futures/account');
    return response.data;
  }

  /**
   * Get current positions
   */
  async getPositions(): Promise<PositionsResponse> {
    const response = await apiClient.get<PositionsResponse>('/binance/futures/positions');
    return response.data;
  }

  /**
   * Get futures 24hr ticker statistics
   */
  async getFutures24hrTicker(symbol?: string): Promise<FuturesMarketDataResponse> {
    const params = symbol ? { symbol } : {};
    const response = await apiClient.get<FuturesMarketDataResponse>('/binance/futures/ticker/24hr', { params });
    return response.data;
  }

  /**
   * Place a futures order
   */
  async placeFuturesOrder(order: FuturesOrderRequest): Promise<FuturesOrderResponse> {
    const response = await apiClient.post<FuturesOrderResponse>('/binance/futures/order', order);
    return response.data;
  }

  /**
   * Get open futures orders
   */
  async getOpenFuturesOrders(symbol?: string): Promise<{ success: boolean; data?: FuturesOrderInfo[]; error?: string }> {
    const params = symbol ? { symbol } : {};
    const response = await apiClient.get('/binance/futures/orders/open', { params });
    return response.data;
  }

  /**
   * Cancel a futures order
   */
  async cancelFuturesOrder(symbol: string, orderId: number): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      const response = await apiClient.delete('/binance/futures/order', {
        params: { symbol, order_id: orderId }
      });
      return response.data;
    } catch (error: any) {
      console.warn('Cancel futures order failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Failed to cancel futures order'
      };
    }
  }

  /**
   * Set leverage for a symbol
   */
  async setLeverage(symbol: string, leverage: number): Promise<LeverageResponse> {
    const response = await apiClient.post<LeverageResponse>('/binance/futures/leverage', {
      symbol,
      leverage
    });
    return response.data;
  }

  /**
   * Set margin type for a symbol
   */
  async setMarginType(symbol: string, marginType: 'ISOLATED' | 'CROSSED'): Promise<MarginTypeResponse> {
    const response = await apiClient.post<MarginTypeResponse>('/binance/futures/margin-type', {
      symbol,
      margin_type: marginType
    });
    return response.data;
  }

  /**
   * Emergency stop - cancel all futures orders and close all positions
   */
  async emergencyStopFutures(): Promise<{ success: boolean; message?: string; data?: any; error?: string }> {
    try {
      const response = await apiClient.post('/binance/futures/emergency-stop');
      return response.data;
    } catch (error: any) {
      console.error('Futures emergency stop failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Futures emergency stop failed'
      };
    }
  }

  /**
   * Cancel all open futures orders
   */
  async cancelAllFuturesOrders(): Promise<{ success: boolean; message?: string; data?: any; error?: string }> {
    try {
      const response = await apiClient.post('/binance/futures/cancel-all-orders');
      return response.data;
    } catch (error: any) {
      console.error('Cancel all futures orders failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Cancel all futures orders failed'
      };
    }
  }

  /**
   * Get popular futures trading pairs
   */
  async getPopularFuturesPairs(): Promise<{ success: boolean; data?: any[]; error?: string }> {
    const response = await apiClient.get('/binance/futures/popular-pairs');
    return response.data;
  }

  /**
   * Get exchange information
   */
  async getFuturesExchangeInfo(): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      const response = await apiClient.get('/binance/futures/exchange-info');
      return response.data;
    } catch (error: any) {
      console.warn('Get futures exchange info failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Failed to get futures exchange info'
      };
    }
  }

  /**
   * Check if user has futures API keys configured
   */
  async checkFuturesApiStatus(): Promise<{ hasApiKeys: boolean; testnet: boolean }> {
    try {
      const response = await this.testFuturesConnection();
      return {
        hasApiKeys: response.success,
        testnet: false // Always false for live trading
      };
    } catch (error) {
      return {
        hasApiKeys: false,
        testnet: false
      };
    }
  }
}

export const binanceFuturesApi = new BinanceFuturesApiService();