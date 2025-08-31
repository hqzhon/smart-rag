import { createTheme, ThemeOptions } from '@mui/material/styles';
import { alpha } from '@mui/material/styles';

// Modern color palette inspired by contemporary design systems
const colors = {
  primary: {
    50: '#f0f9ff',
    100: '#e0f2fe',
    200: '#bae6fd',
    300: '#7dd3fc',
    400: '#38bdf8',
    500: '#0ea5e9',
    600: '#0284c7',
    700: '#0369a1',
    800: '#075985',
    900: '#0c4a6e',
  },
  secondary: {
    50: '#fdf4ff',
    100: '#fae8ff',
    200: '#f5d0fe',
    300: '#f0abfc',
    400: '#e879f9',
    500: '#d946ef',
    600: '#c026d3',
    700: '#a21caf',
    800: '#86198f',
    900: '#701a75',
  },
  success: {
    50: '#f0fdf4',
    100: '#dcfce7',
    200: '#bbf7d0',
    300: '#86efac',
    400: '#4ade80',
    500: '#22c55e',
    600: '#16a34a',
    700: '#15803d',
    800: '#166534',
    900: '#14532d',
  },
  warning: {
    50: '#fffbeb',
    100: '#fef3c7',
    200: '#fde68a',
    300: '#fcd34d',
    400: '#fbbf24',
    500: '#f59e0b',
    600: '#d97706',
    700: '#b45309',
    800: '#92400e',
    900: '#78350f',
  },
  error: {
    50: '#fef2f2',
    100: '#fee2e2',
    200: '#fecaca',
    300: '#fca5a5',
    400: '#f87171',
    500: '#ef4444',
    600: '#dc2626',
    700: '#b91c1c',
    800: '#991b1b',
    900: '#7f1d1d',
  },
  neutral: {
    50: '#fafafa',
    100: '#f5f5f5',
    200: '#e5e5e5',
    300: '#d4d4d4',
    400: '#a3a3a3',
    500: '#737373',
    600: '#525252',
    700: '#404040',
    800: '#262626',
    900: '#171717',
  },
};

