import React, { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { Box, Typography, Fade } from '@mui/material';
import {
  KeyboardArrowUp as ArrowUpIcon,
  Accessibility as AccessibilityIcon,
} from '@mui/icons-material';
import { AccessibleButton } from './AccessibleButton';

interface AccessibilityContextType {
  isKeyboardNavigation: boolean;
  announceMessage: (message: string) => void;
  focusElement: (selector: string) => void;
  skipToContent: () => void;
}

const AccessibilityContext = createContext<AccessibilityContextType | undefined>(undefined);

export const useAccessibility = () => {
  const context = useContext(AccessibilityContext);
  if (!context) {
    throw new Error('useAccessibility must be used within AccessibilityProvider');
  }
  return context;
};

interface AccessibilityProviderProps {
  children: React.ReactNode;
}

export const AccessibilityProvider: React.FC<AccessibilityProviderProps> = ({ children }) => {
  const [isKeyboardNavigation, setIsKeyboardNavigation] = useState(false);
  const [announcements, setAnnouncements] = useState<string[]>([]);

  const [showBackToTop, setShowBackToTop] = useState(false);

  // 检测键盘导航
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Tab') {
        setIsKeyboardNavigation(true);
      }
    };

    const handleMouseDown = () => {
      setIsKeyboardNavigation(false);
    };

    document.addEventListener('keydown', handleKeyDown);
    document.addEventListener('mousedown', handleMouseDown);

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.removeEventListener('mousedown', handleMouseDown);
    };
  }, []);

  // 监听滚动以显示返回顶部按钮
  useEffect(() => {
    const handleScroll = () => {
      setShowBackToTop(window.scrollY > 300);
    };

    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Alt + S: 跳转到搜索
      if (e.altKey && e.key === 's') {
        e.preventDefault();
        focusElement('[data-testid="search-input"], input[type="search"]');
      }
      // Alt + M: 跳转到主要内容
      if (e.altKey && e.key === 'm') {
        e.preventDefault();
        skipToContent();
      }
      // Alt + N: 跳转到导航
      if (e.altKey && e.key === 'n') {
        e.preventDefault();
        focusElement('[role="navigation"], nav');
      }
      // Escape: 关闭模态框或返回
      if (e.key === 'Escape') {
        const activeElement = document.activeElement as HTMLElement;
        if (activeElement && activeElement.closest('[role="dialog"]')) {
          const closeButton = activeElement.closest('[role="dialog"]')?.querySelector('[aria-label*="关闭"], [aria-label*="close"]') as HTMLElement;
          closeButton?.click();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, []);

  const announceMessage = useCallback((message: string) => {
    setAnnouncements(prev => [...prev, message]);
    // 3秒后清除消息
    setTimeout(() => {
      setAnnouncements(prev => prev.slice(1));
    }, 3000);
  }, []);

  const focusElement = (selector: string) => {
    const element = document.querySelector(selector) as HTMLElement;
    if (element) {
      element.focus();
      element.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  };

  const skipToContent = () => {
    const mainContent = document.querySelector('main, [role="main"], #main-content') as HTMLElement;
    if (mainContent) {
      mainContent.focus();
      mainContent.scrollIntoView({ behavior: 'smooth' });
    }
  };

  const scrollToTop = () => {
    window.scrollTo({ top: 0, behavior: 'smooth' });
    announceMessage('已返回页面顶部');
  };

  const contextValue: AccessibilityContextType = {
    isKeyboardNavigation,
    announceMessage,
    focusElement,
    skipToContent,
  };

  return (
    <AccessibilityContext.Provider value={contextValue}>
      {/* 跳转链接 */}
      <Box
        sx={{
          position: 'fixed',
          top: -100,
          left: 20,
          zIndex: 9999,
          '&:focus-within': {
            top: 20,
          },
        }}
      >
        <AccessibleButton
          variant="contained"
          color="primary"
          onClick={skipToContent}

          aria-label="跳转到主要内容"
          shortcut="Alt+M"
          sx={{
            fontSize: '14px',
            fontWeight: 'bold',
            boxShadow: 3,
          }}
        >
          跳转到主要内容 (Alt+M)
        </AccessibleButton>
      </Box>

      {/* 键盘导航提示 */}
      {isKeyboardNavigation && (
        <Box
          sx={{
            position: 'fixed',
            top: 60,
            right: 20,
            zIndex: 9998,
            bgcolor: 'info.main',
            color: 'white',
            p: 1,
            borderRadius: 1,
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            gap: 1,
          }}
        >
          <AccessibilityIcon fontSize="small" />
          <Typography variant="caption">
            键盘导航已启用 | Alt+S:搜索 | Alt+M:主内容 | Alt+N:导航
          </Typography>
        </Box>
      )}

      {/* 返回顶部按钮 */}
      <Fade in={showBackToTop}>
        <Box
          sx={{
            position: 'fixed',
            bottom: 20,
            right: 20,
            zIndex: 9997,
          }}
        >
          <AccessibleButton
            onClick={scrollToTop}
            sx={{
              minWidth: 56,
              height: 56,
              borderRadius: '50%',
              boxShadow: 3,
              '&:hover': {
                boxShadow: 6,
              },
            }}
            variant="contained"
            color="primary"
            aria-label="返回页面顶部"
          >
            <ArrowUpIcon />
          </AccessibleButton>
        </Box>
      </Fade>

      {/* 屏幕阅读器公告区域 */}
      <Box
        aria-live="polite"
        aria-atomic="true"
        sx={{
          position: 'absolute',
          left: -10000,
          width: 1,
          height: 1,
          overflow: 'hidden',
        }}
      >
        {announcements.map((message, index) => (
          <div key={index}>{message}</div>
        ))}
      </Box>

      {children}
    </AccessibilityContext.Provider>
  );
};

export default AccessibilityProvider;