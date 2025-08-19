import React, { useEffect, useRef, useState, memo } from 'react';
import { Box, Typography, Chip, Collapse, IconButton } from '@mui/material';
import {
  Speed as SpeedIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

interface PerformanceMetrics {
  renderTime: number;
  componentCount: number;
  memoryUsage?: number;
  fps: number;
}

interface PerformanceMonitorProps {
  enabled?: boolean;
  position?: 'top-left' | 'top-right' | 'bottom-left' | 'bottom-right';
  children: React.ReactNode;
}

const PerformanceMonitor: React.FC<PerformanceMonitorProps> = memo((
  {
    enabled = process.env.NODE_ENV === 'development',
    position = 'top-right',
    children,
  }
) => {
  const [metrics, setMetrics] = useState<PerformanceMetrics>({
    renderTime: 0,
    componentCount: 0,
    fps: 0,
  });
  const [isExpanded, setIsExpanded] = useState(false);
  const renderStartTime = useRef<number>(0);
  const frameCount = useRef<number>(0);
  const lastTime = useRef<number>(performance.now());
  const componentCountRef = useRef<number>(0);

  // FPS calculation
  useEffect(() => {
    if (!enabled) return;

    let animationId: number;
    
    const calculateFPS = () => {
      const now = performance.now();
      frameCount.current++;
      
      if (now - lastTime.current >= 1000) {
        const fps = Math.round((frameCount.current * 1000) / (now - lastTime.current));
        setMetrics(prev => ({ ...prev, fps }));
        frameCount.current = 0;
        lastTime.current = now;
      }
      
      animationId = requestAnimationFrame(calculateFPS);
    };
    
    animationId = requestAnimationFrame(calculateFPS);
    
    return () => {
      if (animationId) {
        cancelAnimationFrame(animationId);
      }
    };
  }, [enabled]);

  // Render time measurement
  useEffect(() => {
    if (!enabled) return;

    renderStartTime.current = performance.now();
    
    return () => {
      const renderTime = performance.now() - renderStartTime.current;
      setMetrics(prev => ({ ...prev, renderTime }));
    };
  }, [enabled]);

  // Memory usage (if available)
  useEffect(() => {
    if (!enabled) return;

    const updateMemoryUsage = () => {
      if ('memory' in performance) {
        const memory = (performance as any).memory;
        const memoryUsage = Math.round(memory.usedJSHeapSize / 1024 / 1024);
        setMetrics(prev => ({ ...prev, memoryUsage }));
      }
    };

    const interval = setInterval(updateMemoryUsage, 2000);
    updateMemoryUsage();

    return () => clearInterval(interval);
  }, [enabled]);

  // Component count tracking
  useEffect(() => {
    if (!enabled) return;

    const observer = new MutationObserver(() => {
      const componentCount = document.querySelectorAll('[data-testid], [class*="Mui"]').length;
      componentCountRef.current = componentCount;
      setMetrics(prev => ({ ...prev, componentCount }));
    });

    observer.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['class', 'data-testid'],
    });

    return () => observer.disconnect();
  }, [enabled]);

  if (!enabled) {
    return <>{children}</>;
  }

  const getPositionStyles = () => {
    const baseStyles = {
      position: 'fixed' as const,
      zIndex: 9999,
      backgroundColor: 'rgba(0, 0, 0, 0.8)',
      color: 'white',
      padding: 1,
      borderRadius: 1,
      fontSize: '0.75rem',
      fontFamily: 'monospace',
      minWidth: 200,
    };

    switch (position) {
      case 'top-left':
        return { ...baseStyles, top: 16, left: 16 };
      case 'top-right':
        return { ...baseStyles, top: 16, right: 16 };
      case 'bottom-left':
        return { ...baseStyles, bottom: 16, left: 16 };
      case 'bottom-right':
        return { ...baseStyles, bottom: 16, right: 16 };
      default:
        return { ...baseStyles, top: 16, right: 16 };
    }
  };

  const getPerformanceColor = (value: number, thresholds: { good: number; warning: number }) => {
    if (value <= thresholds.good) return 'success';
    if (value <= thresholds.warning) return 'warning';
    return 'error';
  };

  return (
    <>
      {children}
      <Box sx={getPositionStyles()}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            cursor: 'pointer',
          }}
          onClick={() => setIsExpanded(!isExpanded)}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <SpeedIcon sx={{ fontSize: 16 }} />
            <Typography variant="caption" sx={{ fontWeight: 'bold' }}>
              Performance
            </Typography>
          </Box>
          <IconButton size="small" sx={{ color: 'white', p: 0 }}>
            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Box>

        <Collapse in={isExpanded}>
          <Box sx={{ mt: 1, display: 'flex', flexDirection: 'column', gap: 0.5 }}>
            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption">FPS:</Typography>
              <Chip
                label={metrics.fps}
                size="small"
                color={getPerformanceColor(60 - metrics.fps, { good: 15, warning: 30 })}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption">Render:</Typography>
              <Chip
                label={`${metrics.renderTime.toFixed(1)}ms`}
                size="small"
                color={getPerformanceColor(metrics.renderTime, { good: 16, warning: 33 })}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            </Box>

            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <Typography variant="caption">Components:</Typography>
              <Chip
                label={metrics.componentCount}
                size="small"
                color={getPerformanceColor(metrics.componentCount, { good: 100, warning: 500 })}
                sx={{ height: 20, fontSize: '0.7rem' }}
              />
            </Box>

            {metrics.memoryUsage && (
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="caption">Memory:</Typography>
                <Chip
                  label={`${metrics.memoryUsage}MB`}
                  size="small"
                  color={getPerformanceColor(metrics.memoryUsage, { good: 50, warning: 100 })}
                  sx={{ height: 20, fontSize: '0.7rem' }}
                />
              </Box>
            )}
          </Box>
        </Collapse>
      </Box>
    </>
  );
});

PerformanceMonitor.displayName = 'PerformanceMonitor';

export default PerformanceMonitor;