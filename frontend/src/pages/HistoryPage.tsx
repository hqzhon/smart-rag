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
  Grid2,
  Skeleton,
  Alert,
  Divider,
} from '@mui/material';
import {
  Search as SearchIcon,
  FilterList as FilterIcon,
  AccessTime as TimeIcon,
  Chat as ChatIcon,
  Delete as DeleteIcon,
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

  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation();
    
    if (!window.confirm('确定要删除这个对话记录吗？')) {
      return;
    }
    
    try {
      const result = await chatApi.deleteSession(sessionId);
      if (result.success) {
        // 删除成功，重新加载会话列表
        await loadChatSessions();
        
        // 如果当前页没有数据了，回到上一页
        if (sessions.length === 1 && currentPage > 1) {
          setCurrentPage(prev => prev - 1);
        }
      } else {
        alert(result.message || '删除会话失败');
      }
    } catch (error) {
      console.error('删除会话失败:', error);
      alert('删除会话失败');
    }
  };

  const formatDate = (dateString: string) => {
    return format(new Date(dateString), 'yyyy年MM月dd日 HH:mm', { locale: zhCN });
  };

  const truncateText = (text: string, maxLength: number = 100) => {
    return text.length > maxLength ? text.substring(0, maxLength) + '...' : text;
  };

  const handleFilterClick = (event: React.MouseEvent<HTMLElement>) => {
    setFilterAnchorEl(event.currentTarget);
  };

  const handleFilterClose = () => {
    setFilterAnchorEl(null);
  };

  const renderSessionCard = (session: ChatSession) => (
    <AnimatedBox key={session.id} animation="fadeInUp" duration="0.4s">
      <Card
        sx={{
          mb: 2,
          cursor: 'pointer',
          transition: 'all 0.2s ease-in-out',
          '&:hover': {
            transform: 'translateY(-2px)',
            boxShadow: 4,
          },
        }}
        onClick={() => handleSessionClick(session.session_id)}
      >
        <CardContent>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
            <Typography variant="h6" component="h3" sx={{ fontWeight: 600, color: 'primary.main' }}>
              {session.title || `对话 ${session.session_id.slice(-6)}`}
            </Typography>
            <IconButton
              size="small"
              onClick={(e) => handleDeleteSession(session.session_id, e)}
              sx={{ color: 'text.secondary' }}
            >
              <DeleteIcon fontSize="small" />
            </IconButton>
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
        </CardContent>
      </Card>
    </AnimatedBox>
  );

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
        <Typography variant="h4" component="h1" sx={{ mb: 4, fontWeight: 700, color: 'primary.main' }}>
          历史记录
        </Typography>
      </AnimatedBox>

      {/* Search and Filter Bar */}
      <AnimatedBox animation="fadeInUp" duration="0.5s">
        <Box sx={{ mb: 4 }}>
          <Grid2 container spacing={2} alignItems="center">
            <Grid2 xs={12} md={8}>
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
            </Grid2>
            <Grid2 xs={12} md={4}>
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
              </Grid2>
            </Grid2>
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
    </Container>
  );
};

export default HistoryPage;