// Light theme configuration
const lightTheme: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: {
      main: colors.primary[600],
      light: colors.primary[400],
      dark: colors.primary[800],
      contrastText: '#ffffff',
    },
    secondary: {
      main: colors.secondary[600],
      light: colors.secondary[400],
      dark: colors.secondary[800],
      contrastText: '#ffffff',
    },
    success: {
      main: colors.success[600],
      light: colors.success[400],
      dark: colors.success[800],
    },
    warning: {
      main: colors.warning[500],
      light: colors.warning[400],
      dark: colors.warning[700],
    },
    error: {
      main: colors.error[600],
      light: colors.error[400],
      dark: colors.error[800],
    },
    background: {
      default: colors.neutral[50],
      paper: '#ffffff',
    },
    text: {
      primary: colors.neutral[900],
      secondary: colors.neutral[600],
      disabled: colors.neutral[400],
    },
    divider: colors.neutral[200],
    action: {
      hover: alpha(colors.primary[600], 0.04),
      selected: alpha(colors.primary[600], 0.08),
      disabled: colors.neutral[300],
      disabledBackground: colors.neutral[100],
    },
  },
  typography: {
    fontFamily: [
      'Inter',
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
      '"Apple Color Emoji"',
      '"Segoe UI Emoji"',
      '"Segoe UI Symbol"',
    ].join(','),
    h1: {
      fontSize: '2.5rem',
      fontWeight: 700,
      lineHeight: 1.2,
      letterSpacing: '-0.025em',
    },
    h2: {
      fontSize: '2rem',
      fontWeight: 600,
      lineHeight: 1.3,
      letterSpacing: '-0.025em',
    },
    h3: {
      fontSize: '1.5rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h4: {
      fontSize: '1.25rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h5: {
      fontSize: '1.125rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    h6: {
      fontSize: '1rem',
      fontWeight: 600,
      lineHeight: 1.4,
    },
    body1: {
      fontSize: '1rem',
      lineHeight: 1.6,
    },
    body2: {
      fontSize: '0.875rem',
      lineHeight: 1.5,
    },
    caption: {
      fontSize: '0.75rem',
      lineHeight: 1.4,
      color: colors.neutral[600],
    },
  },
  shape: {
    borderRadius: 12,
  },
  shadows: [
    'none',
    '0px 2px 4px rgba(0, 0, 0, 0.02), 0px 1px 2px rgba(0, 0, 0, 0.02)',
    '0px 4px 8px rgba(0, 0, 0, 0.04), 0px 2px 4px rgba(0, 0, 0, 0.02)',
    '0px 8px 16px rgba(0, 0, 0, 0.06), 0px 4px 8px rgba(0, 0, 0, 0.03)',
    '0px 12px 24px rgba(0, 0, 0, 0.08), 0px 6px 12px rgba(0, 0, 0, 0.04)',
    '0px 16px 32px rgba(0, 0, 0, 0.1), 0px 8px 16px rgba(0, 0, 0, 0.05)',
    '0px 20px 40px rgba(0, 0, 0, 0.12), 0px 10px 20px rgba(0, 0, 0, 0.06)',
    '0px 24px 48px rgba(0, 0, 0, 0.14), 0px 12px 24px rgba(0, 0, 0, 0.07)',
    '0px 28px 56px rgba(0, 0, 0, 0.16), 0px 14px 28px rgba(0, 0, 0, 0.08)',
    '0px 32px 64px rgba(0, 0, 0, 0.18), 0px 16px 32px rgba(0, 0, 0, 0.09)',
    '0px 36px 72px rgba(0, 0, 0, 0.2), 0px 18px 36px rgba(0, 0, 0, 0.1)',
    '0px 40px 80px rgba(0, 0, 0, 0.22), 0px 20px 40px rgba(0, 0, 0, 0.11)',
    '0px 44px 88px rgba(0, 0, 0, 0.24), 0px 22px 44px rgba(0, 0, 0, 0.12)',
    '0px 48px 96px rgba(0, 0, 0, 0.26), 0px 24px 48px rgba(0, 0, 0, 0.13)',
    '0px 52px 104px rgba(0, 0, 0, 0.28), 0px 26px 52px rgba(0, 0, 0, 0.14)',
    '0px 56px 112px rgba(0, 0, 0, 0.3), 0px 28px 56px rgba(0, 0, 0, 0.15)',
    '0px 60px 120px rgba(0, 0, 0, 0.32), 0px 30px 60px rgba(0, 0, 0, 0.16)',
    '0px 64px 128px rgba(0, 0, 0, 0.34), 0px 32px 64px rgba(0, 0, 0, 0.17)',
    '0px 68px 136px rgba(0, 0, 0, 0.36), 0px 34px 68px rgba(0, 0, 0, 0.18)',
    '0px 72px 144px rgba(0, 0, 0, 0.38), 0px 36px 72px rgba(0, 0, 0, 0.19)',
    '0px 76px 152px rgba(0, 0, 0, 0.4), 0px 38px 76px rgba(0, 0, 0, 0.2)',
    '0px 80px 160px rgba(0, 0, 0, 0.42), 0px 40px 80px rgba(0, 0, 0, 0.21)',
    '0px 84px 168px rgba(0, 0, 0, 0.44), 0px 42px 84px rgba(0, 0, 0, 0.22)',
    '0px 88px 176px rgba(0, 0, 0, 0.46), 0px 44px 88px rgba(0, 0, 0, 0.23)',
    '0px 92px 184px rgba(0, 0, 0, 0.48), 0px 46px 92px rgba(0, 0, 0, 0.24)',
  ],
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
        },
        html: {
          MozOsxFontSmoothing: 'grayscale',
          WebkitFontSmoothing: 'antialiased',
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100%',
          width: '100%',
        },
        body: {
          display: 'flex',
          flex: '1 1 auto',
          flexDirection: 'column',
          minHeight: '100%',
          width: '100%',
          scrollbarWidth: 'thin',
          scrollbarColor: `${colors.neutral[300]} transparent`,
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: colors.neutral[300],
            borderRadius: '4px',
            '&:hover': {
              background: colors.neutral[400],
            },
          },
        },
        '#root': {
          display: 'flex',
          flex: '1 1 auto',
          flexDirection: 'column',
          height: '100%',
          width: '100%',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          fontWeight: 600,
          borderRadius: 12,
          padding: '12px 24px',
          fontSize: '0.95rem',
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
            background: 'linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent)',
            transition: 'left 0.5s',
          },
          '&:hover': {
            transform: 'translateY(-2px) scale(1.02)',
            boxShadow: '0 8px 25px rgba(103, 126, 234, 0.3)',
          },
          '&:hover::before': {
            left: '100%',
          },
          '&:active': {
            transform: 'translateY(0) scale(1)',
          },
        },
        contained: {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 4px 15px rgba(103, 126, 234, 0.3)',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
            boxShadow: '0 8px 25px rgba(103, 126, 234, 0.4)',
          },
        },
        outlined: {
          borderWidth: '2px',
          borderColor: colors.primary[400],
          background: 'rgba(255, 255, 255, 0.8)',
          backdropFilter: 'blur(10px)',
          '&:hover': {
            borderWidth: '2px',
            background: 'rgba(103, 126, 234, 0.1)',
            borderColor: colors.primary[600],
          },
        },
        text: {
          '&:hover': {
            background: 'rgba(103, 126, 234, 0.08)',
          },
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        },
        elevation0: {
          boxShadow: 'none',
          background: 'transparent',
          backdropFilter: 'none',
          border: 'none',
        },
        elevation1: {
          boxShadow: '0px 2px 8px rgba(0, 0, 0, 0.04), 0px 1px 4px rgba(0, 0, 0, 0.02)',
        },
        elevation2: {
          boxShadow: '0px 4px 12px rgba(0, 0, 0, 0.06), 0px 2px 6px rgba(0, 0, 0, 0.03)',
        },
        elevation3: {
          boxShadow: '0px 8px 20px rgba(0, 0, 0, 0.08), 0px 4px 10px rgba(0, 0, 0, 0.04)',
        },
        elevation4: {
          boxShadow: '0px 12px 28px rgba(0, 0, 0, 0.1), 0px 6px 14px rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 20,
          border: '1px solid rgba(255, 255, 255, 0.2)',
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          position: 'relative',
          overflow: 'hidden',
          '&::before': {
            content: '""',
            position: 'absolute',
            top: 0,
            left: 0,
            right: 0,
            height: '3px',
            background: 'linear-gradient(90deg, #667eea, #764ba2, #9c88ff)',
            opacity: 0,
            transition: 'opacity 0.3s ease',
          },
          '&:hover': {
            transform: 'translateY(-8px) scale(1.02)',
            boxShadow: '0px 20px 40px rgba(0, 0, 0, 0.12), 0px 10px 20px rgba(103, 126, 234, 0.15)',
            borderColor: 'rgba(103, 126, 234, 0.3)',
          },
          '&:hover::before': {
            opacity: 1,
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            borderRadius: 12,
            transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
            background: 'rgba(255, 255, 255, 0.8)',
            backdropFilter: 'blur(10px)',
            '& fieldset': {
              borderColor: 'rgba(0, 0, 0, 0.1)',
              borderWidth: '2px',
            },
            '&:hover': {
              background: 'rgba(255, 255, 255, 0.95)',
              transform: 'translateY(-2px)',
              boxShadow: '0 4px 20px rgba(103, 126, 234, 0.1)',
              '& fieldset': {
                borderColor: colors.primary[400],
              },
            },
            '&.Mui-focused': {
              background: 'rgba(255, 255, 255, 1)',
              transform: 'translateY(-2px)',
              boxShadow: '0 8px 25px rgba(103, 126, 234, 0.2)',
              '& fieldset': {
                borderWidth: '2px',
                borderColor: colors.primary[600],
              },
            },
            '&.Mui-error': {
              '& fieldset': {
                borderColor: colors.error[500],
              },
            },
          },
          '& .MuiInputLabel-root': {
            fontWeight: 500,
            '&.Mui-focused': {
              color: colors.primary[600],
            },
          },
        },
      },
    },
    MuiIconButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'scale(1.1)',
            backgroundColor: alpha(colors.primary[500], 0.1),
          },
        },
      },
    },
    MuiAppBar: {
      styleOverrides: {
        root: {
          backgroundColor: 'transparent',
          backgroundImage: 'none',
          boxShadow: 'none',
          backdropFilter: 'blur(20px)',
          borderBottom: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(0, 0, 0, 0.05)',
        },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          margin: '2px 0',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            backgroundColor: alpha(colors.primary[500], 0.08),
            transform: 'translateX(4px)',
          },
          '&.Mui-selected': {
            backgroundColor: alpha(colors.primary[500], 0.12),
            '&:hover': {
              backgroundColor: alpha(colors.primary[500], 0.16),
            },
          },
        },
      },
    },
    MuiAlert: {
      styleOverrides: {
        root: {
          borderRadius: 12,
          border: '1px solid',
          backdropFilter: 'blur(10px)',
          '&.MuiAlert-standardSuccess': {
            backgroundColor: 'rgba(76, 175, 80, 0.1)',
            borderColor: 'rgba(76, 175, 80, 0.3)',
          },
          '&.MuiAlert-standardError': {
            backgroundColor: 'rgba(244, 67, 54, 0.1)',
            borderColor: 'rgba(244, 67, 54, 0.3)',
          },
          '&.MuiAlert-standardWarning': {
            backgroundColor: 'rgba(255, 152, 0, 0.1)',
            borderColor: 'rgba(255, 152, 0, 0.3)',
          },
          '&.MuiAlert-standardInfo': {
            backgroundColor: 'rgba(33, 150, 243, 0.1)',
            borderColor: 'rgba(33, 150, 243, 0.3)',
          },
        },
      },
    },
    MuiDialog: {
      styleOverrides: {
        paper: {
          borderRadius: 20,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.2)',
        },
      },
    },
    MuiFab: {
      styleOverrides: {
        root: {
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          boxShadow: '0 8px 25px rgba(103, 126, 234, 0.3)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            background: 'linear-gradient(135deg, #5a6fd8 0%, #6a4190 100%)',
            transform: 'scale(1.1)',
            boxShadow: '0 12px 35px rgba(103, 126, 234, 0.4)',
          },
        },
      },
    },
  },
};

