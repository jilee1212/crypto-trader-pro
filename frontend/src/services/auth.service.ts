/**
 * Authentication API service
 */

import { api } from './api';
import {
  User,
  LoginRequest,
  RegisterRequest,
  AuthTokens,
  APIKeyUpdate,
} from '../types/auth.types';

export const authService = {
  /**
   * Login user
   */
  login: async (credentials: LoginRequest): Promise<AuthTokens> => {
    return api.post<AuthTokens>('/auth/login', credentials);
  },

  /**
   * Register new user
   */
  register: async (userData: RegisterRequest): Promise<User> => {
    return api.post<User>('/auth/register', userData);
  },

  /**
   * Refresh access token
   */
  refreshToken: async (refreshToken: string): Promise<AuthTokens> => {
    return api.post<AuthTokens>('/auth/refresh', { refresh_token: refreshToken });
  },

  /**
   * Get current user profile
   */
  getCurrentUser: async (): Promise<User> => {
    return api.get<User>('/auth/me');
  },

  /**
   * Update user profile
   */
  updateProfile: async (updates: Partial<User>): Promise<User> => {
    return api.put<User>('/users/me', updates);
  },

  /**
   * Update API keys
   */
  updateApiKeys: async (apiKeys: APIKeyUpdate): Promise<{ message: string }> => {
    return api.post<{ message: string }>('/users/me/api-keys', apiKeys);
  },

  /**
   * Logout user (client-side)
   */
  logout: () => {
    localStorage.removeItem('auth_tokens');
    localStorage.removeItem('user');
  },

  /**
   * Check if user is authenticated
   */
  isAuthenticated: (): boolean => {
    const tokens = localStorage.getItem('auth_tokens');
    if (!tokens) return false;

    try {
      const { access_token } = JSON.parse(tokens);
      if (!access_token) return false;

      // Simple token expiry check (decode JWT payload)
      const payload = JSON.parse(atob(access_token.split('.')[1]));
      const currentTime = Math.floor(Date.now() / 1000);

      return payload.exp > currentTime;
    } catch {
      return false;
    }
  },

  /**
   * Get stored tokens
   */
  getStoredTokens: (): AuthTokens | null => {
    const tokens = localStorage.getItem('auth_tokens');
    return tokens ? JSON.parse(tokens) : null;
  },

  /**
   * Store tokens
   */
  storeTokens: (tokens: AuthTokens): void => {
    localStorage.setItem('auth_tokens', JSON.stringify(tokens));
  },

  /**
   * Get stored user
   */
  getStoredUser: (): User | null => {
    const user = localStorage.getItem('user');
    return user ? JSON.parse(user) : null;
  },

  /**
   * Store user
   */
  storeUser: (user: User): void => {
    localStorage.setItem('user', JSON.stringify(user));
  },
};