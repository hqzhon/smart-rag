import React, { Suspense, lazy, ComponentType } from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';
import { AnimatedBox } from './animations';

interface LazyRouteProps {
  factory: () => Promise<{ default: ComponentType<any> }>;
  fallback?: React.ReactNode;
  errorBoundary?: ComponentType<{ children: React.ReactNode }>;
  preload?: boolean;
}

// 默认加载组件
const DefaultFallback: React.FC = () => (
  <AnimatedBox animation="fadeInUp" duration="0.3s">
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '200px',
        gap: 2,
      }}
    >
      <CircularProgress size={40} thickness={4} />
      <Typography variant="body2" color="text.secondary">
        Loading...
      </Typography>
    </Box>
  </AnimatedBox>
);

// 默认错误边界
class DefaultErrorBoundary extends React.Component<
  { children: React.ReactNode },
  { hasError: boolean; error?: Error }
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('LazyRoute Error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <AnimatedBox animation="fadeInUp" duration="0.3s">
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              minHeight: '200px',
              gap: 2,
              p: 3,
              textAlign: 'center',
            }}
          >
            <Typography variant="h6" color="error">
              Something went wrong
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {this.state.error?.message || 'Failed to load component'}
            </Typography>
            <Box
              component="button"
              onClick={() => window.location.reload()}
              sx={{
                mt: 2,
                px: 3,
                py: 1,
                border: '1px solid',
                borderColor: 'primary.main',
                borderRadius: 1,
                bgcolor: 'transparent',
                color: 'primary.main',
                cursor: 'pointer',
                '&:hover': {
                  bgcolor: 'primary.main',
                  color: 'primary.contrastText',
                },
              }}
            >
              Reload Page
            </Box>
          </Box>
        </AnimatedBox>
      );
    }

    return this.props.children;
  }
}

// 组件缓存
const componentCache = new Map<string, ComponentType<any>>();

// 预加载函数
const preloadComponent = (factory: () => Promise<{ default: ComponentType<any> }>, key: string) => {
  if (!componentCache.has(key)) {
    factory().then(module => {
      componentCache.set(key, module.default);
    }).catch(error => {
      console.warn('Failed to preload component:', error);
    });
  }
};

const LazyRoute: React.FC<LazyRouteProps> = ({
  factory,
  fallback = <DefaultFallback />,
  errorBoundary: ErrorBoundary = DefaultErrorBoundary,
  preload = false,
}) => {
  // 生成缓存键
  const cacheKey = factory.toString();
  
  // 预加载逻辑
  React.useEffect(() => {
    if (preload) {
      preloadComponent(factory, cacheKey);
    }
  }, [factory, cacheKey, preload]);

  // 创建懒加载组件
  const LazyComponent = React.useMemo(() => {
    // 如果组件已缓存，直接返回
    if (componentCache.has(cacheKey)) {
      return componentCache.get(cacheKey)!;
    }
    
    // 否则创建懒加载组件
    return lazy(() => {
      return factory().then(module => {
        componentCache.set(cacheKey, module.default);
        return module;
      });
    });
  }, [factory, cacheKey]);

  return (
    <ErrorBoundary>
      <Suspense fallback={fallback}>
        <LazyComponent />
      </Suspense>
    </ErrorBoundary>
  );
};

// 高阶组件版本
export const withLazyLoading = <P extends object>(
  factory: () => Promise<{ default: ComponentType<P> }>,
  options?: Omit<LazyRouteProps, 'factory'>
) => {
  return () => (
    <LazyRoute factory={factory} {...options}>
      {/* Props will be passed to the lazy component */}
    </LazyRoute>
  );
};

// 预加载钩子
export const usePreloadComponent = (
  factory: () => Promise<{ default: ComponentType<any> }>
) => {
  const cacheKey = factory.toString();
  
  const preload = React.useCallback(() => {
    preloadComponent(factory, cacheKey);
  }, [factory, cacheKey]);
  
  const isPreloaded = componentCache.has(cacheKey);
  
  return { preload, isPreloaded };
};

export default LazyRoute;