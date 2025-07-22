// Main layout component with sidebar and navigation

import React from 'react';
import { Box, useMediaQuery, useTheme } from '@mui/material';
import { useAppSelector } from '../../store/hooks';
import { selectSidebarOpen } from '../../store/slices/uiSlice';

import Sidebar from './Sidebar';
import TopBar from './TopBar';
import NotificationCenter from './NotificationCenter';

interface LayoutProps {
  children: React.ReactNode;
}

const Layout: React.FC<LayoutProps> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const sidebarOpen = useAppSelector(selectSidebarOpen);

  const sidebarWidth = 280;

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* Sidebar */}
      <Sidebar />
      
      {/* Main content area */}
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          display: 'flex',
          flexDirection: 'column',
          marginLeft: isMobile ? 0 : sidebarOpen ? `${sidebarWidth}px` : '64px',
          transition: theme.transitions.create(['margin'], {
            easing: theme.transitions.easing.sharp,
            duration: theme.transitions.duration.leavingScreen,
          }),
        }}
      >
        {/* Top navigation bar */}
        <TopBar />
        
        {/* Page content */}
        <Box
          sx={{
            flexGrow: 1,
            padding: theme.spacing(3),
            backgroundColor: 'background.default',
            minHeight: 'calc(100vh - 64px)', // Subtract top bar height
          }}
        >
          {children}
        </Box>
      </Box>

      {/* Notification center */}
      <NotificationCenter />
    </Box>
  );
};

export default Layout;