/**
 * Utility functions for formatting data
 */

/**
 * Format number as currency
 */
export const formatCurrency = (
  value: number,
  currency = 'USD',
  decimals = 2
): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

/**
 * Format number with commas
 */
export const formatNumber = (
  value: number,
  decimals = 2
): string => {
  return new Intl.NumberFormat('en-US', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
};

/**
 * Format percentage
 */
export const formatPercentage = (
  value: number,
  decimals = 2
): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'percent',
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value / 100);
};

/**
 * Format date/time
 */
export const formatDateTime = (
  date: string | Date,
  options?: Intl.DateTimeFormatOptions
): string => {
  const dateObj = typeof date === 'string' ? new Date(date) : date;

  const defaultOptions: Intl.DateTimeFormatOptions = {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    ...options,
  };

  return new Intl.DateTimeFormat('en-US', defaultOptions).format(dateObj);
};

/**
 * Format date only
 */
export const formatDate = (date: string | Date): string => {
  return formatDateTime(date, {
    hour: undefined,
    minute: undefined,
  });
};

/**
 * Format time only
 */
export const formatTime = (date: string | Date): string => {
  return formatDateTime(date, {
    year: undefined,
    month: undefined,
    day: undefined,
  });
};

/**
 * Truncate text with ellipsis
 */
export const truncateText = (text: string, maxLength: number): string => {
  if (text.length <= maxLength) return text;
  return text.substring(0, maxLength) + '...';
};

/**
 * Format crypto amount with appropriate decimals
 */
export const formatCrypto = (
  amount: number,
  symbol: string,
  maxDecimals = 8
): string => {
  const decimals = amount < 1 ? maxDecimals : amount < 10 ? 4 : 2;
  return `${formatNumber(amount, decimals)} ${symbol.toUpperCase()}`;
};