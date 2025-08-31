import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Typography,
  Card,
  CardContent,
  TextField,
  InputAdornment,
  Pagination,
  Chip,
  IconButton,
  Menu,
  MenuItem,
  FormControl,
  InputLabel,
  Select,
  Grid,
  Skeleton,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Checkbox,
  Tooltip,
  Fab,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  AccessTime as TimeIcon,
  Chat as ChatIcon,
  Delete as DeleteIcon,
  DeleteSweep as DeleteSweepIcon,
  MoreVert as MoreVertIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import { useNavigate } from 'react-router-dom';
import { AnimatedBox } from '@/components/animations';
import { chatApi } from '@/services/api';

interface ChatSession {
  id: string;
  session_id: string;
  title?: string;
  last_message: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

interface HistoryPageProps {}

const HistoryPage: React.FC<HistoryPageProps> = () => {
  const navigate = useNavigate();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at'>('updated_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [filterAnchorEl, setFilterAnchorEl] = useState<null | HTMLElement>(null);
  
  // 新增状态
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [sessionToDelete, setSessionToDelete] = useState<string | null>(null);
  const [selectedSessions, setSelectedSessions] = useState<Set<string>>(new Set());
  const [batchDeleteDialogOpen, setBatchDeleteDialogOpen] = useState(false);
  const [deleting, setDeleting] = useState(false);
  
  const itemsPerPage = 10;



  useEffect(() => {
    loadChatSessions();
  }, [currentPage, sortBy, sortOrder, searchTerm]);

  const loadChatSessions = async () => {
    try {
      setLoading(true);
      setError(null);
      
      const response = await chatApi.getChatSessions(currentPage, itemsPerPage);
      
      if (response && response.sessions) {
        const sessions = response.sessions.map((item: any) => ({
          id: item.id,
          session_id: item.id,
          title: item.title || '未命名对话',
          last_message: item.preview || '暂无对话内容',
          created_at: item.created_at,
          updated_at: item.updated_at,
          message_count: item.message_count || 0
        }));
        
        setSessions(sessions);
        // 计算总页数，基于API返回的总数
        const totalItems = response.total || 0;
        setTotalPages(Math.max(1, Math.ceil(totalItems / itemsPerPage)));
      } else {
        setSessions([]);
        setTotalPages(1);
      }
    } catch (err) {
      setError('加载历史记录失败，请稍后重试');
      console.error('Error loading chat sessions:', err);
      // 如果API调用失败，显示空数据
      setSessions([]);
      setTotalPages(1);
    } finally {
      setLoading(false);
    }
  };

  const handleSessionClick = (sessionId: string) => {
    navigate(`/chat/${sessionId}`);
  };

  const handleDeleteSession = async (sessionId: string, event?: React.MouseEvent) => {
    if (event) {
      event.stopPropagation();
    }
    
    setSessionToDelete(sessionId);
    setDeleteDialogOpen(true);
  };
  
  const confirmDeleteSession = async () => {
    if (!sessionToDelete) return;
    
    setDeleting(true);
    try {
      console.log('开始删除会话:', sessionToDelete);
      const result = await chatApi.deleteSession(sessionToDelete);
      console.log('删除结果:', result);
      
      if (result.success) {
        console.log('删除成功，开始刷新会话列表');
        // 删除成功，重新加载会话列表
        await loadChatSessions();
        console.log('会话列表刷新完成');
        
        // 如果当前页没有数据了，回到上一页
        if (sessions.length === 1 && currentPage > 1) {
          setCurrentPage(prev => prev - 1);
        }
      } else {
        console.error('删除失败:', result.message);
        setError(result.message || '删除会话失败');
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      setError('删除会话失败: ' + (error instanceof Error ? error.message : '未知错误'));
    } finally {
      setDeleting(false);
      setDeleteDialogOpen(false);
      setSessionToDelete(null);
    }
  };
  
  // 批量删除功能
  const handleSelectSession = (sessionId: string, checked: boolean) => {
    setSelectedSessions(prev => {
      const newSet = new Set(prev);
      if (checked) {
        newSet.add(sessionId);
      } else {
        newSet.delete(sessionId);
      }
      return newSet;
    });
  };
  
  const handleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedSessions(new Set(sessions.map(s => s.session_id)));
    } else {
      setSelectedSessions(new Set());
    }
  };
  
  const handleBatchDelete = () => {
    if (selectedSessions.size > 0) {
      setBatchDeleteDialogOpen(true);
    }
  };
  
