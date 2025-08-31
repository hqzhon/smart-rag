import React, { useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  LinearProgress,
  Alert,
  Container,
  Fade,
  Slide,
  Grow,
} from '@mui/material';

import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox } from '@/components/animations';



interface ChatInterfaceProps {
  sessionId: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({ sessionId }) => {
  const {
    messages,
    isLoading,
    error,
    sendStreamMessage,
    streamingMessage,
  } = useChatStore();

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const messageContainerRef = useRef<HTMLDivElement>(null);

  // 获取当前会话的消息
  const sessionMessages = messages[sessionId] || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // 检查是否需要自动滚动
  const shouldAutoScroll = () => {
    if (!messageContainerRef.current) return true;
    
    const container = messageContainerRef.current;
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    
    // 如果用户滚动到接近底部（距离底部小于100px），则自动滚动
    return scrollHeight - scrollTop - clientHeight < 100;
  };

  useEffect(() => {
    // 新消息时总是滚动到底部
    scrollToBottom();
  }, [sessionMessages.length]);

  useEffect(() => {
    // 流式输出时，只有在用户接近底部时才自动滚动
    if (streamingMessage && shouldAutoScroll()) {
      // 使用requestAnimationFrame确保DOM更新后再滚动
      requestAnimationFrame(() => {
        scrollToBottom();
      });
    }
  }, [streamingMessage?.content]);

  const handleSendMessage = async (content: string) => {
    try {
      console.log('发送消息:', content, '会话ID:', sessionId);
      await sendStreamMessage(sessionId, content);
    } catch (error) {
      console.error('发送消息失败:', error);
    }
  };

  return (
    <Box
      sx={{
        height: '100vh',
        display: 'flex',
        flexDirection: 'column',
        bgcolor: 'background.default',
      }}
    >

      {/* 加载指示器 */}
      <Fade in={isLoading} timeout={300}>
        <LinearProgress
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1000,
          }}
        />
      </Fade>

      {/* 错误提示 */}
      {error && (
        <Grow in timeout={400}>
          <Alert 
            severity="error" 
            sx={{ 
              m: 2,
              '& .MuiAlert-icon': {
                animation: 'pulse 2s infinite',
              },
            }}
          >
            {error}
          </Alert>
        </Grow>
      )}

      {/* 消息列表区域 */}
      <Box
        sx={{
          flexGrow: 1,
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
          position: 'relative',
        }}
      >
        <Container
          ref={messageContainerRef}
          maxWidth={false}
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            py: 1,
            px: 2,
            maxWidth: '100%',
            overflow: 'auto',
          }}
        >
          <Fade in timeout={300}>
            <Box
              sx={{
                flexGrow: 1,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
              }}
            >
              <MessageList
                messages={sessionMessages}
                isStreaming={!!streamingMessage}
                streamingMessageProp={streamingMessage}
              />
              <div ref={messagesEndRef} data-messages-end />
            </Box>
          </Fade>
        </Container>
      </Box>

      {/* 现代化输入区域 */}
      <Slide direction="up" in timeout={800}>
        <Paper
          elevation={0}
          sx={{
            borderTop: '1px solid',
            borderColor: 'divider',
            background: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(10px)',
          }}
        >
          <Container maxWidth={false} sx={{ px: 2 }}>
            <AnimatedBox animation="fadeInUp" delay="0.3s">
              <Box sx={{ py: 1 }}>
                <ChatInput
                  onSendMessage={handleSendMessage}
                  disabled={isLoading}
                  placeholder="请输入您的医疗问题，我将为您提供专业的解答..."
                />
              </Box>
            </AnimatedBox>
          </Container>
        </Paper>
      </Slide>
    </Box>
  );
};

export default ChatInterface;