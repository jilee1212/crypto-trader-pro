/**
 * Error Boundary component to catch JavaScript errors and prevent app crashes
 */

import React from 'react';
import { Result, Button } from 'antd';

interface ErrorBoundaryState {
  hasError: boolean;
  error?: Error;
}

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    // Update state so the next render will show the fallback UI
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    // Log error for debugging
    console.error('Error Boundary caught an error:', error);
    console.error('Error Info:', errorInfo);
  }

  handleReload = () => {
    window.location.reload();
  };

  render() {
    if (this.state.hasError) {
      return (
        <div style={{ padding: '24px' }}>
          <Result
            status="error"
            title="Something went wrong"
            subTitle={
              process.env.NODE_ENV === 'development'
                ? `Error: ${this.state.error?.message}`
                : 'An unexpected error occurred while rendering this component.'
            }
            extra={[
              <Button type="primary" onClick={this.handleReload} key="reload">
                Reload Page
              </Button>,
              <Button key="console">
                Check Console for Details
              </Button>,
            ]}
          />
        </div>
      );
    }

    return this.props.children;
  }
}