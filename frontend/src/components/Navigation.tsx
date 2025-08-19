import React from 'react';
import {
  AppBar,
  Toolbar,
  Typography,
  Button,
  Box,
  Container,
} from '@mui/material';
import {
  Chat as ChatIcon,
  Folder as FolderIcon,
  SmartToy as BotIcon,
} from '@mui/icons-material';
import { useNavigate, useLocation } from 'react-router-dom';

const Navigation: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();

  const isActive = (path: string) => {
    if (path === '/chat') {
      return location.pathname.startsWith('/chat');
    }
    return location.pathname === path;
  };

  return (
    <AppBar 
      position="sticky" 
      elevation={0}
      sx={{
        background: 'linear-gradient(135deg, rgba(14, 165, 233, 0.9) 0%, rgba(217, 70, 239, 0.9) 100%)',
        backdropFilter: 'blur(10px)',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Container maxWidth="lg">
        <Toolbar sx={{ px: 0 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <BotIcon sx={{ mr: 1, fontSize: 28 }} />
            <Typography
              variant="h6"
              component="div"
              sx={{
                fontWeight: 700,
                color: 'white',
              }}
            >
              智能医疗助手
            </Typography>
          </Box>
          
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              color="inherit"
              startIcon={<FolderIcon />}
              onClick={() => navigate('/files')}
              sx={{
                color: 'white',
                fontWeight: isActive('/files') ? 700 : 400,
                backgroundColor: isActive('/files') ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                borderRadius: 2,
                px: 2,
              }}
            >
              文件管理
            </Button>
            
            <Button
              color="inherit"
              startIcon={<ChatIcon />}
              onClick={() => navigate('/chat')}
              sx={{
                color: 'white',
                fontWeight: isActive('/chat') ? 700 : 400,
                backgroundColor: isActive('/chat') ? 'rgba(255, 255, 255, 0.2)' : 'transparent',
                '&:hover': {
                  backgroundColor: 'rgba(255, 255, 255, 0.1)',
                },
                borderRadius: 2,
                px: 2,
              }}
            >
              智能问答
            </Button>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navigation;