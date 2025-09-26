/**
 * API related TypeScript types
 */

export interface ApiResponse<T = any> {
  data?: T;
  message?: string;
  success: boolean;
  error?: string;
}

export interface PaginationParams {
  page?: number;
  limit?: number;
  offset?: number;
}

export interface ApiError {
  detail: string | Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
  status_code: number;
}

export interface HealthCheck {
  status: string;
  environment: string;
}