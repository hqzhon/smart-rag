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
      {/* 现代化头部 */}
      <Slide direction="down" in timeout={600}>
        <Paper
          elevation={0}
          sx={{
            background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.1) 0%, rgba(217, 70, 239, 0.1) 100%)',
            borderBottom: '1px solid',
            borderColor: 'divider',
            backdropFilter: 'blur(10px)',
          }}
        >
          <Container maxWidth="lg">
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                py: 2,
              }}
            >
              <AnimatedBox animation="fadeInLeft" delay="0.2s">
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                  <HoverAnimatedBox hoverAnimation="scale">
                    <Avatar
                      sx={{
                        bgcolor: 'primary.main',
                        width: 48,
                        height: 48,
                      }}
                    >
                      <BotIcon />
                    </Avatar>
                  </HoverAnimatedBox>
                  <Box>
                    <AnimatedBox animation="fadeInUp" delay="0.4s">
                      <Typography
                        variant="h5"
                        component="h1"
                        sx={{
                          fontWeight: 700,
                          background: 'linear-gradient(135deg, #0ea5e9 0%, #d946ef 100%)',
                          backgroundClip: 'text',
                          WebkitBackgroundClip: 'text',
                          WebkitTextFillColor: 'transparent',
                        }}
                      >
                        智能医疗助手
                      </Typography>
                    </AnimatedBox>
                    <AnimatedBox animation="fadeInUp" delay="0.6s">
                      <Typography variant="body2" color="text.secondary">
                        基于RAG技术的医疗知识问答系统
                      </Typography>
                    </AnimatedBox>
                  </Box>
                </Box>
              </AnimatedBox>
              <AnimatedBox animation="fadeInLeft" delay="0.8s">
                <HoverAnimatedBox hoverAnimation="glow">
                  <Chip
                    icon={<ChatIcon />}
                    label={`会话 ${sessionId.slice(0, 8)}`}
                    variant="outlined"
                    size="small"
                    sx={{
                      borderColor: 'primary.main',
                      color: 'primary.main',
                    }}
                  />
                </HoverAnimatedBox>
              </AnimatedBox>
            </Box>
          </Container>
        </Paper>
      </Slide>

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
          maxWidth="lg"
          sx={{
            height: '100%',
            display: 'flex',
            flexDirection: 'column',
            py: 2,
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
          <Container maxWidth="lg">
            <AnimatedBox animation="fadeInUp" delay="0.3s">
              <Box sx={{ py: 2 }}>
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