import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Typography,
  Paper,
  Box,
  Button,
  Alert,
  CircularProgress,
  IconButton,
  Divider,
  List,
  ListItem,
  ListItemText,
  ListItemButton,
  Chip,
  Pagination,
} from '@mui/material';
import {
  ArrowBack as ArrowBackIcon,
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  Refresh as RefreshIcon,
} from '@mui/icons-material';
import { Document, Page, pdfjs } from 'react-pdf';

// Configure PDF.js worker
pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

interface DocumentChunk {
  chunk_id: number;
  chunk_index: number;
  content: string;
  chunk_type: string;
  page_number?: number | null;
  metadata: Record<string, any>;
}

interface ChunksResponse {
  status: string;
  document_id: string;
  total_chunks: number;
  page: number;
  limit: number;
  total_pages: number;
  chunks: DocumentChunk[];
  message?: string;
}

const DocumentPreviewPage: React.FC = () => {
  const { documentId } = useParams<{ documentId: string }>();
  const navigate = useNavigate();
  
  // PDF相关状态
  const [numPages, setNumPages] = useState<number>(0);
  const [currentPage, setCurrentPage] = useState<number>(1);
  const [scale, setScale] = useState<number>(1.0);
  const [pdfLoading, setPdfLoading] = useState<boolean>(true);
  const [pdfError, setPdfError] = useState<string | null>(null);
  const [pdfUrl, setPdfUrl] = useState<string>('');
  
  // 分块相关状态
  const [chunks, setChunks] = useState<DocumentChunk[]>([]);
  const [chunksLoading, setChunksLoading] = useState<boolean>(true);
  const [chunksError, setChunksError] = useState<string | null>(null);
  const [selectedChunk, setSelectedChunk] = useState<DocumentChunk | null>(null);
  const [chunksPage, setChunksPage] = useState<number>(1);
  const [totalChunks, setTotalChunks] = useState<number>(0);
  const [totalChunksPages, setTotalChunksPages] = useState<number>(0);
  
  // 文档信息
  const [documentInfo, setDocumentInfo] = useState<any>(null);

  // 设置PDF URL
  useEffect(() => {
    if (documentId) {
      setPdfUrl(`/api/v1/documents/${documentId}/raw`);
    } else {
      setPdfUrl('');
    }
  }, [documentId]);

  // 页面加载时获取数据
  useEffect(() => {
    if (!documentId) return;
    
    loadDocumentInfo();
    loadChunks();
  }, [documentId]);

  // 加载文档信息
    const loadDocumentInfo = async () => {
      try {
        const response = await fetch(`/api/v1/documents/${documentId}`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        setDocumentInfo(data);
      } catch (error) {
        console.error('Failed to load document info:', error);
      }
    };
    
    // 加载分块数据
    const loadChunks = async () => {
      setChunksLoading(true);
      setChunksError(null);
      
      try {
        const response = await fetch(`/api/v1/documents/${documentId}/chunks?page=1&limit=20`);
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data: ChunksResponse = await response.json();
        
        setChunks(data.chunks || []);
        setTotalChunks(data.total_chunks || 0);
        setTotalChunksPages(data.total_pages || 0);
        setChunksPage(data.page || 1);
        
        if (data.message) {
          setChunksError(data.message);
        }
      } catch (error) {
        console.error('Failed to load chunks:', error);
        setChunksError('加载分块信息失败');
      } finally {
        setChunksLoading(false);
      }
    };

  // PDF加载成功回调
  const onDocumentLoadSuccess = useCallback(({ numPages }: { numPages: number }) => {
    setNumPages(numPages);
    setPdfLoading(false);
    setPdfError(null);
  }, []);

  // PDF加载失败回调
  const onDocumentLoadError = useCallback((error: Error) => {
    console.error('PDF load error:', error);
    setPdfError('PDF文件加载失败');
    setPdfLoading(false);
  }, []);

  // PDF开始加载回调
  const onDocumentLoadStart = useCallback(() => {
    console.log('PDF loading started');
    setPdfLoading(true);
  }, []);

  // 缩放控制
  const handleZoomIn = useCallback(() => {
    setScale(prev => Math.min(prev + 0.2, 3.0));
  }, []);

  const handleZoomOut = useCallback(() => {
    setScale(prev => Math.max(prev - 0.2, 0.5));
  }, []);

  // 分块选择
  const handleChunkSelect = useCallback((chunk: DocumentChunk) => {
    setSelectedChunk(chunk);
    
    // 如果分块有页码信息，跳转到对应页面
    if (chunk.page_number && chunk.page_number > 0) {
      setCurrentPage(chunk.page_number);
    }
    // 注意：当前后端返回的数据中page_number为null，暂时无法实现页面跳转
    // 这是实现联动高亮功能的关键缺失部分
  }, []);

  // 分块分页
  const handleChunksPageChange = useCallback(async (event: React.ChangeEvent<unknown>, page: number) => {
    if (!documentId) return;
    
    setChunksPage(page);
    setChunksLoading(true);
    setChunksError(null);
    
    try {
      const response = await fetch(`/api/v1/documents/${documentId}/chunks?page=${page}&limit=20`);
      
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      
      const data: ChunksResponse = await response.json();
      
      setChunks(data.chunks || []);
      setTotalChunks(data.total_chunks || 0);
      setTotalChunksPages(data.total_pages || 0);
      setChunksPage(data.page || 1);
      
      if (data.message) {
        setChunksError(data.message);
      }
    } catch (error) {
      console.error('Failed to load chunks:', error);
      setChunksError('加载分块信息失败');
    } finally {
      setChunksLoading(false);
    }
  }, [documentId]);

  if (!documentId) {
    return (
      <Container maxWidth="lg" sx={{ py: 4 }}>
        <Alert severity="error">文档ID不存在</Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 2 }}>
      {/* 头部导航 */}
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <IconButton onClick={() => navigate('/files')} color="primary">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" component="h1">
          文档预览
        </Typography>
        {documentInfo && (
          <Chip 
            label={documentInfo.title || '未知文档'} 
            variant="outlined" 
            color="primary"
          />
        )}
      </Box>

      {/* 主要内容区域 */}
      <Box sx={{ display: 'flex', gap: 3, height: 'calc(100vh - 200px)' }}>
        {/* PDF预览区域 */}
        <Paper 
          sx={{ 
            flex: 2, 
            p: 2, 
            display: 'flex', 
            flexDirection: 'column',
            overflow: 'hidden'
          }}
        >
          {/* PDF控制栏 */}
          <Box sx={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'space-between',
            mb: 2,
            pb: 1,
            borderBottom: 1,
            borderColor: 'divider'
          }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <IconButton onClick={handleZoomOut} size="small">
                <ZoomOutIcon />
              </IconButton>
              <Typography variant="body2">
                {Math.round(scale * 100)}%
              </Typography>
              <IconButton onClick={handleZoomIn} size="small">
                <ZoomInIcon />
              </IconButton>
            </Box>
            
            {numPages > 0 && (
              <Typography variant="body2">
                第 {currentPage} 页，共 {numPages} 页
              </Typography>
            )}
            
            <IconButton onClick={() => window.location.reload()} size="small">
              <RefreshIcon />
            </IconButton>
          </Box>

          {/* PDF内容区域 */}
          <Box sx={{ 
            flex: 1, 
            overflow: 'auto', 
            display: 'flex', 
            justifyContent: 'center',
            alignItems: 'flex-start',
            bgcolor: '#f5f5f5',
            p: 2
          }}>
            {pdfError ? (
              <Alert severity="error" sx={{ maxWidth: 400 }}>
                {pdfError}
              </Alert>
            ) : pdfUrl ? (
              <Document
                file={pdfUrl}
                onLoadSuccess={onDocumentLoadSuccess}
                onLoadError={onDocumentLoadError}
                onLoadStart={onDocumentLoadStart}
                loading={(
                  <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2 }}>
                    <CircularProgress />
                    <Typography>加载PDF中...</Typography>
                  </Box>
                )}
                error={(
                  <Alert severity="error">
                    PDF加载失败，请检查文档是否存在
                  </Alert>
                )}
              >
                <Page 
                  pageNumber={currentPage} 
                  scale={scale}
                  renderTextLayer={false}
                  renderAnnotationLayer={false}
                  loading={(
                    <Box sx={{ display: 'flex', justifyContent: 'center', p: 2 }}>
                      <CircularProgress size={24} />
                    </Box>
                  )}
                />
              </Document>
            ) : (
              <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 2, p: 4 }}>
                <CircularProgress />
                <Typography>准备加载PDF...</Typography>
              </Box>
            )}
          </Box>

          {/* PDF分页控制 */}
          {numPages > 1 && (
            <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
              <Pagination
                count={numPages}
                page={currentPage}
                onChange={(event, page) => setCurrentPage(page)}
                color="primary"
                showFirstButton
                showLastButton
              />
            </Box>
          )}
        </Paper>

        {/* 分块信息区域 */}
        <Paper sx={{ flex: 1, p: 2, display: 'flex', flexDirection: 'column' }}>
          <Typography variant="h6" gutterBottom>
            文档分块信息
          </Typography>
          
          <Alert severity="info" sx={{ mb: 2 }}>
            <Typography variant="body2">
              💡 当前版本支持分块内容查看。联动高亮功能需要后端提供页码和坐标信息。
            </Typography>
          </Alert>
          
          {chunksLoading && (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
              <CircularProgress size={24} />
            </Box>
          )}
          
          {chunksError && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              {chunksError}
            </Alert>
          )}
          
          {!chunksLoading && chunks.length > 0 && (
            <>
              <Typography variant="body2" color="text.secondary" gutterBottom>
                共 {totalChunks} 个分块
              </Typography>
              
              <List sx={{ flex: 1, overflow: 'auto' }}>
                {chunks.map((chunk, index) => (
                  <ListItem key={chunk.chunk_id} disablePadding>
                    <ListItemButton
                      selected={selectedChunk?.chunk_id === chunk.chunk_id}
                      onClick={() => handleChunkSelect(chunk)}
                      sx={{ 
                        border: 1, 
                        borderColor: 'divider', 
                        borderRadius: 1, 
                        mb: 1,
                        '&.Mui-selected': {
                          bgcolor: 'primary.light',
                          color: 'primary.contrastText'
                        }
                      }}
                    >
                      <ListItemText
                        primary={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                            <Chip 
                              label={`#${chunk.chunk_index + 1}`} 
                              size="small" 
                              color="primary" 
                              variant="outlined"
                            />
                            <Chip 
                              label={chunk.chunk_type} 
                              size="small" 
                              color="secondary" 
                              variant="outlined"
                            />
                            {chunk.page_number && chunk.page_number > 0 && (
                              <Chip 
                                label={`第${chunk.page_number}页`} 
                                size="small" 
                                variant="outlined"
                              />
                            )}
                          </Box>
                        }
                        secondary={
                          <Typography 
                            variant="body2" 
                            sx={{ 
                              display: '-webkit-box',
                              WebkitLineClamp: 3,
                              WebkitBoxOrient: 'vertical',
                              overflow: 'hidden',
                              textOverflow: 'ellipsis'
                            }}
                          >
                            {chunk.content}
                          </Typography>
                        }
                      />
                    </ListItemButton>
                  </ListItem>
                ))}
              </List>
              
              {totalChunksPages > 1 && (
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'center' }}>
                  <Pagination
                    count={totalChunksPages}
                    page={chunksPage}
                    onChange={handleChunksPageChange}
                    size="small"
                    color="primary"
                  />
                </Box>
              )}
            </>
          )}
          
          {!chunksLoading && chunks.length === 0 && !chunksError && (
            <Alert severity="info">
              暂无分块信息
            </Alert>
          )}
        </Paper>
      </Box>

      {/* 选中分块的详细信息 */}
      {selectedChunk && (
        <Paper sx={{ mt: 3, p: 3 }}>
          <Typography variant="h6" gutterBottom>
            分块详情
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap' }}>
            <Chip label={`分块 #${selectedChunk.chunk_index + 1}`} color="primary" />
            <Chip label={selectedChunk.chunk_type} color="secondary" />
            {selectedChunk.page_number && selectedChunk.page_number > 0 && (
              <Chip label={`第${selectedChunk.page_number}页`} variant="outlined" />
            )}
          </Box>
          
          <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap', lineHeight: 1.6 }}>
            {selectedChunk.content}
          </Typography>
          
          {Object.keys(selectedChunk.metadata).length > 0 && (
            <>
              <Divider sx={{ my: 2 }} />
              <Typography variant="subtitle2" gutterBottom>
                元数据
              </Typography>
              <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                {Object.entries(selectedChunk.metadata).map(([key, value]) => (
                  <Chip 
                    key={key} 
                    label={`${key}: ${value}`} 
                    variant="outlined" 
                    size="small"
                  />
                ))}
              </Box>
            </>
          )}
        </Paper>
      )}
    </Container>
  );
};

export default DocumentPreviewPage;