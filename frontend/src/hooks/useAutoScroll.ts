import { useRef, useCallback, useEffect } from 'react';

interface UseAutoScrollOptions {
  dependencies?: any[];
  enabled?: boolean;
  delay?: number;
}

export const useAutoScroll = (options: UseAutoScrollOptions = {}) => {
  const { dependencies = [], enabled = true, delay = 100 } = options;
  
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

  // 检查是否应该自动滚动（用户接近底部）
  const shouldAutoScroll = useCallback(() => {
    if (!containerRef.current || !enabled) return false;
    
    const container = containerRef.current;
    const { scrollTop, scrollHeight, clientHeight } = container;
    
    // 如果用户滚动到接近底部（距离底部小于100px），则允许自动滚动
    return scrollHeight - scrollTop - clientHeight < 100;
  }, [enabled]);

  // 强制滚动到底部（立即定位）
  const forceScrollToBottom = useCallback(() => {
    if (!endRef.current || !containerRef.current) return;

    cleanup();

    try {
      const endElement = endRef.current;
      const container = containerRef.current;
      
      // 使用 'auto' 模式立即定位
      endElement.scrollIntoView({ 
        behavior: 'auto', 
        block: 'end',
        inline: 'nearest'
      });
      
      // 备用方案：直接设置 scrollTop
      setTimeout(() => {
        if (container) {
          container.scrollTop = container.scrollHeight;
        }
      }, 50);
    } catch (error) {
      console.warn('强制滚动失败:', error);
    }
  }, [cleanup]);

  // 平滑滚动到底部
  const smoothScrollToBottom = useCallback(() => {
    if (!endRef.current || !containerRef.current) return;
    if (!shouldAutoScroll()) return; // 只有在用户接近底部时才平滑滚动

    cleanup();

    try {
      const endElement = endRef.current;
      
      // 使用 'smooth' 模式平滑滚动
      endElement.scrollIntoView({ 
        behavior: 'smooth', 
        block: 'end',
        inline: 'nearest'
      });
    } catch (error) {
      console.warn('平滑滚动失败:', error);
    }
  }, [shouldAutoScroll, cleanup]);

  // 延迟滚动（确保DOM更新完成）
  const delayedScrollToBottom = useCallback((force = false) => {
    cleanup();
    
    timeoutRef.current = setTimeout(() => {
      if (force) {
        forceScrollToBottom();
      } else {
        smoothScrollToBottom();
      }
    }, delay);
  }, [forceScrollToBottom, smoothScrollToBottom, delay, cleanup]);

  // 监听依赖项变化，自动触发滚动
  useEffect(() => {
    if (enabled && dependencies.length > 0) {
      delayedScrollToBottom(true);
    }
  }, [...dependencies, enabled]); // eslint-disable-line react-hooks/exhaustive-deps

  // 组件卸载时清理
  useEffect(() => {
    return cleanup;
  }, [cleanup]);

  return {
    containerRef,
    endRef,
    forceScrollToBottom,
    smoothScrollToBottom,
    delayedScrollToBottom,
    shouldAutoScroll,
  };
};