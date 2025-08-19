import React from 'react';
import { Container, Typography, Box } from '@mui/material';
import DocumentUploader from '../components/DocumentUploader';

const TestUpload: React.FC = () => {
  const handleUploadSuccess = (documents: Array<{ file: File; response: any }>) => {
    console.log('Upload success callback:', documents);
    documents.forEach((doc, index) => {
      console.log(`Document ${index + 1}:`, {
        fileName: doc.file.name,
        fileSize: doc.file.size,
        response: doc.response
      });
      if (doc.response?.filename) {
        console.log(`Backend filename: ${doc.response.filename}`);
      }
    });
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      <Typography variant="h4" component="h1" gutterBottom>
        文档上传测试页面
      </Typography>
      
      <Box sx={{ mt: 4 }}>
        <DocumentUploader 
          onUploadSuccess={handleUploadSuccess}
          dialogMode={false}
        />
      </Box>
      
      <Box sx={{ mt: 4 }}>
        <Typography variant="body2" color="text.secondary">
          请打开浏览器开发者工具的控制台查看调试信息
        </Typography>
      </Box>
    </Container>
  );
};

export default TestUpload;