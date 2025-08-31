import React, { useState, useEffect } from 'react';
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
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
} from '@mui/icons-material';

import { useChatStore } from '@/stores/chatStore';
import { AnimatedBox, HoverAnimatedBox } from '@/components/animations';
import { AccessibleIconButton } from '@/components/AccessibleButton';
import { chatApi } from '@/services/api';

interface SidebarProps {
  open: boolean;
  onToggle: () => void;
  onCreateSession: () => void;
  onWidthChange?: (width: number) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ open, onToggle, onCreateSession, onWidthChange }) => {
  const { sessions, currentSession, setCurrentSession, loadSessions, loadChatHistory } = useChatStore();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  // 状态管理
  const [menuAnchorEl, setMenuAnchorEl] = useState<null | HTMLElement>(null);
  const [selectedSessionId, setSelectedSessionId] = useState<string | null>(null);
  const [renameDialogOpen, setRenameDialogOpen] = useState(false);
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [newSessionTitle, setNewSessionTitle] = useState('');
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(['今天']));
  const [drawerWidth, setDrawerWidth] = useState(isMobile ? window.innerWidth : 280);
  const [isResizing, setIsResizing] = useState(false);
  const [collapsed, setCollapsed] = useState(false);
  const minWidth = 200;
  const maxWidth = 500;
  const collapsedWidth = 60;

  // 监听状态变化
  useEffect(() => {
    // 组件状态更新时的处理逻辑可以在这里添加
  }, [currentSession, sessions]);

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
            // 自动展开包含当前会话的分组
            setExpandedGroups(prev => new Set([...prev, groupName]));
            break;
          }
        }
      }
    }
  }, [currentSession, sessions]);

  // 监听屏幕尺寸变化，调整侧边栏状态
  useEffect(() => {
    if (isMobile) {
      setDrawerWidth(window.innerWidth * 0.8); // 移动端使用80%宽度
    } else {
      setDrawerWidth(280); // PC端恢复默认宽度
    }
    // 移动端也支持折叠模式，与PC端保持一致
    
    // 立即同步宽度给父组件
    const currentWidth = collapsed ? collapsedWidth : (isMobile ? window.innerWidth * 0.8 : 280);
    onWidthChange?.(currentWidth);
  }, [isMobile, collapsed, onWidthChange]);

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

      // 分组逻辑处理

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
    // 注意：不要在这里清除selectedSessionId，因为菜单项的onClick需要使用它
    // setSelectedSessionId(null);
  };

  

  const handleRenameConfirm = async () => {
    if (!selectedSessionId) {
      alert('未选择会话');
      return;
    }
    
    // 更严格的输入验证
    if (!newSessionTitle) {
      alert('请输入会话名称');
      return;
    }
    
    const trimmedTitle = newSessionTitle.trim();
    if (!trimmedTitle) {
      alert('请输入有效的会话名称');
      return;
    }
    
    if (trimmedTitle.length > 100) {
      alert('会话名称不能超过100个字符');
      return;
    }
    
    try {
      const result = await chatApi.renameSession(selectedSessionId, trimmedTitle);
      
      if (result.success) {
        // 重新加载会话列表以反映更改
        await loadSessions();
        setRenameDialogOpen(false);
        setNewSessionTitle('');
        setSelectedSessionId(null);
      } else {
        // 显示错误信息
        alert(result.message || '重命名失败');
      }
    } catch (error) {
      alert('重命名会话失败: ' + (error instanceof Error ? error.message : '未知错误'));
    }
  };

  const handleDeleteConfirm = async () => {
    if (!selectedSessionId) {
      alert('未选择会话');
      setSelectedSessionId(null);
      setDeleteDialogOpen(false);
      return;
    }
    
    try {
      const result = await chatApi.deleteSession(selectedSessionId);
      
      if (result.success) {
        // 如果删除的是当前会话，先清除当前会话状态
        if (currentSession === selectedSessionId) {
          setCurrentSession(null);
          // 导航到首页或选择其他会话
          window.history.pushState(null, '', '/chat');
        }
        
        // 重新加载会话列表
        await loadSessions();
        
      } else {
        alert(result.message || '删除会话失败');
      }
    } catch (error) {
      alert('删除会话失败: ' + (error instanceof Error ? error.message : '未知错误'));
    } finally {
      // 确保对话框关闭和状态清理
      setDeleteDialogOpen(false);
      setSelectedSessionId(null);
    }
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
      // 立即设置当前会话，确保 UI 即时更新
      setCurrentSession(sessionId);
      
      try {
        // 加载会话的完整消息历史(已在chatStore中处理滚动)
        await loadChatHistory(sessionId);
        
        // 更新URL
        window.history.pushState(null, '', `/chat/${sessionId}`);
        
        // 移动端选择会话后自动关闭侧边栏
        if (isMobile) {
          onToggle();
        }
      } catch (error) {
        // 加载会话历史失败处理
      }
    }
  };

  const handleMouseDown = (e: React.MouseEvent) => {
    if (isMobile) return;
    setIsResizing(true);
    e.preventDefault();
  };

  const handleMouseMove = (e: MouseEvent) => {
     if (!isResizing || isMobile) return;
     const newWidth = Math.min(Math.max(e.clientX, minWidth), maxWidth);
     setDrawerWidth(newWidth);
     onWidthChange?.(newWidth);
   };

  const handleMouseUp = () => {
    setIsResizing(false);
  };

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
      return () => {
        document.removeEventListener('mousemove', handleMouseMove);
        document.removeEventListener('mouseup', handleMouseUp);
      };
    }
  }, [isResizing]);

  const toggleCollapse = () => {
     const newCollapsed = !collapsed;
     setCollapsed(newCollapsed);
     const newWidth = newCollapsed ? collapsedWidth : drawerWidth;
     setDrawerWidth(newWidth);
     onWidthChange?.(newWidth);
   };

  const effectiveWidth = collapsed ? collapsedWidth : (isMobile ? '80vw' : `${drawerWidth}px`);
  const mobileCollapsedWidth = 60; // 移动端折叠宽度

  const getMobileEffectiveWidth = () => {
    if (!isMobile) return effectiveWidth;
    return collapsed ? `${mobileCollapsedWidth}px` : '80vw';
  };

  const finalEffectiveWidth = getMobileEffectiveWidth();

  const drawerContent = (
    <AnimatedBox animation="fadeInLeft" duration="0.4s">
      <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
        {/* 切换按钮 */}
        {!isMobile && (
          <Box
            sx={{
              p: 1,
              display: 'flex',
              justifyContent: collapsed ? 'center' : 'flex-end',
              borderBottom: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            }}
          >
            <IconButton onClick={toggleCollapse} size="small" sx={{
              background: 'rgba(255, 255, 255, 0.1)',
              backdropFilter: 'blur(10px)',
              border: '1px solid rgba(255, 255, 255, 0.2)',
              color: 'text.primary',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              '&:hover': {
                background: 'rgba(103, 126, 234, 0.1)',
                borderColor: 'rgba(103, 126, 234, 0.3)',
                transform: 'scale(1.1)',
                color: 'primary.main',
              },
            }}>
              {collapsed ? <ChevronRightIcon /> : <ChevronLeftIcon />}
            </IconButton>
          </Box>
        )}
        {isMobile && (
          <Box
            sx={{
              p: 1.5,
              display: 'flex',
              justifyContent: collapsed ? 'center' : 'space-between',
              alignItems: 'center',
              borderBottom: '1px solid',
              borderColor: 'divider',
              transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
              minHeight: 56, // 确保有足够的点击区域
            }}
          >
            <IconButton 
              onClick={toggleCollapse} 
              size="large"
              sx={{
                width: 48,
                height: 48,
                bgcolor: 'rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                border: '2px solid',
                borderColor: 'rgba(255, 255, 255, 0.2)',
                color: 'text.primary',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  bgcolor: 'rgba(103, 126, 234, 0.1)',
                  borderColor: 'rgba(103, 126, 234, 0.4)',
                  color: 'primary.main',
                  transform: 'scale(1.1)',
                  boxShadow: '0 4px 15px rgba(103, 126, 234, 0.2)',
                },
              }}
            >
              {collapsed ? (
                <ChevronRightIcon sx={{ fontSize: 24, fontWeight: 'bold' }} />
              ) : (
                <ChevronLeftIcon sx={{ fontSize: 24, fontWeight: 'bold' }} />
              )}
            </IconButton>
            {!collapsed && (
              <IconButton 
                onClick={onToggle} 
                edge="end"
                size="large"
                sx={{
                  width: 48,
                  height: 48,
                  bgcolor: 'rgba(255, 255, 255, 0.1)',
                  backdropFilter: 'blur(10px)',
                  border: '2px solid',
                  borderColor: 'rgba(255, 255, 255, 0.2)',
                  color: 'text.primary',
                  transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                  '&:hover': {
                    bgcolor: 'rgba(244, 67, 54, 0.1)',
                    borderColor: 'rgba(244, 67, 54, 0.4)',
                    color: 'error.main',
                    transform: 'scale(1.1)',
                    boxShadow: '0 4px 15px rgba(244, 67, 54, 0.2)',
                  },
                }}
              >
                <CloseIcon sx={{ fontSize: 24, fontWeight: 'bold' }} />
              </IconButton>
            )}
          </Box>
        )}

        {/* 现代化操作按钮 */}
        {!collapsed && (
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
                    py: 1.5,
                    borderRadius: 3,
                    background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #9c88ff 100%)',
                    boxShadow: '0 6px 20px rgba(103, 126, 234, 0.4)',
                    fontSize: isMobile ? '0.9rem' : '1rem',
                    fontWeight: 600,
                    position: 'relative',
                    overflow: 'hidden',
                    border: '1px solid rgba(255, 255, 255, 0.2)',
                    backdropFilter: 'blur(10px)',
                    transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                    '&::before': {
                      content: '""',
                      position: 'absolute',
                      top: 0,
                      left: '-100%',
                      width: '100%',
                      height: '100%',
                      background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                      transition: 'left 0.6s ease',
                    },
                    '&:hover': {
                      transform: 'translateY(-3px) scale(1.02)',
                      background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 50%, #8b7fff 100%)',
                      boxShadow: '0 8px 25px rgba(103, 126, 234, 0.5)',
                      borderColor: 'rgba(255, 255, 255, 0.4)',
                    },
                    '&:hover::before': {
                      left: '100%',
                    },
                    '&:active': {
                      transform: 'translateY(-1px) scale(1.01)',
                      boxShadow: '0 4px 15px rgba(103, 126, 234, 0.4)',
                    },
                  }}
                >
                  新建对话
                </Button>
              </HoverAnimatedBox>

            </Box>
          </AnimatedBox>
        )}
        {collapsed && (
          <Box sx={{ p: 1, display: 'flex', justifyContent: 'center' }}>
            <IconButton
              onClick={onCreateSession}
              sx={{
                bgcolor: 'primary.main',
                color: 'white',
                width: 48,
                height: 48,
                background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                boxShadow: '0 4px 15px rgba(103, 126, 234, 0.4)',
                border: '2px solid rgba(255, 255, 255, 0.2)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                  transform: 'scale(1.1)',
                  boxShadow: '0 6px 20px rgba(103, 126, 234, 0.5)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
                },
              }}
            >
              <AddIcon />
            </IconButton>
          </Box>
        )}

      <Divider />

      {/* 现代化会话列表 */}
      {!collapsed && (
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
      )}
      
      <Box 
        sx={{ 
          maxHeight: 'calc(100vh - 280px)',
          overflow: 'auto',
          overflowX: 'hidden',
          paddingBottom: 2,
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
            !collapsed && (
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
            )
          ) : (
            Object.entries(groupSessionsByDate(sessions)).map(([groupName, groupSessions]) => {
              if (groupSessions.length === 0) return null;
              
              // 分组信息处理
              
              return (
                <Box key={groupName} sx={{ mb: 1 }}>
                  {/* 日期分组标题 */}
                  {!collapsed && (
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
                  )}
                  
                  {/* 会话列表 */}
                  <Collapse in={collapsed || expandedGroups.has(groupName)} timeout="auto">
                    <List sx={{ p: 0 }}>
                      {groupSessions.map((session) => {
                        const isSelected = session.id === currentSession;
                        
                        // 选中状态处理逻辑
                        return (
                        <ListItem key={session.id} disablePadding sx={{ px: collapsed ? 0.5 : 1.5, mb: 0.5 }}>
                          <HoverAnimatedBox hoverAnimation="scale" sx={{ width: '100%' }}>
                            <ListItemButton
                              selected={isSelected}
                              onClick={() => handleSessionClick(session.id)}
                              style={{
                                borderRadius: '12px',
                                paddingTop: '12px',
                                paddingBottom: '12px',
                                paddingRight: collapsed ? '4px' : '8px',
                                paddingLeft: collapsed ? '4px' : '16px',
                                justifyContent: collapsed ? 'center' : 'flex-start',
                                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                position: 'relative',
                                overflow: 'hidden',
                                backdropFilter: 'blur(10px)',
                                ...(isSelected ? {
                                  background: 'linear-gradient(135deg, #667eea 0%, #764ba2 50%, #9c88ff 100%)',
                                  backgroundColor: 'transparent',
                                  color: 'white',
                                  border: '1px solid rgba(255, 255, 255, 0.3)',
                                  boxShadow: '0 4px 15px rgba(103, 126, 234, 0.3)',
                                } : {
                                  background: 'rgba(255, 255, 255, 0.5)',
                                  backgroundColor: 'rgba(255, 255, 255, 0.5)',
                                  border: '1px solid rgba(0, 0, 0, 0.08)',
                                  color: 'inherit',
                                  boxShadow: '0 2px 8px rgba(0, 0, 0, 0.05)',
                                })
                              }}
                            >
                              <ListItemIcon sx={{ minWidth: collapsed ? 'auto' : 40, justifyContent: 'center' }}>
                                <HoverAnimatedBox hoverAnimation="scale" sx={{ minWidth: collapsed ? 'auto' : 40, justifyContent: 'center' }}>
                                  <Avatar
                                    style={{
                                      width: '36px',
                                      height: '36px',
                                      fontSize: '14px',
                                      border: '2px solid',
                                      transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                                      ...(isSelected ? {
                                        backgroundColor: 'rgba(255,255,255,0.2)',
                                        borderColor: 'rgba(255,255,255,0.3)',
                                        boxShadow: '0 2px 8px rgba(0,0,0,0.2)',
                                        color: 'white',
                                      } : {
                                        backgroundColor: '#667eea',
                                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                                        borderColor: 'rgba(103, 126, 234, 0.2)',
                                        boxShadow: '0 2px 8px rgba(103, 126, 234, 0.3)',
                                        color: 'white',
                                      })
                                    }}
                                  >
                                    <ChatIcon fontSize="small" />
                                  </Avatar>
                                </HoverAnimatedBox>
                              </ListItemIcon>
                              {!collapsed && (
                                <ListItemText
                                  primary={session.title}
                                  secondary={`${session.messageCount} 条消息`}
                                  primaryTypographyProps={{
                                    noWrap: true,
                                    fontSize: isMobile ? '0.85rem' : '0.9rem',
                                    fontWeight: 500,
                                    style: {
                                      color: isSelected ? 'white' : 'inherit',
                                      fontWeight: isSelected ? '600' : '500',
                                    }
                                  }}
                                  secondaryTypographyProps={{
                                    fontSize: isMobile ? '0.7rem' : '0.75rem',
                                    style: {
                                      color: isSelected ? 'rgba(255,255,255,0.8)' : 'inherit',
                                    }
                                  }}
                                />
                              )}
                              {!collapsed && (
                                <IconButton
                                  size="small"
                                  onClick={(e) => handleMenuOpen(e, session.id)}
                                  style={{
                                    marginLeft: '8px',
                                    opacity: 0.7,
                                    color: isSelected ? 'white' : 'inherit',
                                    transition: 'all 0.2s ease',
                                  }}
                                >
                                  <MoreVertIcon fontSize="small" />
                                </IconButton>
                              )}
                            </ListItemButton>
                          </HoverAnimatedBox>
                        </ListItem>
                        );
                      })}
                    </List>
                  </Collapse>
                </Box>
              );
            })
          )}
        </Box>

      <Divider />

    </Box>
    </AnimatedBox>
  );

  return (
    <>
      {/* 移动端背景遮罩层 */}
      {isMobile && open && (
        <Box
          onClick={collapsed ? undefined : onToggle}
          sx={{
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100vw',
            height: '100vh',
            backgroundColor: collapsed ? 'transparent' : 'rgba(0, 0, 0, 0.3)',
            zIndex: 799,
            cursor: collapsed ? 'default' : 'pointer',
          }}
        />
      )}

      {/* 移动端打开侧边栏按钮 */}
      {!open && isMobile && (
        <AccessibleIconButton
          onClick={onToggle}
          aria-label="打开侧边栏"
          sx={{
            position: 'fixed',
            top: 16,
            left: 16,
            zIndex: 1300,
            width: 64,
            height: 64,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            color: 'white',
            boxShadow: '0 6px 20px rgba(103, 126, 234, 0.4)',
            border: '2px solid rgba(255, 255, 255, 0.3)',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
              transform: 'scale(1.1)',
              boxShadow: '0 8px 25px rgba(103, 126, 234, 0.5)',
              borderColor: 'rgba(255, 255, 255, 0.5)',
            },
            '&:active': {
              transform: 'scale(1.05)',
            },
          }}
        >
          <ChevronRightIcon sx={{ fontSize: 32, fontWeight: 'bold', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }} />
        </AccessibleIconButton>
      )}

      {/* PC端打开侧边栏按钮 */}
      {!open && !isMobile && (
        <AccessibleIconButton
          onClick={onToggle}
          aria-label="打开侧边栏"
          sx={{
            position: 'fixed',
            top: 16,
            left: 16,
            zIndex: 1300,
            width: 60,
            height: 60,
            bgcolor: 'background.paper',
            boxShadow: '0 6px 20px rgba(0,0,0,0.15)',
            border: '2px solid',
            borderColor: 'divider',
            backdropFilter: 'blur(10px)',
            background: 'rgba(255, 255, 255, 0.95)',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: 'white',
              transform: 'scale(1.1)',
              boxShadow: '0 8px 25px rgba(103, 126, 234, 0.4)',
              borderColor: 'rgba(103, 126, 234, 0.3)',
            },
            '&:active': {
              transform: 'scale(1.05)',
            },
          }}
        >
          <MenuIcon sx={{ fontSize: 28, transition: 'all 0.3s ease' }} />
        </AccessibleIconButton>
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
          width: finalEffectiveWidth,
          flexShrink: 0,
          zIndex: 800,
          transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '& .MuiDrawer-paper': {
            width: finalEffectiveWidth,
            boxSizing: 'border-box',
            borderRight: isMobile ? 'none' : '1px solid',
            borderColor: 'divider',
            boxShadow: isMobile ? '0 8px 32px rgba(0,0,0,0.12)' : 'none',
            position: 'fixed',
            top: isMobile ? '0' : '64px',
            transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            height: isMobile ? '100vh' : 'calc(100vh - 64px)',
            maxHeight: isMobile ? '100vh' : 'calc(100vh - 64px)',
            overflow: 'hidden',
          },
        }}
      >
        {drawerContent}
        {/* 拖拽调整宽度的手柄 */}
        {!isMobile && !collapsed && (
          <Box
            onMouseDown={handleMouseDown}
            sx={{
              position: 'absolute',
              top: 0,
              right: -2,
              width: 4,
              height: '100%',
              cursor: 'col-resize',
              bgcolor: 'transparent',
              '&:hover': {
                bgcolor: 'primary.main',
              },
              zIndex: 1201,
            }}
          />
        )}
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
             const initialTitle = session.title || '新对话';
             setNewSessionTitle(initialTitle);
             setRenameDialogOpen(true);
             handleMenuClose(); // 关闭菜单但保留selectedSessionId
           } else {
             alert('找不到对应的会话');
             setSelectedSessionId(null); // 只有在错误情况下才清除
             handleMenuClose();
           }
         }}>
           <EditIcon sx={{ mr: 1, fontSize: 18 }} />
           重命名
         </MenuItem>
         <MenuItem 
           onClick={() => {
             setDeleteDialogOpen(true);
             handleMenuClose(); // 关闭菜单但保留selectedSessionId
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
        onClose={() => {
          setRenameDialogOpen(false);
          setSelectedSessionId(null); // 关闭对话框时清除选中的会话ID
        }}
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
          <Button onClick={() => {
            setRenameDialogOpen(false);
            setSelectedSessionId(null); // 取消时清除选中的会话ID
          }}>取消</Button>
          <Button onClick={handleRenameConfirm} variant="contained">确认</Button>
        </DialogActions>
      </Dialog>
      
      {/* 删除确认对话框 */}
      <Dialog 
        open={deleteDialogOpen} 
        onClose={() => {
          setDeleteDialogOpen(false);
          setSelectedSessionId(null); // 关闭对话框时清除选中的会话ID
        }}
      >
        <DialogTitle>删除会话</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除这个会话吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => {
            setDeleteDialogOpen(false);
            setSelectedSessionId(null); // 取消时清除选中的会话ID
          }}>取消</Button>
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