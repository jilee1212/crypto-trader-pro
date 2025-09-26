/**
 * Binance API service
 */

import { apiClient } from './api';

export interface ApiKeysRequest {
  api_key: string;
  api_secret: string;
  // testnet removed - LIVE TRADING ONLY
}

export interface ApiTestResponse {
  success: boolean;
  message?: string;
  error?: string;
  trading_mode: string; // Always "LIVE"
  can_trade?: boolean;
  can_withdraw?: boolean;
  can_deposit?: boolean;
  account_type?: string;
}

export interface BalanceInfo {
  asset: string;
  free: number;
  locked: number;
}

export interface AccountInfoResponse {
  success: boolean;
  data?: {
    can_trade: boolean;
    can_withdraw: boolean;
    can_deposit: boolean;
    account_type: string;
    balances: BalanceInfo[];
  };
  error?: string;
}

export interface TickerData {
  symbol: string;
  price: number;
  change_24h?: number;
  change_percent_24h?: number;
  volume_24h?: number;
}

export interface MarketDataResponse {
  success: boolean;
  data?: TickerData[];
  error?: string;
}

export interface KlineData {
  open_time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  close_time: number;
  quote_asset_volume: number;
  number_of_trades: number;
  taker_buy_base_asset_volume: number;
  taker_buy_quote_asset_volume: number;
}

export interface OrderRequest {
  symbol: string;
  side: 'BUY' | 'SELL';
  type: 'MARKET' | 'LIMIT';
  quantity: number;
  price?: number;
  time_in_force?: 'GTC' | 'IOC' | 'FOK';
}

export interface OrderInfo {
  order_id: number;
  symbol: string;
  status: string;
  type: string;
  side: string;
  quantity: number;
  price?: number;
  executed_qty: number;
  cumulative_quote_qty?: number;
  time: number;
}

export interface OrderResponse {
  success: boolean;
  data?: OrderInfo;
  message?: string;
  error?: string;
  error_code?: number;
}

class BinanceApiService {
  /**
   * Configure Binance API keys
   */
  async configureApiKeys(keys: ApiKeysRequest): Promise<ApiTestResponse> {
    const response = await apiClient.post<ApiTestResponse>('/binance/configure-keys', keys);
    return response.data;
  }

  /**
   * Test API connection
   */
  async testConnection(): Promise<ApiTestResponse> {
    const response = await apiClient.get<ApiTestResponse>('/binance/test-connection');
    return response.data;
  }

  /**
   * Get account information
   */
  async getAccountInfo(): Promise<AccountInfoResponse> {
    const response = await apiClient.get<AccountInfoResponse>('/binance/account');
    return response.data;
  }

  /**
   * Get ticker prices for all symbols or specific symbol
   */
  async getTickerPrices(symbol?: string): Promise<MarketDataResponse> {
    const params = symbol ? { symbol } : {};
    const response = await apiClient.get<MarketDataResponse>('/binance/ticker/prices', { params });
    return response.data;
  }

  /**
   * Get 24hr ticker statistics
   */
  async get24hrTicker(symbol?: string): Promise<MarketDataResponse> {
    const params = symbol ? { symbol } : {};
    const response = await apiClient.get<MarketDataResponse>('/binance/ticker/24hr', { params });
    return {
      success: response.data.success,
      data: Array.isArray(response.data.data) ? response.data.data.map((item: any) => ({
        symbol: item.symbol,
        price: item.last_price,
        change_24h: item.price_change,
        change_percent_24h: item.price_change_percent,
        volume_24h: item.volume
      })) : response.data.data ? [{
        symbol: response.data.data.symbol,
        price: response.data.data.last_price,
        change_24h: response.data.data.price_change,
        change_percent_24h: response.data.data.price_change_percent,
        volume_24h: response.data.data.volume
      }] : [],
      error: response.data.error
    };
  }

  /**
   * Get kline/candlestick data
   */
  async getKlines(
    symbol: string,
    interval: string = '1h',
    limit: number = 100
  ): Promise<{ success: boolean; data?: KlineData[]; error?: string }> {
    const response = await apiClient.get('/binance/klines', {
      params: { symbol, interval, limit }
    });
    return response.data;
  }

  /**
   * Place a new order
   */
  async placeOrder(order: OrderRequest): Promise<OrderResponse> {
    const response = await apiClient.post<OrderResponse>('/binance/order', order);
    return response.data;
  }

  /**
   * Get open orders
   */
  async getOpenOrders(symbol?: string): Promise<{ success: boolean; data?: OrderInfo[]; error?: string }> {
    const params = symbol ? { symbol } : {};
    const response = await apiClient.get('/binance/orders/open', { params });
    return response.data;
  }

  /**
   * Cancel an order
   */
  async cancelOrder(symbol: string, orderId: number): Promise<{ success: boolean; data?: any; error?: string }> {
    try {
      const response = await apiClient.delete('/binance/order', {
        data: { symbol, order_id: orderId }
      });
      return response.data;
    } catch (error: any) {
      console.warn('Cancel order failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Failed to cancel order'
      };
    }
  }

  /**
   * Get popular trading pairs
   */
  async getPopularPairs(): Promise<{ success: boolean; data?: TickerData[]; error?: string }> {
    const response = await apiClient.get('/binance/popular-pairs');
    return {
      success: response.data.success,
      data: response.data.data?.map((item: any) => ({
        symbol: item.symbol,
        price: item.price,
        change_24h: item.change_24h,
        change_percent_24h: item.change_percent_24h,
        volume_24h: item.volume_24h
      })),
      error: response.data.error
    };
  }

  /**
   * Check if user has API keys configured
   */
  async checkApiStatus(): Promise<{ hasApiKeys: boolean; testnet: boolean; error?: string }> {
    try {
      const response = await this.testConnection();
      return {
        hasApiKeys: response.success,
        testnet: response.testnet || false,
        error: response.error
      };
    } catch (error: any) {
      const errorMessage = error?.response?.data?.detail || error?.message || 'Failed to check API status';
      return {
        hasApiKeys: false,
        testnet: false,
        error: errorMessage
      };
    }
  }

  /**
   * Emergency stop - cancel all orders and liquidate all positions
   */
  async emergencyStop(): Promise<{ success: boolean; message?: string; data?: any; error?: string }> {
    try {
      const response = await apiClient.post('/binance/emergency-stop');
      return response.data;
    } catch (error: any) {
      console.error('Emergency stop failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Emergency stop failed'
      };
    }
  }

  /**
   * Cancel all open orders
   */
  async cancelAllOrders(): Promise<{ success: boolean; message?: string; data?: any; error?: string }> {
    try {
      const response = await apiClient.post('/binance/cancel-all-orders');
      return response.data;
    } catch (error: any) {
      console.error('Cancel all orders failed:', error?.response?.data?.detail);
      return {
        success: false,
        error: error?.response?.data?.detail || 'Cancel all orders failed'
      };
    }
  }
}

export const binanceApi = new BinanceApiService();