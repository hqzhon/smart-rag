import React, { useState, useEffect, useCallback } from 'react';
import {
  Container,
  Typography,
  Box,
  Paper,
  Divider,
  Alert,
  Snackbar,
  Fab,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Tabs,
  Tab,
} from '@mui/material';
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

  // 加载文档列表
  const loadDocuments = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    
    try {
      const response = await documentApi.getDocuments();
      setDocuments(response || []);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '加载文档列表失败';
      setError(errorMessage);
      console.error('Failed to load documents:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

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
    
    try {
      await documentApi.deleteDocument(documentToDelete);
      
      // 从列表中移除已删除的文档
      setDocuments(prev => prev.filter(doc => doc.id !== documentToDelete));
      
      setSnackbarMessage('文档删除成功');
      setSnackbarOpen(true);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : '删除文档失败';
      setSnackbarMessage(errorMessage);
      setSnackbarOpen(true);
      console.error('Failed to delete document:', err);
    } finally {
      setDeleteDialogOpen(false);
      setDocumentToDelete(null);
    }
  }, [documentToDelete]);

  // 处理查看文档
  const handleViewDocument = useCallback((document: Document) => {
    console.log('View document:', document);
    // TODO: 实现文档预览功能
    setSnackbarMessage('文档预览功能开发中');
    setSnackbarOpen(true);
  }, []);

  // 处理加载更多（暂时不需要分页）
  const handleLoadMore = useCallback(async (startIndex: number, stopIndex: number) => {
    // 暂时不实现分页加载
    return Promise.resolve();
  }, []);

  // 处理标签页切换
  const handleTabChange = useCallback((event: React.SyntheticEvent, newValue: number) => {
    setCurrentTab(newValue);
  }, []);

  return (
    <Container maxWidth="lg" sx={{ py: 4 }}>
      <AnimatedBox animation="fadeInUp" duration="0.6s">
        <Typography variant="h4" component="h1" gutterBottom>
          文件管理
        </Typography>
        <Typography variant="body1" color="text.secondary" sx={{ mb: 4 }}>
          管理您的医疗文档，支持上传、查看和删除操作
        </Typography>
      </AnimatedBox>

      <AnimatedBox animation="fadeInUp" delay="0.2s" duration="0.6s">
        <Paper elevation={2} sx={{ p: 3, mb: 3 }}>
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs value={currentTab} onChange={handleTabChange} aria-label="文件管理标签页">
              <Tab label="文档管理" />
              <Tab label="智能分块配置" />
            </Tabs>
          </Box>
          
          {/* 文档管理标签页 */}
          {currentTab === 0 && (
            <>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6" component="h2">
                  文档列表 ({documents.length})
                </Typography>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <HoverAnimatedBox hoverAnimation="scale">
                    <AccessibleButton
                      variant="outlined"
                      startIcon={<RefreshIcon />}
                      onClick={loadDocuments}
                      disabled={isLoading}
                      size="small"
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
                    >
                      上传文档
                    </AccessibleButton>
                  </HoverAnimatedBox>
                </Box>
              </Box>
              
              <Divider sx={{ mb: 2 }} />
              
              {error && (
                <AnimatedBox animation="fadeInUp">
                  <Alert severity="error" sx={{ mb: 2 }}>
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
          <Button onClick={() => setDeleteDialogOpen(false)}>取消</Button>
          <Button onClick={confirmDeleteDocument} color="error" variant="contained">
            删除
          </Button>
        </DialogActions>
      </Dialog>

      {/* 浮动操作按钮 */}
      <HoverAnimatedBox hoverAnimation="scale">
        <Fab
          color="primary"
          aria-label="上传文档"
          sx={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 1000,
          }}
          onClick={() => setUploadDialogOpen(true)}
        >
          <AddIcon />
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