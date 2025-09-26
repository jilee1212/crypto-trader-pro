import React, { useState, useEffect } from 'react';
import { riskService } from '../../services/riskService';
import {
  RiskCalculationRequest,
  RiskCalculationResponse,
  RiskPresets,
  LeverageOptions,
  ValidationResult
} from '../../types/risk.types';

interface AIRiskCalculatorProps {
  initialValues?: Partial<RiskCalculationRequest>;
  onResultUpdate?: (result: RiskCalculationResponse | null) => void;
  useMockAPI?: boolean;
}

export const AIRiskCalculator: React.FC<AIRiskCalculatorProps> = ({
  initialValues = {},
  onResultUpdate,
  useMockAPI = false
}) => {
  const [formData, setFormData] = useState<RiskCalculationRequest>({
    entry_price: initialValues.entry_price || 0,
    stop_loss_price: initialValues.stop_loss_price || 0,
    risk_percentage: initialValues.risk_percentage || 3.0,
    account_balance: initialValues.account_balance || 1000
  });

  const [result, setResult] = useState<RiskCalculationResponse | null>(null);
  const [isCalculating, setIsCalculating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);

  const [presets, setPresets] = useState<RiskPresets | null>(null);
  const [leverageOptions, setLeverageOptions] = useState<LeverageOptions | null>(null);
  const [selectedPreset, setSelectedPreset] = useState<string>('moderate');

  // Load presets and leverage options on mount
  useEffect(() => {
    const loadStaticData = async () => {
      try {
        const [presetsData, leverageData] = await Promise.all([
          riskService.getRiskPresets(),
          riskService.getLeverageOptions()
        ]);
        setPresets(presetsData);
        setLeverageOptions(leverageData);
      } catch (err) {
        console.error('Failed to load static data:', err);
      }
    };
    loadStaticData();
  }, []);

  // Validate form data
  const validateForm = (): ValidationResult => {
    const errors: string[] = [];
    const warnings: string[] = [];

    if (formData.entry_price <= 0) {
      errors.push('진입가는 0보다 큰 값이어야 합니다');
    }

    if (formData.stop_loss_price <= 0) {
      errors.push('손절가는 0보다 큰 값이어야 합니다');
    }

    if (formData.entry_price === formData.stop_loss_price) {
      errors.push('진입가와 손절가는 다른 값이어야 합니다');
    }

    if (formData.risk_percentage < 0.1 || formData.risk_percentage > 10) {
      errors.push('리스크 비율은 0.1%~10% 범위여야 합니다');
    }

    if (formData.account_balance && formData.account_balance <= 0) {
      errors.push('계좌 잔고는 0보다 큰 값이어야 합니다');
    }

    // Price difference validation
    const priceDiff = Math.abs(formData.entry_price - formData.stop_loss_price);
    const priceDiffPercent = (priceDiff / formData.entry_price) * 100;

    if (priceDiffPercent > 20) {
      warnings.push('가격 차이가 20%를 초과합니다. 높은 리스크를 주의하세요.');
    }
    if (priceDiffPercent < 0.5) {
      warnings.push('가격 차이가 0.5% 미만입니다. 너무 타이트한 손절일 수 있습니다.');
    }

    if (formData.risk_percentage > 5) {
      warnings.push('5%를 초과하는 리스크는 고위험 거래입니다.');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  };

  // Handle form submission
  const handleCalculate = async () => {
    const validation = validateForm();
    setValidationError(validation.errors.length > 0 ? validation.errors.join(', ') : null);

    if (!validation.isValid) return;

    setIsCalculating(true);
    setError(null);

    try {
      const calculationResult = useMockAPI
        ? await riskService.calculatePositionSizeMock(formData)
        : await riskService.calculatePositionSize(formData);

      setResult(calculationResult);
      onResultUpdate?.(calculationResult);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '계산 중 오류가 발생했습니다';
      setError(errorMessage);
      setResult(null);
      onResultUpdate?.(null);
    } finally {
      setIsCalculating(false);
    }
  };

  // Handle preset selection
  const handlePresetSelect = (presetKey: string) => {
    if (!presets) return;

    const preset = presets[presetKey as keyof RiskPresets];
    setSelectedPreset(presetKey);
    setFormData(prev => ({
      ...prev,
      risk_percentage: preset.risk_percentage
    }));
  };

  // Handle input changes
  const handleInputChange = (field: keyof RiskCalculationRequest, value: number) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setValidationError(null);
  };

  // Get risk level styling
  const getRiskLevelColor = (level: string) => {
    switch (level) {
      case 'VERY_LOW': return 'text-green-600 bg-green-100';
      case 'LOW': return 'text-green-700 bg-green-200';
      case 'MEDIUM': return 'text-yellow-700 bg-yellow-200';
      case 'HIGH': return 'text-red-700 bg-red-200';
      default: return 'text-gray-600 bg-gray-200';
    }
  };

  const validation = validateForm();

  return (
    <div className="bg-white rounded-lg shadow-lg p-6">
      <h2 className="text-2xl font-bold mb-6 text-gray-800">
        🎯 AI 포지션 사이징 계산기
      </h2>

      {/* Risk Presets */}
      {presets && (
        <div className="mb-6">
          <h3 className="text-lg font-semibold mb-3">리스크 프리셋</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
            {Object.entries(presets).map(([key, preset]) => (
              <button
                key={key}
                onClick={() => handlePresetSelect(key)}
                className={`p-3 rounded border text-sm ${
                  selectedPreset === key
                    ? 'border-blue-500 bg-blue-50 text-blue-700'
                    : 'border-gray-300 hover:border-gray-400'
                }`}
              >
                <div className="font-medium">{preset.description.split(' - ')[0]}</div>
                <div className="text-xs text-gray-600">
                  {preset.risk_percentage}% / {preset.max_leverage}x
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input Form */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            진입 예상 가격 (USDT)
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.entry_price || ''}
            onChange={(e) => handleInputChange('entry_price', parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="예: 42000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            손절 가격 (USDT)
          </label>
          <input
            type="number"
            step="0.01"
            value={formData.stop_loss_price || ''}
            onChange={(e) => handleInputChange('stop_loss_price', parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="예: 40000"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            리스크 비율 (%)
          </label>
          <input
            type="number"
            step="0.1"
            min="0.1"
            max="10"
            value={formData.risk_percentage}
            onChange={(e) => handleInputChange('risk_percentage', parseFloat(e.target.value) || 3)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <div className="text-xs text-gray-500 mt-1">
            전체 자금 대비 위험을 감수할 비율
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            계좌 잔고 (USDT)
          </label>
          <input
            type="number"
            step="1"
            value={formData.account_balance || ''}
            onChange={(e) => handleInputChange('account_balance', parseFloat(e.target.value) || 0)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="예: 1000"
          />
        </div>
      </div>

      {/* Validation Warnings */}
      {validation.warnings.length > 0 && (
        <div className="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-md">
          <div className="text-sm text-yellow-800">
            ⚠️ 경고사항:
            <ul className="list-disc list-inside mt-1">
              {validation.warnings.map((warning, index) => (
                <li key={index}>{warning}</li>
              ))}
            </ul>
          </div>
        </div>
      )}

      {/* Validation Errors */}
      {validationError && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="text-sm text-red-800">❌ {validationError}</div>
        </div>
      )}

      {/* API Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
          <div className="text-sm text-red-800">오류: {error}</div>
        </div>
      )}

      {/* Calculate Button */}
      <button
        onClick={handleCalculate}
        disabled={isCalculating || !validation.isValid}
        className="w-full bg-blue-600 text-white py-3 px-4 rounded-md font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
      >
        {isCalculating ? '계산 중...' : '🧮 AI 포지션 계산'}
      </button>

      {/* Results Display */}
      {result && (
        <div className="mt-8 p-6 bg-gray-50 rounded-lg">
          <h3 className="text-xl font-bold mb-4 flex items-center">
            📊 계산 결과
            <span className={`ml-3 px-2 py-1 rounded text-xs ${getRiskLevelColor(result.risk_level)}`}>
              {result.risk_level}
            </span>
          </h3>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <div className="bg-white p-4 rounded border">
              <h4 className="font-medium text-gray-700">포지션 정보</h4>
              <div className="mt-2 space-y-1 text-sm">
                <div>포지션 가치: <span className="font-mono">${result.position_value.toLocaleString()}</span></div>
                <div>수량: <span className="font-mono">{result.position_quantity.toFixed(6)}</span></div>
                <div>레버리지: <span className="font-mono">{result.leverage}x</span></div>
              </div>
            </div>

            <div className="bg-white p-4 rounded border">
              <h4 className="font-medium text-gray-700">마진 정보</h4>
              <div className="mt-2 space-y-1 text-sm">
                <div>사용 마진: <span className="font-mono">${result.margin_used.toLocaleString()}</span></div>
                <div>시드 사용률: <span className="font-mono">{result.seed_usage_percent.toFixed(1)}%</span></div>
                <div>남은 잔고: <span className="font-mono">${result.remaining_balance.toLocaleString()}</span></div>
              </div>
            </div>

            <div className="bg-white p-4 rounded border">
              <h4 className="font-medium text-gray-700">리스크 분석</h4>
              <div className="mt-2 space-y-1 text-sm">
                <div>목표 리스크: <span className="font-mono">${result.target_risk_amount.toLocaleString()}</span></div>
                <div>실제 리스크: <span className="font-mono">${result.actual_risk_amount.toLocaleString()}</span></div>
                <div>정확도: <span className="font-mono">{result.risk_accuracy.toFixed(1)}%</span></div>
              </div>
            </div>
          </div>

          <div className="mt-4 p-4 bg-blue-50 rounded border border-blue-200">
            <div className="text-sm">
              <div className="font-medium text-blue-800">💡 최적화 결과</div>
              <div className="text-blue-700 mt-1">{result.optimization_notes}</div>
            </div>
          </div>

          {result.warnings.length > 0 && (
            <div className="mt-4 p-4 bg-yellow-50 rounded border border-yellow-200">
              <div className="text-sm text-yellow-800">
                ⚠️ 주의사항:
                <ul className="list-disc list-inside mt-1">
                  {result.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};