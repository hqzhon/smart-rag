import React, { useEffect, useState, createContext } from 'react';
import { BrowserRouter as Router, Routes, Route, useLocation } from 'react-router-dom';
import { ThemeProvider } from '@mui/material/styles';
import { CssBaseline, Box, IconButton, Tooltip, Fade, Grow } from '@mui/material';
import { Brightness4, Brightness7 } from '@mui/icons-material';
import { QueryClient, QueryClientProvider } from 'react-query';
import { ReactQueryDevtools } from 'react-query/devtools';
import { AnimatedBox, HoverAnimatedBox } from '@/components/animations';

import ChatPage from '@/pages/ChatPage';
import TestUpload from '@/pages/TestUpload';
import FileManagementPage from '@/pages/FileManagementPage';
import HistoryPage from '@/pages/HistoryPage';

import Navigation from '@/components/Navigation';
import { useChatStore } from '@/stores/chatStore';
import { createAppTheme } from './theme';
import AccessibilityProvider from '@/components/AccessibilityProvider';

// Theme context for managing light/dark mode
interface ThemeContextType {
  mode: 'light' | 'dark';
  toggleTheme: () => void;
}

const ThemeContext = createContext<ThemeContextType>({
  mode: 'light',
  toggleTheme: () => {},
});

// const useThemeMode = () => useContext(ThemeContext);

// 带动画的路由组件
const AnimatedRoutes: React.FC = () => {
  const location = useLocation();
  
  return (
    <AnimatedBox animation="fadeInUp" duration="0.6s">
      <Fade in timeout={600}>
        <Box sx={{ flex: 1, overflow: 'auto' }}>
          <Routes location={location}>
            <Route path="/" element={<FileManagementPage />} />
            <Route path="/files" element={<FileManagementPage />} />
            <Route path="/chat/:sessionId?" element={<ChatPage />} />
            <Route path="/history" element={<HistoryPage />} />
            <Route path="/test-upload" element={<TestUpload />} />

          </Routes>
        </Box>
      </Fade>
    </AnimatedBox>
  );
};

// 创建React Query客户端
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

const App: React.FC = () => {
  const [themeMode, setThemeMode] = useState<'light' | 'dark'>('light');

  const toggleTheme = () => {
    setThemeMode(prev => prev === 'light' ? 'dark' : 'light');
  };

  const theme = createAppTheme(themeMode);

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeContext.Provider value={{ mode: themeMode, toggleTheme }}>
        <ThemeProvider theme={theme}>
          <CssBaseline />
          <AccessibilityProvider>
            <Router future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
              <AnimatedBox animation="fadeInUp" duration="0.8s">
                <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
                  <Navigation />
                  <Box sx={{ position: 'fixed', top: 16, right: 16, zIndex: 1000 }}>
                    <HoverAnimatedBox hoverAnimation="scale">
                      <Grow in timeout={800}>
                        <Tooltip title={`切换到${themeMode === 'light' ? '深色' : '浅色'}模式`}>
                          <IconButton 
                            onClick={toggleTheme} 
                            color="inherit"
                            aria-label={`切换到${themeMode === 'light' ? '深色' : '浅色'}模式`}
                            sx={{
                              background: 'rgba(255, 255, 255, 0.1)',
                              backdropFilter: 'blur(10px)',
                              border: '1px solid rgba(255, 255, 255, 0.2)',
                              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                              '&:hover': {
                                background: 'rgba(255, 255, 255, 0.2)',
                                transform: 'scale(1.1) rotate(180deg)',
                                boxShadow: '0 8px 32px rgba(0, 0, 0, 0.2)',
                              },
                            }}
                          >
                            <AnimatedBox 
                              animation={themeMode === 'light' ? 'pulse' : 'pulse'} 
                              duration="2s"
                            >
                              {themeMode === 'light' ? <Brightness4 /> : <Brightness7 />}
                            </AnimatedBox>
                          </IconButton>
                        </Tooltip>
                      </Grow>
                    </HoverAnimatedBox>
                  </Box>
                  <AnimatedRoutes />
                </Box>
              </AnimatedBox>
            </Router>
          </AccessibilityProvider>
          <ReactQueryDevtools initialIsOpen={false} />
        </ThemeProvider>
      </ThemeContext.Provider>
    </QueryClientProvider>
  );
};

export default App;