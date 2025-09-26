import React, { useState, useEffect } from 'react';
import { riskService } from '../../services/riskService';
import {
  PortfolioRiskAssessment,
  PositionRiskAssessment
} from '../../types/risk.types';

interface PortfolioRiskMonitorProps {
  refreshInterval?: number; // in seconds
  useMockAPI?: boolean;
}

export const PortfolioRiskMonitor: React.FC<PortfolioRiskMonitorProps> = ({
  refreshInterval = 30,
  useMockAPI = false
}) => {
  const [assessment, setAssessment] = useState<PortfolioRiskAssessment | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdate, setLastUpdate] = useState<string | null>(null);

  // Load portfolio assessment
  const loadAssessment = async () => {
    setIsLoading(true);
    setError(null);

    try {
      const result = useMockAPI
        ? await riskService.assessPortfolioRiskMock()
        : await riskService.assessPortfolioRisk();

      setAssessment(result);
      setLastUpdate(new Date().toLocaleString('ko-KR'));
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '포트폴리오 평가 중 오류가 발생했습니다';
      setError(errorMessage);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-refresh effect
  useEffect(() => {
    loadAssessment(); // Initial load

    const interval = setInterval(loadAssessment, refreshInterval * 1000);
    return () => clearInterval(interval);
  }, [refreshInterval, useMockAPI]);

  // Get risk level styling
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'text-green-600 bg-green-100 border-green-200';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-100 border-yellow-200';
      case 'HIGH': return 'text-orange-600 bg-orange-100 border-orange-200';
      case 'CRITICAL': return 'text-red-600 bg-red-100 border-red-200';
      default: return 'text-gray-600 bg-gray-100 border-gray-200';
    }
  };

  // Get PnL styling
  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600';
    if (pnl < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  // Format PnL display
  const formatPnL = (value: number, isPercentage = false) => {
    const sign = value >= 0 ? '+' : '';
    const suffix = isPercentage ? '%' : '';
    return `${sign}${value.toFixed(2)}${suffix}`;
  };

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-2xl font-bold text-gray-800">
            ⚡ 포트폴리오 리스크 모니터
          </h2>
          <button
            onClick={loadAssessment}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"
          >
            다시 시도
          </button>
        </div>
        <div className="p-4 bg-red-50 border border-red-200 rounded-md">
          <div className="text-red-800">❌ {error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl font-bold text-gray-800">
          ⚡ 포트폴리오 리스크 모니터
        </h2>
        <div className="flex items-center space-x-4">
          {lastUpdate && (
            <div className="text-sm text-gray-500">
              최근 업데이트: {lastUpdate}
            </div>
          )}
          <button
            onClick={loadAssessment}
            disabled={isLoading}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {isLoading ? '업데이트 중...' : '새로고침'}
          </button>
        </div>
      </div>

      {isLoading && !assessment && (
        <div className="flex justify-center items-center py-12">
          <div className="text-lg text-gray-600">📊 포트폴리오 분석 중...</div>
        </div>
      )}

      {assessment && (
        <>
          {/* Overall Portfolio Status */}
          <div className="mb-6">
            <div className={`p-4 rounded-lg border-2 ${getRiskLevelColor(assessment.portfolio_risk_level)}`}>
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-lg font-bold">
                    전체 리스크 레벨: {assessment.portfolio_risk_level}
                  </h3>
                  <p className="text-sm mt-1">{assessment.recommendation}</p>
                </div>
                {assessment.requires_immediate_action && (
                  <div className="text-red-600 font-bold text-lg">⚠️ 즉시 조치 필요</div>
                )}
              </div>
            </div>
          </div>

          {/* Portfolio Summary */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            <div className="bg-gray-50 p-4 rounded border">
              <h4 className="font-medium text-gray-700">총 잔고</h4>
              <div className="text-2xl font-bold mt-1">
                ${assessment.total_balance.toLocaleString()}
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded border">
              <h4 className="font-medium text-gray-700">미실현 손익</h4>
              <div className={`text-2xl font-bold mt-1 ${getPnLColor(assessment.total_unrealized_pnl)}`}>
                {formatPnL(assessment.total_unrealized_pnl)}
              </div>
              <div className={`text-sm ${getPnLColor(assessment.portfolio_pnl_percent)}`}>
                ({formatPnL(assessment.portfolio_pnl_percent, true)})
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded border">
              <h4 className="font-medium text-gray-700">마진 비율</h4>
              <div className="text-2xl font-bold mt-1">
                {assessment.overall_margin_ratio.toFixed(1)}%
              </div>
            </div>

            <div className="bg-gray-50 p-4 rounded border">
              <h4 className="font-medium text-gray-700">포지션 현황</h4>
              <div className="text-2xl font-bold mt-1">
                {assessment.position_count}개
              </div>
              {assessment.critical_positions > 0 && (
                <div className="text-sm text-red-600 mt-1">
                  위험 {assessment.critical_positions}개
                </div>
              )}
            </div>
          </div>

          {/* Individual Positions */}
          {assessment.position_risks.length > 0 && (
            <div>
              <h3 className="text-lg font-bold mb-4">개별 포지션 리스크</h3>
              <div className="space-y-3">
                {assessment.position_risks.map((position, index) => (
                  <PositionCard key={index} position={position} />
                ))}
              </div>
            </div>
          )}

          {/* No positions message */}
          {assessment.position_risks.length === 0 && (
            <div className="text-center py-8">
              <div className="text-gray-600">📈 현재 활성 포지션이 없습니다</div>
            </div>
          )}
        </>
      )}
    </div>
  );
};

// Individual Position Card Component
interface PositionCardProps {
  position: PositionRiskAssessment;
}

const PositionCard: React.FC<PositionCardProps> = ({ position }) => {
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'LOW': return 'text-green-600 bg-green-50 border-green-200';
      case 'MEDIUM': return 'text-yellow-600 bg-yellow-50 border-yellow-200';
      case 'HIGH': return 'text-orange-600 bg-orange-50 border-orange-200';
      case 'CRITICAL': return 'text-red-600 bg-red-50 border-red-200';
      default: return 'text-gray-600 bg-gray-50 border-gray-200';
    }
  };

  const getPnLColor = (pnl: number) => {
    if (pnl > 0) return 'text-green-600';
    if (pnl < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  return (
    <div className={`p-4 rounded border-2 ${getRiskLevelColor(position.risk_level)}`}>
      <div className="flex items-center justify-between mb-2">
        <h4 className="font-bold text-lg">{position.symbol}</h4>
        <div className="flex items-center space-x-2">
          <span className={`px-2 py-1 rounded text-xs font-medium ${getRiskLevelColor(position.risk_level)}`}>
            {position.risk_level}
          </span>
          {position.requires_action && (
            <span className="text-red-600 font-bold">⚠️</span>
          )}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 text-sm">
        <div>
          <div className="text-gray-600">마진 비율</div>
          <div className="font-medium">{position.margin_ratio.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-600">청산가까지</div>
          <div className="font-medium">{position.liquidation_distance.toFixed(1)}%</div>
        </div>
        <div>
          <div className="text-gray-600">수익률</div>
          <div className={`font-medium ${getPnLColor(position.pnl_percent)}`}>
            {position.pnl_percent >= 0 ? '+' : ''}{position.pnl_percent.toFixed(2)}%
          </div>
        </div>
      </div>

      {position.alerts.length > 0 && (
        <div className="mt-3 p-2 bg-yellow-50 border border-yellow-200 rounded">
          <div className="text-sm text-yellow-800">
            {position.alerts.map((alert, idx) => (
              <div key={idx}>⚠️ {alert}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};