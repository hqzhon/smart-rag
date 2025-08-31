import React, { useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  LinearProgress,
  Alert,
  Fade,
  Slide,
  Grow,
} from '@mui/material';

import MessageList, { MessageListRef } from './MessageList';
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

  // 获取当前会话的消息
  const sessionMessages = messages[sessionId] || [];
  
  // MessageList的引用，用于控制滚动
  const messageListRef = useRef<MessageListRef>(null);

  // 问题2: 切换会话时强制滚动到底部
  useEffect(() => {
    if (sessionMessages.length > 0 && messageListRef.current) {
      // 延迟执行确保组件完全渲染
      setTimeout(() => {
        messageListRef.current?.forceScrollToBottom();
      }, 100);
    }
  }, [sessionId, sessionMessages.length]);

  const handleSendMessage = async (content: string) => {
    try {
      console.log('发送消息:', content, '会话 ID:', sessionId);
      
      // 问题3: 发送消息时立即滚动到底部
      messageListRef.current?.forceScrollToBottom();
      
      await sendStreamMessage(sessionId, content);
      
      // 发送完成后再次确保滚动，让用户看到问题和回答
      setTimeout(() => {
        messageListRef.current?.forceScrollToBottom();
      }, 200);
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
        <Fade in timeout={300}>
          <Box
            sx={{
              flexGrow: 1,
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column',
              // 去除多余的内边距，让MessageList直接管理滚动
              padding: 0,
              margin: 0,
            }}
          >
            <MessageList
              ref={messageListRef}
              messages={sessionMessages}
              isStreaming={!!streamingMessage}
              streamingMessageProp={streamingMessage}
            />
          </Box>
        </Fade>
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