import { useRef, useCallback, useEffect } from 'react';

interface UseAutoScrollOptions {
  dependencies?: any[];
  enabled?: boolean;
  delay?: number;
}

export const useAutoScroll = (options: UseAutoScrollOptions = {}) => {
  const { dependencies = [], enabled = true, delay = 50 } = options;
  
  const containerRef = useRef<HTMLDivElement>(null);
  const endRef = useRef<HTMLDivElement>(null);
  const timeoutRef = useRef<NodeJS.Timeout>();
  const animationRef = useRef<number>();

  // 清理定时器和动画帧
  const cleanup = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }
    if (animationRef.current) {
      cancelAnimationFrame(animationRef.current);
    }
  }, []);

  // 检查是否应该自动滚动
  const shouldAutoScroll = useCallback(() => {
    if (!containerRef.current || !enabled) return false;
    
    const container = containerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // 如果用户滚动到接近底部（距离底部小于100px），则允许自动滚动
    return scrollHeight - scrollTop - clientHeight < 100;
  }, [enabled]);

  // 执行滚动到底部
  const scrollToBottom = useCallback((force = false) => {
    if (!containerRef.current || !endRef.current) return;
    if (!force && !shouldAutoScroll()) return;

    cleanup();

    const performScroll = () => {
      try {
        const container = containerRef.current;
        const endElement = endRef.current;
        
        if (container && endElement) {
          // 使用 scrollIntoView 平滑滚动
          endElement.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'end',
            inline: 'nearest'
          });
          
          // 备用方案：直接设置 scrollTop
          timeoutRef.current = setTimeout(() => {
            if (container) {
              container.scrollTop = container.scrollHeight;
            }
          }, 100);
        }
      } catch (error) {
        console.warn('滚动失败:', error);
      }
    };

    // 延迟执行滚动，确保DOM已更新
    timeoutRef.current = setTimeout(performScroll, delay);
  }, [shouldAutoScroll, cleanup, delay]);

  // 强制滚动到底部（忽略用户位置）
  const forceScrollToBottom = useCallback(() => {
    scrollToBottom(true);
  }, [scrollToBottom]);

  // 平滑滚动（考虑用户位置）
  const smoothScrollToBottom = useCallback(() => {
    scrollToBottom(false);
  }, [scrollToBottom]);

  // 监听依赖项变化，自动触发滚动
  useEffect(() => {
    if (enabled && dependencies.length > 0) {
      forceScrollToBottom();
    }
  }, [...dependencies, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // 组件卸载时清理
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    containerRef,
    endRef,
    scrollToBottom: smoothScrollToBottom,
    forceScrollToBottom,
    shouldAutoScroll,
  };
};