import React from 'react';
import {
  Box,
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Typography,
  Divider,
  Button,
  useTheme,
  useMediaQuery,
  Fade,
  Slide,
  Avatar,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Add as AddIcon,
  Upload as UploadIcon,
  Chat as ChatIcon,
  History as HistoryIcon,
  Settings as SettingsIcon,
  Close as CloseIcon,
} from '@mui/icons-material';

import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox, HoverAnimatedBox } from '@/components/animations';
import { AccessibleIconButton } from '@/components/AccessibleButton';

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  onCreateSession: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  open,
  onToggle,
  onCreateSession,
}) => {
  const { sessions, currentSession, setCurrentSession } = useChatStore();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isTablet = useMediaQuery(theme.breakpoints.down('lg'));

  const handleSessionClick = (sessionId: string) => {
    setCurrentSession(sessionId);
    window.history.pushState(null, '', `/chat/${sessionId}`);
    // 移动端选择会话后自动关闭侧边栏
    if (isMobile) {
      onToggle();
    }
  };

  const drawerWidth = isMobile ? '100vw' : isTablet ? 260 : 300;

  const drawerContent = (
    <AnimatedBox animation="fadeInLeft" duration="0.4s">
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* 现代化头部 */}
        <AnimatedBox animation="fadeInUp" duration="0.6s" delay="0.1s">
          <Box
            sx={{
              p: 3,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              position: 'relative',
              overflow: 'hidden',
              '&::before': {
                content: '""',
                position: 'absolute',
                top: 0,
                left: 0,
                right: 0,
                bottom: 0,
                background: 'rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                zIndex: 0,
              },
            }}
          >
            <Box sx={{ position: 'relative', zIndex: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
                <HoverAnimatedBox hoverAnimation="scale">
                  <Avatar
                    sx={{
                      width: 40,
                      height: 40,
                      mr: 2,
                      background: 'linear-gradient(135deg, #ff6b6b 0%, #ee5a24 100%)',
                      boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                      cursor: 'pointer',
                    }}
                  >
                    <ChatIcon />
                  </Avatar>
                </HoverAnimatedBox>
                {isMobile && (
                  <HoverAnimatedBox hoverAnimation="scale">
                    <AccessibleIconButton
                      onClick={onToggle}
                      aria-label="关闭侧边栏"
                      sx={{
                        ml: 'auto',
                        color: 'white',
                        '&:hover': { bgcolor: 'rgba(255,255,255,0.1)' },
                      }}
                    >
                      <CloseIcon />
                    </AccessibleIconButton>
                  </HoverAnimatedBox>
                )}
              </Box>
              <Typography 
                variant={isMobile ? "h6" : "h5"} 
                sx={{ 
                  fontWeight: 700,
                  background: 'linear-gradient(45deg, #fff 30%, #f8f9fa 90%)',
                  backgroundClip: 'text',
                  WebkitBackgroundClip: 'text',
                  WebkitTextFillColor: 'transparent',
                  mb: 0.5,
                }}
              >
                医疗RAG系统
              </Typography>
              <Typography 
                variant="body2" 
                sx={{ 
                  opacity: 0.9,
                  fontSize: isMobile ? '0.8rem' : '0.875rem',
                }}
              >
                智能医疗问答助手
              </Typography>
            </Box>
          </Box>
        </AnimatedBox>

        {/* 现代化操作按钮 */}
        <AnimatedBox animation="fadeInUp" duration="0.6s" delay="0.3s">
          <Box sx={{ p: 2.5 }}>
            <HoverAnimatedBox hoverAnimation="scale">
              <Button
                fullWidth
                variant="contained"
                startIcon={<AddIcon />}
                onClick={onCreateSession}
                sx={{ 
                  mb: 1.5,
                  py: 1.2,
                  borderRadius: 2,
                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                  boxShadow: '0 4px 12px rgba(103, 126, 234, 0.3)',
                  fontSize: isMobile ? '0.9rem' : '1rem',
                  fontWeight: 600,
                  transition: 'all 0.2s ease-in-out',
                  '&:hover': {
                    transform: 'translateY(-2px)',
                    boxShadow: '0 6px 16px rgba(103, 126, 234, 0.4)',
                  },
                }}
              >
                新建对话
              </Button>
            </HoverAnimatedBox>

          </Box>
        </AnimatedBox>

      <Divider />

      {/* 现代化会话列表 */}
      <Box sx={{ flexGrow: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        <Box sx={{ px: 2.5, py: 1.5 }}>
          <Typography 
            variant="subtitle2" 
            sx={{ 
              color: 'text.secondary',
              fontWeight: 600,
              fontSize: isMobile ? '0.8rem' : '0.875rem',
            }}
          >
            最近对话
          </Typography>
        </Box>
        
        <Box 
          sx={{ 
            flexGrow: 1, 
            overflow: 'auto',
            '&::-webkit-scrollbar': {
              width: 6,
            },
            '&::-webkit-scrollbar-track': {
              background: 'transparent',
            },
            '&::-webkit-scrollbar-thumb': {
              background: 'rgba(0,0,0,0.2)',
              borderRadius: 3,
              '&:hover': {
                background: 'rgba(0,0,0,0.3)',
              },
            },
          }}
        >
          <List sx={{ p: 0 }}>
            {sessions.length === 0 ? (
              <Fade in timeout={300}>
                <ListItem sx={{ px: 2.5, py: 3 }}>
                  <ListItemText
                    primary="暂无对话"
                    secondary="创建新对话开始使用"
                    sx={{ 
                      textAlign: 'center',
                      '& .MuiListItemText-primary': {
                        color: 'text.secondary',
                        fontSize: isMobile ? '0.9rem' : '1rem',
                        fontWeight: 500,
                      },
                      '& .MuiListItemText-secondary': {
                        fontSize: isMobile ? '0.8rem' : '0.875rem',
                      },
                    }}
                  />
                </ListItem>
              </Fade>
            ) : (
              sessions.map((session, index) => (
                <Slide 
                  key={session.id} 
                  direction="right" 
                  in 
                  timeout={200 + index * 50}
                >
                  <ListItem disablePadding sx={{ px: 1.5, mb: 0.5 }}>
                    <HoverAnimatedBox hoverAnimation="scale">
                      <ListItemButton
                        selected={session.id === currentSession}
                        onClick={() => handleSessionClick(session.id)}
                        sx={{
                          borderRadius: 2,
                          py: 1.5,
                          transition: 'all 0.2s ease-in-out',
                          '&.Mui-selected': {
                            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                            color: 'white',
                            boxShadow: '0 4px 12px rgba(103, 126, 234, 0.3)',
                            '&:hover': {
                              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                              transform: 'translateX(4px)',
                            },
                          },
                          '&:hover': {
                            bgcolor: 'action.hover',
                            transform: 'translateX(2px)',
                          },
                        }}
                      >
                        <ListItemIcon sx={{ minWidth: 40 }}>
                          <HoverAnimatedBox hoverAnimation="scale">
                            <Avatar
                              sx={{
                                width: 32,
                                height: 32,
                                bgcolor: session.id === currentSession 
                                  ? 'rgba(255,255,255,0.2)' 
                                  : 'primary.main',
                                fontSize: '0.875rem',
                              }}
                            >
                              <ChatIcon fontSize="small" />
                            </Avatar>
                          </HoverAnimatedBox>
                        </ListItemIcon>
                        <ListItemText
                          primary={session.title}
                          secondary={`${session.messageCount} 条消息`}
                          primaryTypographyProps={{
                            noWrap: true,
                            fontSize: isMobile ? '0.85rem' : '0.9rem',
                            fontWeight: 500,
                          }}
                          secondaryTypographyProps={{
                            fontSize: isMobile ? '0.7rem' : '0.75rem',
                            sx: {
                              color: session.id === currentSession 
                                ? 'rgba(255,255,255,0.8)' 
                                : 'text.secondary',
                            },
                          }}
                        />
                      </ListItemButton>
                    </HoverAnimatedBox>
                  </ListItem>
                </Slide>
              ))
            )}
          </List>
        </Box>
      </Box>

      <Divider />

      {/* 现代化底部菜单 */}
      <Box sx={{ borderTop: '1px solid', borderColor: 'divider', p: 1.5 }}>
        <List sx={{ p: 0 }}>
          <ListItem disablePadding sx={{ mb: 0.5 }}>
            <ListItemButton 
              sx={{ 
                borderRadius: 2,
                py: 1.2,
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateX(2px)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    bgcolor: 'secondary.main',
                    fontSize: '0.875rem',
                  }}
                >
                  <HistoryIcon fontSize="small" />
                </Avatar>
              </ListItemIcon>
              <ListItemText 
                primary="历史记录" 
                primaryTypographyProps={{
                  fontSize: isMobile ? '0.85rem' : '0.9rem',
                  fontWeight: 500,
                }}
              />
            </ListItemButton>
          </ListItem>
          <ListItem disablePadding>
            <ListItemButton 
              sx={{ 
                borderRadius: 2,
                py: 1.2,
                transition: 'all 0.2s ease-in-out',
                '&:hover': {
                  bgcolor: 'action.hover',
                  transform: 'translateX(2px)',
                },
              }}
            >
              <ListItemIcon sx={{ minWidth: 40 }}>
                <Avatar
                  sx={{
                    width: 32,
                    height: 32,
                    bgcolor: 'info.main',
                    fontSize: '0.875rem',
                  }}
                >
                  <SettingsIcon fontSize="small" />
                </Avatar>
              </ListItemIcon>
              <ListItemText 
                primary="设置" 
                primaryTypographyProps={{
                  fontSize: isMobile ? '0.85rem' : '0.9rem',
                  fontWeight: 500,
                }}
              />
            </ListItemButton>
          </ListItem>
        </List>
      </Box>
    </Box>
    </AnimatedBox>
  );

  return (
    <>
      {/* 响应式切换按钮 */}
      {!open && (
        <Fade in timeout={200}>
          <AccessibleIconButton
            onClick={onToggle}
            aria-label="打开侧边栏"
            sx={{
              position: 'fixed',
              top: isMobile ? 12 : 16,
              left: isMobile ? 12 : 16,
              zIndex: 1300,
              width: isMobile ? 48 : 56,
              height: isMobile ? 48 : 56,
              bgcolor: 'background.paper',
              boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
              border: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.2s ease-in-out',
              '&:hover': {
                bgcolor: 'primary.main',
                color: 'primary.contrastText',
                transform: 'scale(1.05)',
                boxShadow: '0 6px 16px rgba(103, 126, 234, 0.3)',
              },
            }}
          >
            <MenuIcon fontSize={isMobile ? 'medium' : 'large'} />
          </AccessibleIconButton>
        </Fade>
      )}

      {/* 响应式侧边栏 */}
      <Drawer
        variant={isMobile ? 'temporary' : 'persistent'}
        anchor="left"
        open={open}
        onClose={isMobile ? onToggle : undefined}
        ModalProps={{
          keepMounted: true, // Better open performance on mobile.
        }}
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          '& .MuiDrawer-paper': {
            width: drawerWidth,
            boxSizing: 'border-box',
            borderRight: isMobile ? 'none' : '1px solid',
            borderColor: 'divider',
            boxShadow: isMobile ? '0 8px 32px rgba(0,0,0,0.12)' : 'none',
            ...(isMobile && {
              height: '100vh',
              maxHeight: '100vh',
            }),
          },
        }}
      >
        {drawerContent}
      </Drawer>
    </>
  );
};

export default Sidebar;