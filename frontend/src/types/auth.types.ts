/**
 * Authentication related TypeScript types
 */

export interface User {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  is_active: boolean;
  is_verified: boolean;
  // testnet removed - LIVE TRADING ONLY
  max_daily_loss_percent: string;
  max_position_size_percent: string;
  binance_api_key?: string;
  binance_api_secret?: string;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthTokens {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface AuthState {
  user: User | null;
  tokens: AuthTokens | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
}

export interface APIKeyUpdate {
  binance_api_key?: string;
  binance_api_secret?: string;
  // testnet removed - LIVE TRADING ONLY
}