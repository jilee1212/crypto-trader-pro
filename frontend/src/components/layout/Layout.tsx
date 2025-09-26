/**
 * Main layout component
 */

import React, { useState, useEffect } from 'react';
import { Layout as AntLayout } from 'antd';
import { Header } from './Header';
import { Sidebar } from './Sidebar';

const { Content, Sider } = AntLayout;

interface LayoutProps {
  children: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ children }) => {
  const [collapsed, setCollapsed] = useState(false);

  // Handle responsive collapse
  useEffect(() => {
    const handleResize = () => {
      if (window.innerWidth < 1024) {
        setCollapsed(true);
      } else {
        setCollapsed(false);
      }
    };

    // Initial check
    handleResize();

    // Add event listener
    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => window.removeEventListener('resize', handleResize);
  }, []);

  const toggleCollapse = () => {
    setCollapsed(!collapsed);
  };

  return (
    <AntLayout style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header - fixed at top */}
      <Header collapsed={collapsed} onToggle={toggleCollapse} />

      {/* Body with sidebar and content - horizontal layout */}
      <AntLayout style={{ flex: 1, display: 'flex', flexDirection: 'row' }}>
        {/* Sidebar - fixed width */}
        <Sider
          trigger={null}
          collapsible
          collapsed={collapsed}
          width={240}
          collapsedWidth={80}
          style={{
            height: 'calc(100vh - 64px)',
            backgroundColor: '#fff',
            boxShadow: '2px 0 8px rgba(0,0,0,0.1)',
            position: 'fixed',
            left: 0,
            top: 64,
            zIndex: 100
          }}
        >
          <Sidebar collapsed={collapsed} />
        </Sider>

        {/* Main content area - takes remaining space */}
        <Content
          style={{
            marginLeft: collapsed ? 80 : 240,
            padding: '24px',
            minHeight: 'calc(100vh - 64px)',
            backgroundColor: '#f5f5f5',
            transition: 'margin-left 0.3s ease'
          }}
        >
          <div
            style={{
              minHeight: '100%',
              backgroundColor: '#fff',
              padding: '24px',
              borderRadius: '8px',
              boxShadow: '0 2px 8px rgba(0,0,0,0.1)'
            }}
          >
            {children}
          </div>
        </Content>
      </AntLayout>
    </AntLayout>
  );
};