  const confirmBatchDelete = async () => {
    setDeleting(true);
    try {
      const deletePromises = Array.from(selectedSessions).map(sessionId => 
        chatApi.deleteSession(sessionId)
      );
      
      const results = await Promise.allSettled(deletePromises);
      const successCount = results.filter(r => r.status === 'fulfilled' && r.value.success).length;
      const failCount = results.length - successCount;
      
      if (failCount > 0) {
        setError(`批量删除完成，成功 ${successCount} 个，失败 ${failCount} 个`);
      }
      
      // 重新加载数据
      await loadChatSessions();
      setSelectedSessions(new Set());
      
    } catch (error) {
      console.error('批量删除失败:', error);
      setError('批量删除失败');
    } finally {
      setDeleting(false);
      setBatchDeleteDialogOpen(false);
    }
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'yyyy年MM月dd日 HH:mm', { locale: zhCN });
  };

  

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };

  const renderSessionCard = (session: ChatSession) => {
    const isSelected = selectedSessions.has(session.session_id);
    
    return (
      <AnimatedBox key={session.id} animation="fadeInUp" duration="0.4s">
        <Card
          sx={{
            mb: 2,
            cursor: 'pointer',
            transition: 'all 0.2s ease-in-out',
            border: isSelected ? '2px solid' : '1px solid',
            borderColor: isSelected ? 'primary.main' : 'divider',
            backgroundColor: isSelected ? 'primary.50' : 'background.paper',
            '&:hover': {
              transform: 'translateY(-2px)',
              boxShadow: 4,
            },
          }}
        >
          <CardContent>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', mb: 1 }}>
              {/* 选择框 */}
              <Checkbox
                checked={isSelected}
                onChange={(e) => {
                  e.stopPropagation();
                  handleSelectSession(session.session_id, e.target.checked);
                }}
                sx={{ mt: -1, mr: 1 }}
              />
              
              {/* 会话信息 */}
              <Box 
                sx={{ flexGrow: 1, cursor: 'pointer' }}
                onClick={() => handleSessionClick(session.session_id)}
              >
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
                  <Typography variant="h6" component="h3" sx={{ fontWeight: 600, color: 'primary.main' }}>
                    {session.title || `对话 ${session.session_id.slice(-6)}`}
                  </Typography>
                </Box>
                
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <TimeIcon fontSize="small" color="action" />
                      <Typography variant="caption" color="text.secondary">
                        {formatDate(session.updated_at)}
                      </Typography>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <ChatIcon fontSize="small" color="action" />
                      <Typography variant="caption" color="text.secondary">
                        {session.message_count} 条消息
                      </Typography>
                    </Box>
                  </Box>
                  <Chip
                    label="查看详情"
                    size="small"
                    variant="outlined"
                    color="primary"
                  />
                </Box>
              </Box>
              
              {/* 删除按钮 */}
              <Tooltip title="删除会话">
                <IconButton
                  size="small"
                  onClick={(e) => handleDeleteSession(session.session_id, e)}
                  sx={{ 
                    color: 'text.secondary',
                    '&:hover': {
                      color: 'error.main',
                      backgroundColor: 'error.50'
                    }
                  }}
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Tooltip>
            </Box>
          </CardContent>
        </Card>
      </AnimatedBox>
    );
  };

  const renderSkeletonCard = () => (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Skeleton variant="text" width="60%" height={32} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="100%" height={20} sx={{ mb: 1 }} />
        <Skeleton variant="text" width="80%" height={20} sx={{ mb: 2 }} />
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Box sx={{ display: 'flex', gap: 2 }}>
            <Skeleton variant="text" width={120} height={16} />
            <Skeleton variant="text" width={80} height={16} />
          </Box>
          <Skeleton variant="rectangular" width={80} height={24} sx={{ borderRadius: 1 }} />
        </Box>
      </CardContent>
    </Card>
  );

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <AnimatedBox animation="fadeInDown" duration="0.6s">
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 4 }}>
          <Typography variant="h4" component="h1" sx={{ fontWeight: 700, color: 'primary.main' }}>
            历史记录
          </Typography>
          
          {/* 批量操作按钮 */}
          {selectedSessions.size > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Chip 
                label={`已选择 ${selectedSessions.size} 个会话`}
                color="primary"
                variant="outlined"
              />
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteSweepIcon />}
                onClick={handleBatchDelete}
                disabled={deleting}
              >
                批量删除
              </Button>
            </Box>
          )}
        </Box>
      </AnimatedBox>

      {/* Search and Filter Bar */}
      <AnimatedBox animation="fadeInUp" duration="0.5s">
        <Box sx={{ mb: 4 }}>
          <Grid container spacing={2} alignItems="center">
            {/* @ts-ignore */}
            <Grid xs={12} md={8}>
              <TextField
                fullWidth
                placeholder="搜索对话内容..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon color="action" />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': {
                    borderRadius: 2,
                  },
                }}
              />
            </Grid>
            {/* @ts-ignore */}
            <Grid xs={12} md={4}>
              <Box sx={{ display: 'flex', gap: 1 }}>
                <FormControl size="small" sx={{ minWidth: 120 }}>
                  <InputLabel>排序方式</InputLabel>
                  <Select
                    value={`${sortBy}_${sortOrder}`}
                    label="排序方式"
                    onChange={(e) => {
                      const [field, order] = e.target.value.split('_');
                      setSortBy(field as 'created_at' | 'updated_at');
                      setSortOrder(order as 'asc' | 'desc');
                    }}
                  >
                    <MenuItem value="updated_at_desc">最近更新</MenuItem>
                    <MenuItem value="updated_at_asc">最早更新</MenuItem>
                    <MenuItem value="created_at_desc">最近创建</MenuItem>
                    <MenuItem value="created_at_asc">最早创建</MenuItem>
                  </Select>
                </FormControl>
                <IconButton onClick={handleFilterClick} sx={{ border: 1, borderColor: 'divider' }}>
                  <FilterIcon />
                </IconButton>
              </Box>
            </Grid>
          </Grid>
        </Box>
      </AnimatedBox>

      {/* Filter Menu */}
      <Menu
        anchorEl={filterAnchorEl}
        open={Boolean(filterAnchorEl)}
        onClose={handleFilterClose}
      >
        <MenuItem onClick={handleFilterClose}>今天</MenuItem>
        <MenuItem onClick={handleFilterClose}>本周</MenuItem>
        <MenuItem onClick={handleFilterClose}>本月</MenuItem>
        <MenuItem onClick={handleFilterClose}>全部</MenuItem>
      </Menu>

      {/* Content */}
      <Box>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {loading ? (
          <Box>
            {Array.from({ length: 5 }).map((_, index) => (
              <div key={index}>{renderSkeletonCard()}</div>
            ))}
          </Box>
        ) : sessions.length === 0 ? (
          <AnimatedBox animation="fadeIn" duration="0.5s">
            <Box
              sx={{
                textAlign: 'center',
                py: 8,
                color: 'text.secondary',
              }}
            >
              <ChatIcon sx={{ fontSize: 64, mb: 2, opacity: 0.5 }} />
              <Typography variant="h6" sx={{ mb: 1 }}>
                {searchTerm ? '未找到匹配的对话记录' : '暂无对话记录'}
              </Typography>
              <Typography variant="body2">
                {searchTerm ? '尝试使用其他关键词搜索' : '开始您的第一次对话吧'}
              </Typography>
            </Box>
          </AnimatedBox>
        ) : (
          <>
            {/* 全选按钮 */}
            {sessions.length > 0 && (
              <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
                <Checkbox
                  checked={selectedSessions.size === sessions.length && sessions.length > 0}
                  indeterminate={selectedSessions.size > 0 && selectedSessions.size < sessions.length}
                  onChange={(e) => handleSelectAll(e.target.checked)}
                />
                <Typography variant="body2" color="text.secondary">
                  {selectedSessions.size === sessions.length ? '取消全选' : '全选'}
                </Typography>
              </Box>
            )}
            
            {sessions.map(renderSessionCard)}
            
            {/* Pagination */}
            {totalPages > 1 && (
              <AnimatedBox animation="fadeInUp" duration="0.4s">
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={(_, page) => setCurrentPage(page)}
                    color="primary"
                    size="large"
                    showFirstButton
                    showLastButton
                  />
                </Box>
              </AnimatedBox>
            )}
          </>
        )}
      </Box>
      
      {/* 单个删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => !deleting && setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>删除会话</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除这个会话吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteDialogOpen(false)} disabled={deleting}>
            取消
          </Button>
          <Button 
            onClick={confirmDeleteSession} 
            color="error" 
            variant="contained"
            disabled={deleting}
          >
            {deleting ? '删除中...' : '删除'}
          </Button>
        </DialogActions>
      </Dialog>
      
      {/* 批量删除确认对话框 */}
      <Dialog
        open={batchDeleteDialogOpen}
        onClose={() => !deleting && setBatchDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>批量删除会话</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除选中的 {selectedSessions.size} 个会话吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setBatchDeleteDialogOpen(false)} disabled={deleting}>
            取消
          </Button>
          <Button 
            onClick={confirmBatchDelete} 
            color="error" 
            variant="contained"
            disabled={deleting}
          >
            {deleting ? '删除中...' : `删除 ${selectedSessions.size} 个会话`}
          </Button>
        </DialogActions>
      </Dialog>
    </Container>
  );
};

export default HistoryPage;