import React, { useEffect, useState } from 'react';
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
  IconButton,
  Menu,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Collapse,
} from '@mui/material';
import {
  Menu as MenuIcon,
  Add as AddIcon,
  Chat as ChatIcon,
  Close as CloseIcon,
  MoreVert as MoreVertIcon,
  Edit as EditIcon,
  Delete as DeleteIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
} from '@mui/icons-material';

import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox, HoverAnimatedBox } from '@/components/animations';
import { AccessibleIconButton } from '@/components/AccessibleButton';
import { chatApi } from '@/services/api';

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
  const { sessions, currentSession, setCurrentSession, loadSessions, loadChatHistory } = useChatStore();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const isTablet = useMediaQuery(theme.breakpoints.down('lg'));

  // 状态管理
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['今天']));

  useEffect(() => {
    loadSessions();
  }, [loadSessions]);

  // 监听当前会话变化，自动展开包含该会话的分组
  useEffect(() => {
    if (currentSession && sessions.length > 0) {
      const currentSessionObj = sessions.find(s => s.id === currentSession);
      if (currentSessionObj) {
        const groups = groupSessionsByDate(sessions);
        // 找到包含当前会话的分组
        for (const [groupName, groupSessions] of Object.entries(groups)) {
          if (groupSessions.some(s => s.id === currentSession)) {
            setExpandedGroups(prev => new Set([...prev, groupName]));
            break;
          }
        }
      }
    }
  }, [currentSession, sessions]);

  // 日期分组函数
  const groupSessionsByDate = (sessions: any[]) => {
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today.getTime() - 24 * 60 * 60 * 1000);
    const weekAgo = new Date(today.getTime() - 7 * 24 * 60 * 60 * 1000);

    const groups: { [key: string]: any[] } = {
      '今天': [],
      '昨天': [],
      '过去7天': [],
      '更早': []
    };

    sessions.forEach(session => {
      const sessionDate = new Date(session.updatedAt || session.createdAt);
      const sessionDay = new Date(sessionDate.getFullYear(), sessionDate.getMonth(), sessionDate.getDate());

      if (sessionDay.getTime() === today.getTime()) {
        groups['今天'].push(session);
      } else if (sessionDay.getTime() === yesterday.getTime()) {
        groups['昨天'].push(session);
      } else if (sessionDay.getTime() > weekAgo.getTime()) {
        groups['过去7天'].push(session);
      } else {
        groups['更早'].push(session);
      }
    });

    return groups;
  };

  // 菜单操作
  const handleMenuOpen = (event: React.MouseEvent<HTMLElement>, sessionId: string) => {
    event.stopPropagation();
    setMenuAnchorEl(event.currentTarget);
    setSelectedSessionId(sessionId);
  };

  const handleMenuClose = () => {
    setMenuAnchorEl(null);
    setSelectedSessionId(null);
  };

  

  const handleRenameConfirm = async () => {
    if (selectedSessionId && newSessionTitle.trim()) {
      try {
        const response = await fetch(`/api/chat/sessions/${selectedSessionId}`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ title: newSessionTitle.trim() }),
        });
        
        if (response.ok) {
          // 重新加载会话列表以反映更改
          loadSessions();
          console.log('会话重命名成功');
        } else {
          console.error('重命名会话失败');
        }
      } catch (error) {
        console.error('重命名失败:', error);
      }
    }
    setRenameDialogOpen(false);
    setNewSessionTitle('');
    setSelectedSessionId(null);
  };

  const handleDeleteConfirm = async () => {
    if (selectedSessionId) {
      try {
        const result = await chatApi.deleteSession(selectedSessionId);
        if (result.success) {
          // 重新加载会话列表
          loadSessions();
          setDeleteDialogOpen(false);
          if (currentSession === selectedSessionId) {
            setCurrentSession(null);
          }
        } else {
          console.error('删除会话失败:', result.message);
        }
      } catch (error) {
        console.error('删除失败:', error);
      }
    }
    setSelectedSessionId(null);
  };

  const toggleGroup = (groupName: string) => {
    const newExpanded = new Set(expandedGroups);
    if (newExpanded.has(groupName)) {
      newExpanded.delete(groupName);
    } else {
      newExpanded.add(groupName);
    }
    setExpandedGroups(newExpanded);
  };

  const handleSessionClick = async (sessionId: string) => {
    // 找到对应的会话对象
    const session = sessions.find(s => s.id === sessionId);
    if (session) {
      // 设置当前会话
      setCurrentSession(sessionId);
      // 加载会话的完整消息历史
      await loadChatHistory(sessionId);
      // 更新URL
      window.history.pushState(null, '', `/chat/${sessionId}`);
      // 移动端选择会话后自动关闭侧边栏
      if (isMobile) {
        onToggle();
      }
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
          {sessions.length === 0 ? (
            <Fade in timeout={300}>
              <Box sx={{ px: 2.5, py: 3, textAlign: 'center' }}>
                <Typography 
                  variant="body2" 
                  color="text.secondary"
                  sx={{ mb: 1, fontWeight: 500 }}
                >
                  暂无对话
                </Typography>
                <Typography 
                  variant="caption" 
                  color="text.secondary"
                >
                  创建新对话开始使用
                </Typography>
              </Box>
            </Fade>
          ) : (
            Object.entries(groupSessionsByDate(sessions)).map(([groupName, groupSessions]) => {
              if (groupSessions.length === 0) return null;
              
              return (
                <Box key={groupName} sx={{ mb: 1 }}>
                  {/* 日期分组标题 */}
                  <ListItemButton
                    onClick={() => toggleGroup(groupName)}
                    sx={{
                      px: 2.5,
                      py: 1,
                      minHeight: 'auto',
                      '&:hover': {
                        bgcolor: 'action.hover',
                      },
                    }}
                  >
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: 'text.secondary',
                        fontWeight: 600,
                        fontSize: '0.75rem',
                        textTransform: 'uppercase',
                        letterSpacing: 0.5,
                        flexGrow: 1,
                      }}
                    >
                      {groupName}
                    </Typography>
                    <Typography 
                      variant="caption" 
                      sx={{ 
                        color: 'text.secondary',
                        fontSize: '0.7rem',
                        mr: 1,
                      }}
                    >
                      {groupSessions.length}
                    </Typography>
                    {expandedGroups.has(groupName) ? (
                      <ExpandLessIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    ) : (
                      <ExpandMoreIcon sx={{ fontSize: 16, color: 'text.secondary' }} />
                    )}
                  </ListItemButton>
                  
                  {/* 会话列表 */}
                  <Collapse in={expandedGroups.has(groupName)} timeout="auto">
                    <List sx={{ p: 0 }}>
                      {groupSessions.map((session, index) => (
                        <Slide 
                          key={session.id} 
                          direction="right" 
                          in 
                          timeout={200 + index * 50}
                        >
                          <ListItem disablePadding sx={{ px: 1.5, mb: 0.5 }}>
                            <HoverAnimatedBox hoverAnimation="scale" sx={{ width: '100%' }}>
                              <ListItemButton
                                selected={session.id === currentSession}
                                onClick={() => handleSessionClick(session.id)}
                                sx={{
                                  borderRadius: 2,
                                  py: 1.5,
                                  pr: 1,
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
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleMenuOpen(e, session.id)}
                                  sx={{
                                    ml: 1,
                                    opacity: 0.7,
                                    color: session.id === currentSession ? 'white' : 'text.secondary',
                                    '&:hover': {
                                      opacity: 1,
                                      bgcolor: session.id === currentSession 
                                        ? 'rgba(255,255,255,0.1)' 
                                        : 'action.hover',
                                    },
                                  }}
                                >
                                  <MoreVertIcon fontSize="small" />
                                </IconButton>
                              </ListItemButton>
                            </HoverAnimatedBox>
                          </ListItem>
                        </Slide>
                      ))}
                    </List>
                  </Collapse>
                </Box>
              );
            })
          )}
        </Box>
      </Box>

      <Divider />


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
      
      {/* 操作菜单 */}
      <Menu
        anchorEl={menuAnchorEl}
        open={Boolean(menuAnchorEl)}
        onClose={handleMenuClose}
        PaperProps={{
          sx: {
            minWidth: 120,
            boxShadow: '0 4px 20px rgba(0,0,0,0.15)',
            borderRadius: 2,
          },
        }}
      >
        <MenuItem onClick={() => {
           const session = sessions.find(s => s.id === selectedSessionId);
           if (session) {
             setNewSessionTitle(session.title || '');
             setRenameDialogOpen(true);
           }
           handleMenuClose();
         }}>
           <EditIcon sx={{ mr: 1, fontSize: 18 }} />
           重命名
         </MenuItem>
         <MenuItem 
           onClick={() => {
             setDeleteDialogOpen(true);
             handleMenuClose();
           }}
           sx={{ color: 'error.main' }}
         >
          <DeleteIcon sx={{ mr: 1, fontSize: 18 }} />
          删除
        </MenuItem>
      </Menu>
      
      {/* 重命名对话框 */}
      <Dialog 
        open={renameDialogOpen} 
        onClose={() => setRenameDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>重命名会话</DialogTitle>
        <DialogContent>
          <TextField
            autoFocus
            margin="dense"
            label="会话名称"
            fullWidth
            variant="outlined"
            value={newSessionTitle}
        onChange={(e) => setNewSessionTitle(e.target.value)}
            onKeyPress={(e) => {
              if (e.key === 'Enter') {
                handleRenameConfirm();
              }
            }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRenameDialogOpen(false)}>取消</Button>
          <Button onClick={handleRenameConfirm} variant="contained">确认</Button>
        </DialogActions>
      </Dialog>
      
      {/* 删除确认对话框 */}
      <Dialog 
        open={deleteDialogOpen} 
        onClose={() => setDeleteDialogOpen(false)}
      >
        <DialogTitle>删除会话</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除这个会话吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button 
            onClick={handleDeleteConfirm} 
            color="error" 
            variant="contained"
          >
            删除
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default Sidebar;