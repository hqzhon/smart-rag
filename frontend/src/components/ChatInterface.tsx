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

  // 简单直接的滚动到底部函数
  const scrollToBottom = (force = false) => {
    if (!messagesEndRef.current) return;
    
    try {
      messagesEndRef.current.scrollIntoView({ 
        behavior: force ? 'auto' : 'smooth',
        block: 'end' 
      });
    } catch (error) {
      console.warn('滚动失败:', error);
    }
  };

  // 1. 新消息时自动滚动
  useEffect(() => {
    if (sessionMessages.length > 0) {
      setTimeout(() => scrollToBottom(true), 100);
    }
  }, [sessionMessages.length]);

  // 2. 切换会话时滚动到底部
  useEffect(() => {
    if (sessionMessages.length > 0) {
      setTimeout(() => scrollToBottom(true), 300);
    }
  }, [sessionId]);

  // 3. 流式输出时跟踪滚动
  useEffect(() => {
    if (streamingMessage?.content) {
      scrollToBottom(false); // 使用平滑滚动
    }
  }, [streamingMessage?.content]);

  const handleSendMessage = async (content: string) => {
    try {
      console.log('发送消息:', content, '会话 ID:', sessionId);
      
      // 4. 发送消息时立即滚动
      scrollToBottom(true);
      
      await sendStreamMessage(sessionId, content);
      
      // 发送后再次确保滚动
      setTimeout(() => scrollToBottom(true), 200);
    } catch (error) {
      console.error('发送消息失败:', error);
    }
  };

  return (
    <Box
      sx={{
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        background: 'linear-gradient(135deg, rgba(246, 249, 252, 0.8) 0%, rgba(238, 243, 248, 0.8) 100%)',
        backdropFilter: 'blur(20px)',
        minHeight: 0, // 确保flex子元素可以收缩
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `
            radial-gradient(circle at 15% 30%, rgba(103, 126, 234, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 85% 70%, rgba(217, 70, 239, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 50% 80%, rgba(14, 165, 233, 0.02) 0%, transparent 50%)
          `,
          pointerEvents: 'none',
          zIndex: 0,
        },
      }}
    >

      {/* 现代化加载指示器 */}
      <Fade in={isLoading} timeout={300}>
        <LinearProgress
          sx={{
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            zIndex: 1000,
            height: 3,
            background: 'rgba(255, 255, 255, 0.3)',
            '& .MuiLinearProgress-bar': {
              background: 'linear-gradient(90deg, #667eea, #764ba2, #9c88ff)',
              animation: 'shimmer 1.5s infinite ease-in-out',
            },
            '@keyframes shimmer': {
              '0%': {
                transform: 'translateX(-100%)',
              },
              '100%': {
                transform: 'translateX(100%)',
              },
            },
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
          minHeight: 0, // 确保flex子元素可以收缩
        }}
      >
        <Box
          ref={messageContainerRef}
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            // 完全去除所有间距，让内容紧贴侧边栏
            padding: 0,
            margin: 0,
            width: '100%',
            overflow: 'auto',
            minHeight: 0,
          }}
        >
          <Fade in timeout={300}>
            <Box
              sx={{
                flexGrow: 1,
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'column',
                // 只在这里添加最小的内边距，避免消息贴边
                px: 1, // 减少为1，更紧凑
                py: 1,
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
        </Box>
      </Box>

      {/* 现代化输入区域 */}
      <Slide direction="up" in timeout={800}>
        <Paper
          elevation={0}
          sx={{
            borderTop: '1px solid rgba(255, 255, 255, 0.2)',
            background: 'rgba(255, 255, 255, 0.9)',
            backdropFilter: 'blur(20px)',
            position: 'sticky',
            bottom: 0,
            zIndex: 10,
            flexShrink: 0, // 防止输入框被压缩
            borderRadius: 0,
            boxShadow: '0 -4px 20px rgba(0, 0, 0, 0.1)',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 1,
              background: 'linear-gradient(90deg, transparent, rgba(103, 126, 234, 0.3), transparent)',
            },
          }}
        >
          <Box sx={{ px: 1, py: 1.5 }}>
            <AnimatedBox animation="fadeInUp" delay="0.3s">
              <Box sx={{ py: 1 }}>
                <ChatInput
                  onSendMessage={handleSendMessage}
                  disabled={isLoading}
                  placeholder="请输入您的医疗问题，我将为您提供专业的解答..."
                />
              </Box>
            </AnimatedBox>
          </Box>
        </Paper>
      </Slide>
    </Box>
  );
};

export default ChatInterface;