// Dark theme configuration with enhanced modern styling
const darkTheme: ThemeOptions = {
  ...lightTheme,
  palette: {
    mode: 'dark',
    primary: {
      main: colors.primary[400],
      light: colors.primary[300],
      dark: colors.primary[600],
      contrastText: colors.neutral[900],
    },
    secondary: {
      main: colors.secondary[400],
      light: colors.secondary[300],
      dark: colors.secondary[600],
      contrastText: colors.neutral[900],
    },
    success: {
      main: colors.success[400],
      light: colors.success[300],
      dark: colors.success[600],
    },
    warning: {
      main: colors.warning[400],
      light: colors.warning[300],
      dark: colors.warning[600],
    },
    error: {
      main: colors.error[400],
      light: colors.error[300],
      dark: colors.error[600],
    },
    background: {
      default: '#0a0e27',
      paper: 'rgba(15, 23, 42, 0.95)',
    },
    text: {
      primary: colors.neutral[100],
      secondary: colors.neutral[400],
      disabled: colors.neutral[600],
    },
    divider: colors.neutral[700],
    action: {
      hover: alpha(colors.primary[400], 0.08),
      selected: alpha(colors.primary[400], 0.12),
      disabled: colors.neutral[600],
      disabledBackground: colors.neutral[800],
    },
  },
  components: {
    ...lightTheme.components,
    MuiCssBaseline: {
      styleOverrides: {
        '*': {
          boxSizing: 'border-box',
        },
        html: {
          MozOsxFontSmoothing: 'grayscale',
          WebkitFontSmoothing: 'antialiased',
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100%',
          width: '100%',
        },
        body: {
          display: 'flex',
          flex: '1 1 auto',
          flexDirection: 'column',
          minHeight: '100%',
          width: '100%',
          background: 'linear-gradient(135deg, #0a0e27 0%, #1a1f3a 100%)',
          backgroundAttachment: 'fixed',
          scrollbarWidth: 'thin',
          scrollbarColor: `${colors.neutral[600]} transparent`,
          '&::-webkit-scrollbar': {
            width: '8px',
            height: '8px',
          },
          '&::-webkit-scrollbar-track': {
            background: 'transparent',
          },
          '&::-webkit-scrollbar-thumb': {
            background: colors.neutral[600],
            borderRadius: '4px',
            '&:hover': {
              background: colors.neutral[500],
            },
          },
          '&::before': {
            content: '""',
            position: 'fixed',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            background: `
              radial-gradient(circle at 20% 50%, rgba(103, 126, 234, 0.1) 0%, transparent 50%),
              radial-gradient(circle at 80% 20%, rgba(217, 70, 239, 0.08) 0%, transparent 50%),
              radial-gradient(circle at 40% 80%, rgba(14, 165, 233, 0.06) 0%, transparent 50%)
            `,
            pointerEvents: 'none',
            zIndex: -1,
          },
        },
        '#root': {
          display: 'flex',
          flex: '1 1 auto',
          flexDirection: 'column',
          height: '100%',
          width: '100%',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          backgroundImage: 'none',
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        },
        elevation0: {
          boxShadow: 'none',
          background: 'transparent',
          backdropFilter: 'none',
          border: 'none',
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          background: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(20px)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          '&:hover': {
            borderColor: 'rgba(103, 126, 234, 0.4)',
            boxShadow: '0px 20px 40px rgba(0, 0, 0, 0.3), 0px 10px 20px rgba(103, 126, 234, 0.2)',
          },
        },
      },
    },
    MuiTextField: {
      styleOverrides: {
        root: {
          '& .MuiOutlinedInput-root': {
            background: 'rgba(255, 255, 255, 0.05)',
            '&:hover': {
              background: 'rgba(255, 255, 255, 0.08)',
            },
            '&.Mui-focused': {
              background: 'rgba(255, 255, 255, 0.1)',
            },
          },
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          backgroundColor: 'rgba(15, 23, 42, 0.95)',
          backdropFilter: 'blur(20px)',
          borderRight: '1px solid rgba(255, 255, 255, 0.1)',
        },
      },
    },
  },
};

export const createAppTheme = (mode: 'light' | 'dark' = 'light') => {
  return createTheme(mode === 'light' ? lightTheme : darkTheme);
};

export { colors };
export default createAppTheme();