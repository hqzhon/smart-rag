import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import {
  Box,
  Container,
  Paper,
  Typography,
  Alert,
  Snackbar,
  Fade,
  Slide,
  Grow,
  Button,
} from '@mui/material';

import ChatInterface from '@/components/ChatInterface';
import Sidebar from '@/components/Sidebar';
import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox, HoverAnimatedBox, Typewriter } from '@/components/animations';

const ChatPage: React.FC = () => {
  const { sessionId } = useParams<{ sessionId?: string }>();
  const {
    currentSession,
    setCurrentSession,
    createSession,
    loadChatHistory,
    error,
    setError,
  } = useChatStore();

  const [sidebarOpen, setSidebarOpen] = useState(true);

  useEffect(() => {
    if (sessionId && sessionId !== currentSession) {
      setCurrentSession(sessionId);
      loadChatHistory(sessionId);
    }
  }, [sessionId, currentSession, setCurrentSession, loadChatHistory]);

  const handleCreateSession = async () => {
    try {
      const newSessionId = await createSession();
      window.history.pushState(null, '', `/chat/${newSessionId}`);
    } catch (error) {
      console.error('创建会话失败:', error);
    }
  };

  const handleCloseError = () => {
    setError(null);
  };

  return (
    <AnimatedBox animation="fadeInUp" duration="0.5s">
      <Box sx={{ height: '100vh', display: 'flex' }}>
        {/* 侧边栏 */}
        <Slide direction="right" in={sidebarOpen} timeout={300}>
          <Box>
            <Sidebar
              open={sidebarOpen}
              onToggle={() => setSidebarOpen(!sidebarOpen)}
              onCreateSession={handleCreateSession}
            />
          </Box>
        </Slide>

        {/* 主内容区域 */}
        <Box
          sx={{
            flexGrow: 1,
            display: 'flex',
            flexDirection: 'column',
            transition: 'margin-left 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            marginLeft: sidebarOpen ? '280px' : '0px',
          }}
        >
          {currentSession ? (
            <Fade in timeout={600}>
              <Box sx={{ height: '100%' }}>
                <ChatInterface sessionId={currentSession} />
              </Box>
            </Fade>
          ) : (
            <AnimatedBox animation="fadeInUp" duration="0.8s" delay="0.2s">
              <Container maxWidth="md" sx={{ mt: 8 }}>
                <HoverAnimatedBox hoverAnimation="lift">
                  <Paper
                    elevation={3}
                    sx={{
                      p: 6,
                      textAlign: 'center',
                      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                      color: 'white',
                      borderRadius: 4,
                      position: 'relative',
                      overflow: 'hidden',
                      '&::before': {
                        content: '""',
                        position: 'absolute',
                        top: 0,
                        left: 0,
                        right: 0,
                        bottom: 0,
                        background: 'linear-gradient(45deg, rgba(255,255,255,0.1) 0%, transparent 50%, rgba(255,255,255,0.1) 100%)',
                        transform: 'translateX(-100%)',
                        transition: 'transform 0.6s',
                      },
                      '&:hover::before': {
                        transform: 'translateX(100%)',
                      },
                    }}
                  >
                    <AnimatedBox animation="fadeInUp" duration="0.6s" delay="0.4s">
                      <Typography variant="h3" component="h1" gutterBottom>
                        <Typewriter text="医疗RAG智能问答系统" speed={100} />
                      </Typography>
                    </AnimatedBox>
                    <AnimatedBox animation="fadeInUp" duration="0.6s" delay="0.6s">
                      <Typography variant="h6" sx={{ mb: 4, opacity: 0.9 }}>
                        基于深度学习的医疗文档智能检索与问答平台
                      </Typography>
                    </AnimatedBox>
                    <AnimatedBox animation="fadeInUp" duration="0.6s" delay="0.8s">
                      <Typography variant="body1" sx={{ mb: 4 }}>
                        上传医疗文档，开始智能对话，获取专业的医疗信息解答
                      </Typography>
                    </AnimatedBox>
                    <AnimatedBox animation="fadeInUp" duration="0.6s" delay="1s">
                      <Box sx={{ display: 'flex', gap: 2, justifyContent: 'center' }}>
                        <HoverAnimatedBox hoverAnimation="scale">
                          <Button
                            variant="contained"
                            size="large"
                            onClick={handleCreateSession}
                            sx={{ 
                              bgcolor: 'rgba(255,255,255,0.2)', 
                              '&:hover': { 
                                bgcolor: 'rgba(255,255,255,0.3)',
                                transform: 'scale(1.05)',
                              },
                              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                            }}
                          >
                            开始对话
                          </Button>
                        </HoverAnimatedBox>
                      </Box>
                    </AnimatedBox>
                  </Paper>
                </HoverAnimatedBox>
              </Container>
            </AnimatedBox>
          )}
        </Box>



        {/* 错误提示 */}
        <Grow in={!!error} timeout={400}>
          <Box>
            <Snackbar
              open={!!error}
              autoHideDuration={6000}
              onClose={handleCloseError}
              anchorOrigin={{ vertical: 'top', horizontal: 'center' }}
            >
              <Alert 
                onClose={handleCloseError} 
                severity="error" 
                sx={{ 
                  width: '100%',
                  '& .MuiAlert-icon': {
                    animation: 'pulse 2s infinite',
                  },
                  '@keyframes pulse': {
                    '0%': {
                      transform: 'scale(1)',
                    },
                    '50%': {
                      transform: 'scale(1.1)',
                    },
                    '100%': {
                      transform: 'scale(1)',
                    },
                  },
                }}
              >
                {error}
              </Alert>
            </Snackbar>
          </Box>
        </Grow>
      </Box>
    </AnimatedBox>
  );
};

export default ChatPage;