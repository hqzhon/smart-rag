import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  Alert,
  Snackbar,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Fab,
  Divider,
  Tabs,
  Tab,
  Pagination,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  CircularProgress,
} from '@mui/material';
import { SelectChangeEvent } from '@mui/material/Select';
import {
  Add as AddIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';

import DocumentUploader from '../components/DocumentUploader';
import LazyDocumentList from '../components/LazyDocumentList';
import ChunkingConfig from '../components/ChunkingConfig';
import { AnimatedBox, HoverAnimatedBox } from '../components/animations';
import { AccessibleButton } from '../components/AccessibleButton';
import { documentApi } from '@/services/api';

interface Document {
  id: string;
  name: string;
  size: number;
  uploadTime: string;
  type: string;
}

const FileManagementPage: React.FC = () => {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [snackbarOpen, setSnackbarOpen] = useState(false);
  const [snackbarMessage, setSnackbarMessage] = useState('');
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [documentToDelete, setDocumentToDelete] = useState<string | null>(null);
  const [currentTab, setCurrentTab] = useState(0);
  
  // 分页相关状态
  const [currentPage, setCurrentPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [totalDocuments, setTotalDocuments] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  // 加载文档列表
  const loadDocuments = useCallback(async (page?: number, size?: number, retryCount = 0) => {
    setIsLoading(true);
    setError(null);
    
    const targetPage = page || currentPage;
    const targetSize = size || pageSize;
    
    try {
      const response = await documentApi.getDocuments({
        page: targetPage,
        page_size: targetSize
      });
      
      setDocuments(response.documents || []);
      setTotalDocuments(response.total || 0);
      setTotalPages(response.total_pages || 0);
      setCurrentPage(response.page || targetPage);
      setPageSize(response.page_size || targetSize);
    } catch (err) {
      let errorMessage = '加载文档列表失败';
      
      if (err instanceof Error) {
        // 网络错误处理
        if (err.message.includes('Network Error') || err.message.includes('fetch')) {
          errorMessage = '网络连接失败，请检查网络连接';
        } else if (err.message.includes('timeout')) {
          errorMessage = '请求超时，请稍后重试';
        } else if (err.message.includes('500')) {
          errorMessage = '服务器内部错误，请稍后重试';
        } else if (err.message.includes('404')) {
          errorMessage = '请求的资源不存在';
        } else {
          errorMessage = err.message;
        }
      }
      
      setError(errorMessage);
      console.error('Failed to load documents:', err);
      
      // 自动重试机制（最多重试2次）
      if (retryCount < 2 && (errorMessage.includes('网络') || errorMessage.includes('超时'))) {
        setTimeout(() => {
          loadDocuments(page, size, retryCount + 1);
        }, 1000 * (retryCount + 1)); // 递增延迟
      }
    } finally {
      setIsLoading(false);
    }
  }, [currentPage, pageSize]);

  // 页面加载时获取文档列表
  useEffect(() => {
    loadDocuments();
  }, [loadDocuments]);

  // 处理上传成功
  const handleUploadSuccess = useCallback((uploadedDocuments: Array<{ file: File; response: any }>) => {
    console.log('Upload success:', uploadedDocuments);
    
    // 显示成功消息
    const count = uploadedDocuments.length;
    setSnackbarMessage(`成功上传 ${count} 个文档`);
    setSnackbarOpen(true);
    
    // 关闭上传对话框
    setUploadDialogOpen(false);
    
    // 刷新文档列表
    loadDocuments();
  }, [loadDocuments]);

  // 处理删除文档
  const handleDeleteDocument = useCallback(async (documentId: string) => {
    setDocumentToDelete(documentId);
    setDeleteDialogOpen(true);
  }, []);

  // 确认删除文档
  const confirmDeleteDocument = useCallback(async () => {
    if (!documentToDelete) return;
    
    setIsLoading(true);
    
    try {
      await documentApi.deleteDocument(documentToDelete);
      
      setSnackbarMessage('文档删除成功');
      setSnackbarOpen(true);
      
      // 刷新当前页面的文档列表
      loadDocuments();
    } catch (err) {
      let errorMessage = '删除文档失败';
      
      if (err instanceof Error) {
        if (err.message.includes('Network Error') || err.message.includes('fetch')) {
          errorMessage = '网络连接失败，删除操作未完成';
        } else if (err.message.includes('timeout')) {
          errorMessage = '请求超时，请重试删除操作';
        } else if (err.message.includes('404')) {
          errorMessage = '文档不存在或已被删除';
        } else if (err.message.includes('403')) {
          errorMessage = '没有权限删除此文档';
        } else if (err.message.includes('500')) {
          errorMessage = '服务器错误，请稍后重试';
        } else {
          errorMessage = err.message;
        }
      }
      
      setSnackbarMessage(errorMessage);
      setSnackbarOpen(true);
      console.error('Failed to delete document:', err);
    } finally {
      setIsLoading(false);
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
    }
  }, [documentToDelete, loadDocuments]);

  const navigate = useNavigate();

  // 处理查看文档
  const handleViewDocument = useCallback((document: Document) => {
    console.log('View document:', document);
    // 导航到文档预览页面
    navigate(`/documents/${document.id}/preview`);
  }, [navigate]);

  // 处理加载更多（暂时不需要分页）
  const handleLoadMore = useCallback(async (_startIndex: number, _stopIndex: number) => {
    // 暂时不实现分页加载
    return Promise.resolve();
  }, []);

  // 处理分页变更
  const handlePageChange = useCallback((_event: React.ChangeEvent<unknown>, page: number) => {
    setCurrentPage(page);
    loadDocuments(page, pageSize);
  }, [loadDocuments, pageSize]);

  // 处理每页条数变更
  const handlePageSizeChange = useCallback((event: SelectChangeEvent<number>) => {
    const newPageSize = event.target.value as number;
    setPageSize(newPageSize);
    setCurrentPage(1); // 重置到第一页
    loadDocuments(1, newPageSize);
  }, [loadDocuments]);

  // 处理标签页切换
  const handleTabChange = useCallback((_event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  }, []);

  return (
    <Container 
      maxWidth="lg" 
      sx={{ 
        py: 4,
        background: 'linear-gradient(135deg, rgba(246, 249, 252, 0.8) 0%, rgba(238, 243, 248, 0.8) 100%)',
        minHeight: 'calc(100vh - 64px)',
        position: 'relative',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: `
            radial-gradient(circle at 20% 30%, rgba(103, 126, 234, 0.03) 0%, transparent 50%),
            radial-gradient(circle at 80% 70%, rgba(217, 70, 239, 0.03) 0%, transparent 50%)
          `,
          pointerEvents: 'none',
          zIndex: 0,
        },
      }}>
      <AnimatedBox animation="fadeInUp" duration="0.6s">
        <Box sx={{ position: 'relative', zIndex: 1 }}>
          <Typography variant="h4" component="h1" gutterBottom sx={{
            fontWeight: 700,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            backgroundClip: 'text',
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: 'transparent',
            textShadow: 'none',
            mb: 2,
          }}>
          文件管理
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ 
          mb: 4,
          fontSize: '1.1rem',
          lineHeight: 1.6,
          opacity: 0.8,
        }}>
          管理您的医疗文档，支持上传、查看和删除操作
        </Typography>
        </Box>
      </AnimatedBox>

      <AnimatedBox animation="fadeInUp" delay="0.2s" duration="0.6s">
        <Paper 
          elevation={3} 
          sx={{ 
            p: 4, 
            mb: 3,
            background: 'rgba(255, 255, 255, 0.95)',
            backdropFilter: 'blur(20px)',
            borderRadius: 4,
            border: '1px solid rgba(255, 255, 255, 0.2)',
            position: 'relative',
            overflow: 'hidden',
            boxShadow: '0 8px 32px rgba(0, 0, 0, 0.1)',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&::before': {
              content: '""',
              position: 'absolute',
              top: 0,
              left: 0,
              right: 0,
              height: 3,
              background: 'linear-gradient(90deg, #667eea, #764ba2, #9c88ff)',
            },
            '&:hover': {
              transform: 'translateY(-4px)',
              boxShadow: '0 12px 40px rgba(0, 0, 0, 0.15)',
            },
          }}>
          <Box sx={{ borderBottom: 1, borderColor: 'rgba(0, 0, 0, 0.08)', mb: 3, pb: 2 }}>
            <Tabs 
              value={currentTab} 
              onChange={handleTabChange} 
              aria-label="文件管理标签页"
              sx={{
                '& .MuiTab-root': {
                  fontSize: '1rem',
                  fontWeight: 600,
                  textTransform: 'none',
                  minWidth: 120,
                  transition: 'all 0.3s ease',
                  '&:hover': {
                    color: 'primary.main',
                    transform: 'translateY(-2px)',
                  },
                  '&.Mui-selected': {
                    color: 'primary.main',
                    fontWeight: 700,
                  },
                },
                '& .MuiTabs-indicator': {
                  height: 3,
                  borderRadius: '3px 3px 0 0',
                  background: 'linear-gradient(90deg, #667eea, #764ba2)',
                },
              }}>
              <Tab 
                label="文档管理" 
                sx={{
                  '&:hover': {
                    background: 'rgba(103, 126, 234, 0.05)',
                    borderRadius: 2,
                  },
                }} 
              />
              <Tab 
                label="智能分块配置" 
                sx={{
                  '&:hover': {
                    background: 'rgba(103, 126, 234, 0.05)',
                    borderRadius: 2,
                  },
                }} 
              />
            </Tabs>
          </Box>
          
          {/* 文档管理标签页 */}
          {currentTab === 0 && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" component="h2">
                  文档列表 (共 {totalDocuments} 条)
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
                  <FormControl size="small" sx={{ minWidth: 120 }}>
                    <InputLabel>每页条数</InputLabel>
                    <Select
                      value={pageSize}
                      label="每页条数"
                      onChange={handlePageSizeChange}
                    >
                      <MenuItem value={5}>5条</MenuItem>
                      <MenuItem value={10}>10条</MenuItem>
                      <MenuItem value={20}>20条</MenuItem>
                      <MenuItem value={50}>50条</MenuItem>
                    </Select>
                  </FormControl>
                  <HoverAnimatedBox hoverAnimation="scale">
                    <AccessibleButton
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      onClick={() => loadDocuments()}
                      disabled={isLoading}
                      size="small"
                      sx={{
                        borderRadius: 3,
                        borderWidth: 2,
                        borderColor: 'rgba(103, 126, 234, 0.3)',
                        color: 'primary.main',
                        background: 'rgba(255, 255, 255, 0.8)',
                        backdropFilter: 'blur(10px)',
                        fontWeight: 600,
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        '&:hover': {
                          borderColor: 'primary.main',
                          background: 'rgba(103, 126, 234, 0.1)',
                          transform: 'translateY(-2px)',
                          boxShadow: '0 4px 15px rgba(103, 126, 234, 0.2)',
                        },
                      }}
                    >
                      刷新
                    </AccessibleButton>
                  </HoverAnimatedBox>
                  <HoverAnimatedBox hoverAnimation="scale">
                    <AccessibleButton
                      variant="contained"
                      startIcon={<AddIcon />}
                      onClick={() => setUploadDialogOpen(true)}
                      size="small"
                      sx={{
                        borderRadius: 3,
                        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
                        boxShadow: '0 4px 15px rgba(103, 126, 234, 0.3)',
                        fontWeight: 600,
                        fontSize: '0.9rem',
                        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                        '&:hover': {
                          background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
                          transform: 'translateY(-2px)',
                          boxShadow: '0 6px 20px rgba(103, 126, 234, 0.4)',
                        },
                      }}
                    >
                      上传文档
                    </AccessibleButton>
                  </HoverAnimatedBox>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 2 }} />
              
              {error && (
                <AnimatedBox animation="fadeInUp">
                  <Alert 
                    severity="error" 
                    sx={{ mb: 2 }}
                    action={
                      <Button 
                        color="inherit" 
                        size="small" 
                        onClick={() => loadDocuments()}
                        disabled={isLoading}
                      >
                        重试
                      </Button>
                    }
                  >
                    {error}
                  </Alert>
                </AnimatedBox>
              )}
              
              <Box sx={{ height: 500 }}>
                <LazyDocumentList
                  documents={documents}
                  onLoadMore={handleLoadMore}
                  onDelete={handleDeleteDocument}
                  onView={handleViewDocument}
                  hasNextPage={false}
                  isLoading={isLoading}
                  height={500}
                />
              </Box>
              
              {/* 分页控件 */}
              {totalPages > 1 && (
                <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
                  <Pagination
                    count={totalPages}
                    page={currentPage}
                    onChange={handlePageChange}
                    color="primary"
                    size="large"
                    showFirstButton
                    showLastButton
                  />
                </Box>
              )}
            </>
          )}
          
          {/* 智能分块配置标签页 */}
          {currentTab === 1 && (
            <ChunkingConfig />
          )}
        </Paper>
      </AnimatedBox>

      {/* 上传对话框 */}
      <DocumentUploader
        open={uploadDialogOpen}
        onClose={() => setUploadDialogOpen(false)}
        onUploadSuccess={handleUploadSuccess}
        dialogMode={true}
      />

      {/* 删除确认对话框 */}
      <Dialog
        open={deleteDialogOpen}
        onClose={() => setDeleteDialogOpen(false)}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle>确认删除</DialogTitle>
        <DialogContent>
          <Typography>
            确定要删除这个文档吗？此操作无法撤销。
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button 
            onClick={() => setDeleteDialogOpen(false)} 
            disabled={isLoading}
          >
            取消
          </Button>
          <Button 
             onClick={confirmDeleteDocument} 
             color="error" 
             variant="contained"
             disabled={isLoading}
             startIcon={isLoading ? <CircularProgress size={16} color="inherit" /> : undefined}
           >
             {isLoading ? '删除中...' : '删除'}
           </Button>
        </DialogActions>
      </Dialog>

      {/* 现代化浮动操作按钮 */}
      <HoverAnimatedBox hoverAnimation="scale">
        <Fab
          color="primary"
          aria-label="上传文档"
          sx={{
            position: 'fixed',
            bottom: 32,
            right: 32,
            zIndex: 1000,
            width: 64,
            height: 64,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            boxShadow: '0 8px 25px rgba(103, 126, 234, 0.4)',
            border: '2px solid rgba(255, 255, 255, 0.2)',
            backdropFilter: 'blur(10px)',
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            '&:hover': {
              background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
              transform: 'scale(1.15)',
              boxShadow: '0 12px 35px rgba(103, 126, 234, 0.5)',
              borderColor: 'rgba(255, 255, 255, 0.4)',
            },
            '&:active': {
              transform: 'scale(1.1)',
            },
          }}
          onClick={() => setUploadDialogOpen(true)}
        >
          <AddIcon sx={{ fontSize: 28 }} />
        </Fab>
      </HoverAnimatedBox>

      {/* 消息提示 */}
      <Snackbar
        open={snackbarOpen}
        autoHideDuration={4000}
        onClose={() => setSnackbarOpen(false)}
        message={snackbarMessage}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
      />
    </Container>
  );
};

export default FileManagementPage;