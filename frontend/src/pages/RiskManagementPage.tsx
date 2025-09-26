import React, { useState } from 'react';
import { AIRiskCalculator, PortfolioRiskMonitor } from '../components/risk';

type TabType = 'calculator' | 'monitor';

export const RiskManagementPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('calculator');

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-6">
        {/* Page Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🛡️ AI 리스크 관리 시스템
          </h1>
          <p className="text-gray-600">
            선물 거래를 위한 지능형 포지션 사이징 및 실시간 리스크 모니터링
          </p>
        </div>

        {/* Tab Navigation */}
        <div className="mb-6">
          <div className="border-b border-gray-200">
            <nav className="-mb-px flex space-x-8">
              <button
                onClick={() => setActiveTab('calculator')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'calculator'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                🧮 AI 포지션 계산기
              </button>
              <button
                onClick={() => setActiveTab('monitor')}
                className={`py-2 px-1 border-b-2 font-medium text-sm ${
                  activeTab === 'monitor'
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                ⚡ 포트폴리오 모니터
              </button>
            </nav>
          </div>
        </div>

        {/* Tab Content */}
        <div className="tab-content">
          {activeTab === 'calculator' && (
            <div>
              <AIRiskCalculator
                useMockAPI={false} // Use live API for real trading
                onResultUpdate={(result) => {
                  if (result) {
                    console.log('Risk calculation result:', result);
                  }
                }}
              />

              <div className="mt-8 p-6 bg-blue-50 border border-blue-200 rounded-lg">
                <h3 className="text-lg font-bold text-blue-800 mb-2">
                  💡 AI 포지션 계산기 사용법
                </h3>
                <div className="text-blue-700 space-y-2">
                  <p>• <strong>진입가와 손절가</strong>를 정확히 입력하세요</p>
                  <p>• <strong>리스크 비율</strong>은 전체 자금 대비 위험을 감수할 비율입니다</p>
                  <p>• AI가 최적의 <strong>레버리지와 포지션 크기</strong>를 계산합니다</p>
                  <p>• <strong>리스크 프리셋</strong>을 활용해 빠른 설정이 가능합니다</p>
                  <p>• 계산 결과의 <strong>경고사항</strong>을 반드시 확인하세요</p>
                </div>
              </div>
            </div>
          )}

          {activeTab === 'monitor' && (
            <div>
              <PortfolioRiskMonitor
                useMockAPI={false} // Use live API for real trading
                refreshInterval={30} // Refresh every 30 seconds
              />

              <div className="mt-8 p-6 bg-yellow-50 border border-yellow-200 rounded-lg">
                <h3 className="text-lg font-bold text-yellow-800 mb-2">
                  ⚠️ 리스크 모니터링 가이드
                </h3>
                <div className="text-yellow-700 space-y-2">
                  <p>• <strong>CRITICAL</strong> 레벨은 즉시 조치가 필요한 상태입니다</p>
                  <p>• <strong>청산가까지 거리</strong>가 15% 미만인 경우 주의하세요</p>
                  <p>• <strong>마진 비율</strong>이 75%를 초과하면 위험 수준입니다</p>
                  <p>• 자동 업데이트로 실시간 모니터링이 가능합니다</p>
                  <p>• 포지션별 상세 분석을 통해 개별 관리하세요</p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer Information */}
        <div className="mt-12 p-6 bg-gray-50 border border-gray-200 rounded-lg">
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div>
              <h4 className="font-bold text-gray-800 mb-2">🎯 정밀한 리스크 계산</h4>
              <p className="text-sm text-gray-600">
                AI 기반 알고리즘으로 최적의 레버리지와 포지션 크기를 계산하여
                정확한 리스크 관리를 지원합니다.
              </p>
            </div>
            <div>
              <h4 className="font-bold text-gray-800 mb-2">⚡ 실시간 모니터링</h4>
              <p className="text-sm text-gray-600">
                포트폴리오 전체와 개별 포지션의 리스크를 실시간으로 모니터링하여
                위험 상황을 즉시 감지합니다.
              </p>
            </div>
            <div>
              <h4 className="font-bold text-gray-800 mb-2">🛡️ 자동 경고 시스템</h4>
              <p className="text-sm text-gray-600">
                위험 수준이 임계치를 넘으면 자동으로 경고를 발생시켜
                적시에 대응할 수 있도록 합니다.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};