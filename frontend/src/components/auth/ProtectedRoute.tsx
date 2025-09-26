/**
 * Protected route component for authenticated users
 */

import React, { useEffect } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Spin } from 'antd';
import { useAuthStore } from '../../stores/authStore';
import { ROUTES } from '../../utils/constants';

interface ProtectedRouteProps {
  children: React.ReactNode;
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ children }) => {
  const location = useLocation();
  const { isAuthenticated, isLoading, user, initializeAuth } = useAuthStore();

  // Initialize auth on component mount
  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  // Show loading spinner while initializing
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <Spin size="large" />
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated || !user) {
    return (
      <Navigate
        to={ROUTES.LOGIN}
        state={{ from: location.pathname }}
        replace
      />
    );
  }

  // Render protected content
  return <>{children}</>;
};