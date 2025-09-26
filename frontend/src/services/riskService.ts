// Risk Management API Service
// AI 기반 리스크 관리 API 서비스

import {
  RiskCalculationRequest,
  RiskCalculationResponse,
  PortfolioRiskAssessment,
  OptimalStopLossRequest,
  OptimalStopLossResponse,
  MultiScenarioRequest,
  MultiScenarioResponse,
  LeverageOptions,
  RiskPresets
} from '../types/risk.types';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1';

class RiskService {
  private async makeRequest<T>(url: string, options?: RequestInit): Promise<T> {
    const token = localStorage.getItem('auth_token');

    const response = await fetch(`${API_BASE}${url}`, {
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options?.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
    }

    return response.json();
  }

  // AI 기반 포지션 사이징 계산
  async calculatePositionSize(request: RiskCalculationRequest): Promise<RiskCalculationResponse> {
    return this.makeRequest<RiskCalculationResponse>('/risk/calculate-position', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }


  // 여러 시나리오 계산
  async calculateMultipleScenarios(request: MultiScenarioRequest): Promise<MultiScenarioResponse> {
    return this.makeRequest<MultiScenarioResponse>('/risk/calculate-scenarios', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // 최적 손절가 범위 계산
  async getOptimalStopLossRange(request: OptimalStopLossRequest): Promise<OptimalStopLossResponse> {
    return this.makeRequest<OptimalStopLossResponse>('/risk/optimal-stop-range', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  }

  // 포트폴리오 리스크 평가
  async assessPortfolioRisk(): Promise<PortfolioRiskAssessment> {
    return this.makeRequest<PortfolioRiskAssessment>('/risk/assess-portfolio');
  }


  // 레버리지 옵션 조회
  async getLeverageOptions(): Promise<LeverageOptions> {
    return this.makeRequest<LeverageOptions>('/risk/leverage-options');
  }

  // 리스크 프리셋 조회
  async getRiskPresets(): Promise<RiskPresets> {
    return this.makeRequest<RiskPresets>('/risk/risk-presets');
  }
}

export const riskService = new RiskService();