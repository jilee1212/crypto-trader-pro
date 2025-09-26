/**
 * Main App component with routing
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ConfigProvider } from 'antd';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ReactQueryDevtools } from '@tanstack/react-query-devtools';

// Components
import { Layout } from './components/layout/Layout';
import { ProtectedRoute } from './components/auth/ProtectedRoute';
import { ErrorBoundary } from './components/common/ErrorBoundary';

// Pages
import { LoginPage } from './pages/auth/LoginPage';
import { RegisterPage } from './pages/auth/RegisterPage';
import { DashboardPage } from './pages/DashboardPage';
import { TradingPage } from './pages/TradingPage';
import { FuturesTradingPage } from './pages/FuturesTradingPage';
import { PortfolioPage } from './pages/PortfolioPage';
import { SettingsPage } from './pages/SettingsPage';

// Utils
import { ROUTES, THEME_CONFIG } from './utils/constants';

// Create a client
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000, // 5 minutes
      gcTime: 10 * 60 * 1000, // 10 minutes (formerly cacheTime)
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

// Ant Design theme configuration
const antdTheme = {
  token: {
    colorPrimary: THEME_CONFIG.PRIMARY_COLOR,
    colorSuccess: THEME_CONFIG.SUCCESS_COLOR,
    colorError: THEME_CONFIG.ERROR_COLOR,
    colorWarning: THEME_CONFIG.WARNING_COLOR,
    borderRadius: THEME_CONFIG.BORDER_RADIUS,
  },
};

// Placeholder components for missing pages
const MarketPage = () => <div className="p-6"><h1 className="text-2xl">Market Page - Coming Soon</h1></div>;

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={antdTheme}>
        <Router>
          <Routes>
            {/* Public routes */}
            <Route path={ROUTES.LOGIN} element={<LoginPage />} />
            <Route path={ROUTES.REGISTER} element={<RegisterPage />} />

            {/* Protected routes */}
            <Route
              path={ROUTES.DASHBOARD}
              element={
                <ProtectedRoute>
                  <Layout>
                    <DashboardPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path={ROUTES.TRADING}
              element={
                <ProtectedRoute>
                  <Layout>
                    <ErrorBoundary>
                      <TradingPage />
                    </ErrorBoundary>
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path={ROUTES.FUTURES}
              element={
                <ProtectedRoute>
                  <Layout>
                    <ErrorBoundary>
                      <FuturesTradingPage />
                    </ErrorBoundary>
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path={ROUTES.PORTFOLIO}
              element={
                <ProtectedRoute>
                  <Layout>
                    <PortfolioPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path={ROUTES.MARKET}
              element={
                <ProtectedRoute>
                  <Layout>
                    <MarketPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            <Route
              path={ROUTES.SETTINGS}
              element={
                <ProtectedRoute>
                  <Layout>
                    <SettingsPage />
                  </Layout>
                </ProtectedRoute>
              }
            />

            {/* Default redirect */}
            <Route
              path={ROUTES.HOME}
              element={<Navigate to={ROUTES.DASHBOARD} replace />}
            />

            {/* Catch all route */}
            <Route
              path="*"
              element={<Navigate to={ROUTES.DASHBOARD} replace />}
            />
          </Routes>
        </Router>

        {/* React Query Devtools */}
        <ReactQueryDevtools initialIsOpen={false} />
      </ConfigProvider>
    </QueryClientProvider>
  );
}

export default App;