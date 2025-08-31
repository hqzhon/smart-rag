import React, { useMemo, useRef, useEffect, useImperativeHandle, forwardRef } from 'react';
import {
  Box,
  List,
} from '@mui/material';

import { Message } from '@/types';
import OptimizedMessageItem from './OptimizedMessageItem';
import VirtualizedMessageList from './VirtualizedMessageList';
import PerformanceMonitor from './PerformanceMonitor';
import { useAccessibility } from './AccessibilityProvider';

interface MessageListProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingMessageProp?: { id: string; content: string; sessionId: string; } | null;
  onScrollToBottom?: () => void;
}

export interface MessageListRef {
  scrollToBottom: (smooth?: boolean) => void;
  forceScrollToBottom: () => void;
}

const MessageList = forwardRef<MessageListRef, MessageListProps>((
  {
    messages,
    isStreaming = false,
    streamingMessageProp,
    onScrollToBottom,
  },
  ref
) => {
  const { announceMessage } = useAccessibility();
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  
  // 判断是否使用虚拟化列表（消息数量超过50条时）
  const shouldUseVirtualization = useMemo(() => messages.length > 50, [messages.length]);
  
  // 滚动到底部的核心函数
  const scrollToBottom = React.useCallback((smooth = false) => {
    if (!scrollContainerRef.current || !messagesEndRef.current) return;
    
    try {
      const container = scrollContainerRef.current;
      const endElement = messagesEndRef.current;
      
      if (smooth) {
        // 平滑滚动
        endElement.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'end',
          inline: 'nearest'
        });
      } else {
        // 立即滚动
        endElement.scrollIntoView({ 
          behavior: 'auto', 
          block: 'end',
          inline: 'nearest'
        });
        // 备用方案
        setTimeout(() => {
          if (container) {
            container.scrollTop = container.scrollHeight;
          }
        }, 10);
      }
      
      onScrollToBottom?.();
    } catch (error) {
      console.warn('滚动失败:', error);
    }
  }, [onScrollToBottom]);
  
  const forceScrollToBottom = React.useCallback(() => {
    scrollToBottom(false);
  }, [scrollToBottom]);
  
  // 向父组件暴露滚动方法
  useImperativeHandle(ref, () => ({
    scrollToBottom,
    forceScrollToBottom,
  }), [scrollToBottom, forceScrollToBottom]);

  // 宣布新消息并自动滚动
  const lastMessageRef = React.useRef<Message | null>(null);
  React.useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      // 只有当最后一条消息真正改变时才宣布并滚动
      if (lastMessage && lastMessage.id !== lastMessageRef.current?.id) {
        const sender = lastMessage.type === 'user' ? '用户' : '助手';
        announceMessage(`收到来自${sender}的新消息`);
        lastMessageRef.current = lastMessage;
        
        // 新消息时强制滚动到底部
        setTimeout(() => {
          forceScrollToBottom();
        }, 100);
      }
    }
  }, [messages.length, messages, announceMessage, forceScrollToBottom]);
  
  // 流式消息内容变化时平滑滚动
  React.useEffect(() => {
    if (isStreaming && streamingMessageProp?.content) {
      scrollToBottom(true);
    }
  }, [streamingMessageProp?.content, isStreaming, scrollToBottom]);
  
  // 获取当前流式传输的消息
  const streamingMessage = useMemo(() => {
    if (!isStreaming) return null;
    return messages[messages.length - 1];
  }, [isStreaming, messages]);

  const renderOptimizedMessage = (message: Message, index: number) => {
    const isCurrentStreaming = isStreaming && message.id === streamingMessage?.id;
    const streamingContent = isCurrentStreaming ? streamingMessageProp?.content || '' : '';
    
    return (
      <OptimizedMessageItem
        key={message.id}
        message={message}
        isStreaming={isCurrentStreaming}
        streamingContent={streamingContent}
        index={index}
      />
    );
  };

  return (
    <PerformanceMonitor enabled={process.env.NODE_ENV === 'development'}>
      <Box
        ref={scrollContainerRef}
        component="main"
        role="main"
        aria-label="消息列表"
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          py: 3,
          px: 2,
          background: 'transparent',
          position: 'relative',
          zIndex: 1,
          '&::-webkit-scrollbar': {
            width: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'rgba(0, 0, 0, 0.02)',
            borderRadius: '12px',
            margin: '8px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'linear-gradient(135deg, rgba(103, 126, 234, 0.3) 0%, rgba(217, 70, 239, 0.3) 100%)',
            borderRadius: '12px',
            border: '2px solid transparent',
            backgroundClip: 'content-box',
            transition: 'all 0.3s ease',
            '&:hover': {
              background: 'linear-gradient(135deg, rgba(103, 126, 234, 0.5) 0%, rgba(217, 70, 239, 0.5) 100%)',
              backgroundClip: 'content-box',
              transform: 'scaleY(1.2)',
            },
          },
          '&::-webkit-scrollbar-corner': {
            background: 'transparent',
          },
          // 火狐浏览器滚动条
          scrollbarWidth: 'thin',
          scrollbarColor: 'rgba(103, 126, 234, 0.3) transparent',
        }}
      >
        {shouldUseVirtualization ? (
          <VirtualizedMessageList
            messages={messages}
          />
        ) : (
          <List sx={{ p: 0 }}>
            {messages.map((message, index) => renderOptimizedMessage(message, index))}
          </List>
        )}
        {/* 滚动定位点 */}
        <div ref={messagesEndRef} style={{ height: 1, width: 1 }} />
      </Box>
    </PerformanceMonitor>
  );
});

MessageList.displayName = 'MessageList';
export default MessageList;