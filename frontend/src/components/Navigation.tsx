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
  History as HistoryIcon,
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
        background: 'linear-gradient(135deg, rgba(103, 126, 234, 0.95) 0%, rgba(217, 70, 239, 0.95) 50%, rgba(156, 136, 255, 0.95) 100%)',
        backdropFilter: 'blur(20px)',
        borderBottom: '1px solid rgba(255, 255, 255, 0.2)',
        boxShadow: '0 4px 20px rgba(103, 126, 234, 0.2)',
        position: 'relative',
        overflow: 'hidden',
        '&::before': {
          content: '""',
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          background: 'linear-gradient(45deg, rgba(255, 255, 255, 0.1) 0%, transparent 50%, rgba(255, 255, 255, 0.1) 100%)',
          transform: 'translateX(-100%)',
          transition: 'transform 0.8s ease',
        },
        '&:hover::before': {
          transform: 'translateX(100%)',
        },
        transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
      }}
    >
      <Container maxWidth="lg">
        <Toolbar sx={{ px: 0, position: 'relative', zIndex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', flexGrow: 1 }}>
            <Box
              sx={{
                mr: 1,
                p: 1,
                borderRadius: 2,
                background: 'rgba(255, 255, 255, 0.2)',
                backdropFilter: 'blur(10px)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                '&:hover': {
                  transform: 'scale(1.1) rotate(10deg)',
                  background: 'rgba(255, 255, 255, 0.3)',
                },
              }}
            >
              <BotIcon sx={{ fontSize: 28, color: 'white', filter: 'drop-shadow(0 2px 4px rgba(0,0,0,0.2))' }} />
            </Box>
            <Typography
              variant="h6"
              component="div"
              sx={{
                fontWeight: 700,
                color: 'white',
                fontSize: '1.3rem',
                textShadow: '0 2px 4px rgba(0,0,0,0.3)',
                background: 'linear-gradient(45deg, #ffffff 30%, #f0f0f0 90%)',
                backgroundClip: 'text',
                WebkitBackgroundClip: 'text',
                WebkitTextFillColor: 'transparent',
                letterSpacing: '0.5px',
                position: 'relative',
                '&::after': {
                  content: '""',
                  position: 'absolute',
                  bottom: -2,
                  left: 0,
                  width: 0,
                  height: 2,
                  background: 'linear-gradient(90deg, #ffffff, rgba(255,255,255,0.5))',
                  transition: 'width 0.3s ease',
                },
                '&:hover::after': {
                  width: '100%',
                },
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
                fontWeight: isActive('/files') ? 700 : 500,
                fontSize: '0.95rem',
                background: isActive('/files') 
                  ? 'rgba(255, 255, 255, 0.25)' 
                  : 'rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: '-100%',
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                  transition: 'left 0.5s ease',
                },
                '&:hover': {
                  background: 'rgba(255, 255, 255, 0.2)',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
                },
                '&:hover::before': {
                  left: '100%',
                },
                '&:active': {
                  transform: 'translateY(0)',
                },
                borderRadius: 3,
                px: 3,
                py: 1,
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
                fontWeight: isActive('/chat') ? 700 : 500,
                fontSize: '0.95rem',
                background: isActive('/chat') 
                  ? 'rgba(255, 255, 255, 0.25)' 
                  : 'rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: '-100%',
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                  transition: 'left 0.5s ease',
                },
                '&:hover': {
                  background: 'rgba(255, 255, 255, 0.2)',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
                },
                '&:hover::before': {
                  left: '100%',
                },
                '&:active': {
                  transform: 'translateY(0)',
                },
                borderRadius: 3,
                px: 3,
                py: 1,
              }}
            >
              智能问答
            </Button>
            
            <Button
              color="inherit"
              startIcon={<HistoryIcon />}
              onClick={() => navigate('/history')}
              sx={{
                color: 'white',
                fontWeight: isActive('/history') ? 700 : 500,
                fontSize: '0.95rem',
                background: isActive('/history') 
                  ? 'rgba(255, 255, 255, 0.25)' 
                  : 'rgba(255, 255, 255, 0.1)',
                backdropFilter: 'blur(10px)',
                border: '1px solid rgba(255, 255, 255, 0.2)',
                transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
                position: 'relative',
                overflow: 'hidden',
                '&::before': {
                  content: '""',
                  position: 'absolute',
                  top: 0,
                  left: '-100%',
                  width: '100%',
                  height: '100%',
                  background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent)',
                  transition: 'left 0.5s ease',
                },
                '&:hover': {
                  background: 'rgba(255, 255, 255, 0.2)',
                  transform: 'translateY(-2px)',
                  boxShadow: '0 4px 15px rgba(0, 0, 0, 0.2)',
                  borderColor: 'rgba(255, 255, 255, 0.4)',
                },
                '&:hover::before': {
                  left: '100%',
                },
                '&:active': {
                  transform: 'translateY(0)',
                },
                borderRadius: 3,
                px: 3,
                py: 1,
              }}
            >
              历史记录
            </Button>
          </Box>
        </Toolbar>
      </Container>
    </AppBar>
  );
};

export default Navigation;