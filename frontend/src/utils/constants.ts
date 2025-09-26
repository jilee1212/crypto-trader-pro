/**
 * Application constants
 */

export const APP_CONFIG = {
  APP_NAME: 'Crypto Trader Pro',
  API_BASE_URL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  WS_BASE_URL: import.meta.env.VITE_WS_URL || 'ws://localhost:8000',
  VERSION: '1.0.0',
};

export const ROUTES = {
  HOME: '/',
  LOGIN: '/login',
  REGISTER: '/register',
  DASHBOARD: '/dashboard',
  TRADING: '/trading',
  FUTURES: '/futures',
  PORTFOLIO: '/portfolio',
  MARKET: '/market',
  SETTINGS: '/settings',
} as const;

export const STORAGE_KEYS = {
  AUTH_TOKENS: 'auth_tokens',
  USER: 'user',
  THEME: 'theme',
  PREFERENCES: 'preferences',
} as const;

export const API_ENDPOINTS = {
  AUTH: {
    LOGIN: '/auth/login',
    REGISTER: '/auth/register',
    REFRESH: '/auth/refresh',
    ME: '/auth/me',
  },
  USERS: {
    PROFILE: '/users/me',
    API_KEYS: '/users/me/api-keys',
  },
} as const;

export const THEME_CONFIG = {
  PRIMARY_COLOR: '#1890ff',
  SUCCESS_COLOR: '#52c41a',
  ERROR_COLOR: '#ff4d4f',
  WARNING_COLOR: '#faad14',
  BORDER_RADIUS: 6,
};