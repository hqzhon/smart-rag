import React, { useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Alert,
  Container,
  Fade,
  Chip,
  Avatar,
  Slide,
  Grow,
} from '@mui/material';
import {
  Chat as ChatIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';

import MessageList from './MessageList';
import ChatInput from './ChatInput';
import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox, HoverAnimatedBox } from '@/components/animations';



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

  // 获取当前会话的消息
  const sessionMessages = messages[sessionId] || [];

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [sessionMessages, streamingMessage]);

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
          maxWidth={false}
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            py: 1,
            px: 2,
            maxWidth: '100%',
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
              <div ref={messagesEndRef} />
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