import React, { useMemo } from 'react';
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
}

const MessageList: React.FC<MessageListProps> = ({
  messages,
  isStreaming = false,
  streamingMessageProp,
}) => {
  const { announceMessage } = useAccessibility();
  // 判断是否使用虚拟化列表（消息数量超过50条时）
  const shouldUseVirtualization = useMemo(() => messages.length > 50, [messages.length]);
  
  // 宣布新消息
  const lastMessageRef = React.useRef<Message | null>(null);
  React.useEffect(() => {
    if (messages.length > 0) {
      const lastMessage = messages[messages.length - 1];
      // 只有当最后一条消息真正改变时才宣布
      if (lastMessage && lastMessage.id !== lastMessageRef.current?.id) {
        const sender = lastMessage.type === 'user' ? '用户' : '助手';
        announceMessage(`收到来自${sender}的新消息`);
        lastMessageRef.current = lastMessage;
      }
    }
  }, [messages.length, messages, announceMessage]); // 依赖消息数量和消息数组
  
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
        component="main"
        role="main"
        aria-label="消息列表"
        sx={{
          flexGrow: 1,
          overflow: 'auto',
          py: 2,
          px: 1,
          '&::-webkit-scrollbar': {
            width: '6px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'rgba(0,0,0,0.05)',
            borderRadius: '3px',
          },
          '&::-webkit-scrollbar-thumb': {
            background: 'rgba(0,0,0,0.2)',
            borderRadius: '3px',
            '&:hover': {
              background: 'rgba(0,0,0,0.3)',
            },
          },
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
      </Box>
    </PerformanceMonitor>
  );
};

export default MessageList;