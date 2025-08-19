import React from 'react';
import { Box, keyframes, styled } from '@mui/material';
import { SxProps, Theme } from '@mui/material/styles';

// 脉冲动画
const pulseAnimation = keyframes`
  0% {
    transform: scale(1);
    opacity: 1;
  }
  50% {
    transform: scale(1.05);
    opacity: 0.8;
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
`;

// 弹跳动画
const bounceAnimation = keyframes`
  0%, 20%, 53%, 80%, 100% {
    transform: translate3d(0, 0, 0);
  }
  40%, 43% {
    transform: translate3d(0, -8px, 0);
  }
  70% {
    transform: translate3d(0, -4px, 0);
  }
  90% {
    transform: translate3d(0, -2px, 0);
  }
`;

// 摇摆动画
const shakeAnimation = keyframes`
  0%, 100% {
    transform: translateX(0);
  }
  10%, 30%, 50%, 70%, 90% {
    transform: translateX(-2px);
  }
  20%, 40%, 60%, 80% {
    transform: translateX(2px);
  }
`;

// 渐变加载动画
const shimmerAnimation = keyframes`
  0% {
    background-position: -200px 0;
  }
  100% {
    background-position: calc(200px + 100%) 0;
  }
`;

// 旋转动画
const spinAnimation = keyframes`
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
`;

// 淡入上升动画
const fadeInUpAnimation = keyframes`
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
`;

// 淡入左移动画
const fadeInLeftAnimation = keyframes`
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
`;

// 缩放进入动画
const scaleInAnimation = keyframes`
  from {
    opacity: 0;
    transform: scale(0.8);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
`;

// 打字机效果
const typewriterAnimation = keyframes`
  from {
    width: 0;
  }
  to {
    width: 100%;
  }
`;

// 呼吸灯效果
const breatheAnimation = keyframes`
  0%, 100% {
    opacity: 0.4;
  }
  50% {
    opacity: 1;
  }
`;

interface AnimatedBoxProps {
  children: React.ReactNode;
  animation?: 'pulse' | 'bounce' | 'shake' | 'shimmer' | 'spin' | 'fadeInUp' | 'fadeInLeft' | 'scaleIn' | 'typewriter' | 'breathe';
  duration?: string;
  delay?: string;
  iterationCount?: string | number;
  sx?: SxProps<Theme>;
  [key: string]: any; // Allow any additional props
}

// 动画容器组件
export const AnimatedBox = React.forwardRef<HTMLDivElement, AnimatedBoxProps>((
  {
    children,
    animation = 'fadeInUp',
    duration = '0.3s',
    delay = '0s',
    iterationCount = 1,
    sx = {},
    ...otherProps
  },
  ref
) => {
  const getAnimation = () => {
    switch (animation) {
      case 'pulse':
        return pulseAnimation;
      case 'bounce':
        return bounceAnimation;
      case 'shake':
        return shakeAnimation;
      case 'shimmer':
        return shimmerAnimation;
      case 'spin':
        return spinAnimation;
      case 'fadeInUp':
        return fadeInUpAnimation;
      case 'fadeInLeft':
        return fadeInLeftAnimation;
      case 'scaleIn':
        return scaleInAnimation;
      case 'typewriter':
        return typewriterAnimation;
      case 'breathe':
        return breatheAnimation;
      default:
        return fadeInUpAnimation;
    }
  };

  return (
    <Box
      ref={ref}
      sx={{
        animation: `${getAnimation()} ${duration} ${delay} ${iterationCount} ease-in-out`,
        ...sx,
      }}
      {...otherProps}
    >
      {children}
    </Box>
  );
});

AnimatedBox.displayName = 'AnimatedBox';

// 悬停动画组件
interface HoverAnimatedBoxProps {
  children: React.ReactNode;
  hoverAnimation?: 'lift' | 'scale' | 'rotate' | 'glow' | 'tilt';
  sx?: SxProps<Theme>;
  [key: string]: any; // Allow any additional props
}

export const HoverAnimatedBox = React.forwardRef<HTMLDivElement, HoverAnimatedBoxProps>((
  {
    children,
    hoverAnimation = 'lift',
    sx = {},
    ...otherProps
  },
  ref
) => {
  const getHoverStyles = () => {
    switch (hoverAnimation) {
      case 'lift':
        return {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'translateY(-4px)',
            boxShadow: '0 10px 25px rgba(0, 0, 0, 0.15)',
          },
        };
      case 'scale':
        return {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'scale(1.05)',
          },
        };
      case 'rotate':
        return {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'rotate(2deg)',
          },
        };
      case 'glow':
        return {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            boxShadow: '0 0 20px rgba(103, 126, 234, 0.4)',
          },
        };
      case 'tilt':
        return {
          transition: 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
          '&:hover': {
            transform: 'perspective(1000px) rotateX(5deg) rotateY(5deg)',
          },
        };
      default:
        return {};
    }
  };

  return (
    <Box
      ref={ref}
      sx={{
        ...getHoverStyles(),
        ...sx,
      }}
      {...otherProps}
    >
      {children}
    </Box>
  );
});

HoverAnimatedBox.displayName = 'HoverAnimatedBox';

// 加载骨架屏组件
const SkeletonBox = styled(Box)(({ theme }) => ({
  background: `linear-gradient(90deg, ${theme.palette.grey[300]} 25%, ${theme.palette.grey[200]} 50%, ${theme.palette.grey[300]} 75%)`,
  backgroundSize: '200px 100%',
  animation: `${shimmerAnimation} 1.5s infinite`,
  borderRadius: theme.shape.borderRadius,
}));

interface SkeletonProps {
  width?: string | number;
  height?: string | number;
  variant?: 'text' | 'rectangular' | 'circular';
  sx?: SxProps<Theme>;
}

export const Skeleton: React.FC<SkeletonProps> = ({
  width = '100%',
  height = 20,
  variant = 'text',
  sx = {},
}) => {
  const getVariantStyles = () => {
    switch (variant) {
      case 'text':
        return {
          height: height,
          borderRadius: 4,
        };
      case 'rectangular':
        return {
          width: width,
          height: height,
          borderRadius: 8,
        };
      case 'circular':
        return {
          width: width,
          height: width,
          borderRadius: '50%',
        };
      default:
        return {};
    }
  };

  return (
    <SkeletonBox
      sx={{
        width: variant === 'text' ? width : undefined,
        ...getVariantStyles(),
        ...sx,
      }}
    />
  );
};

// 打字机效果组件
interface TypewriterProps {
  text: string;
  speed?: number;
  delay?: number;
  onComplete?: () => void;
  sx?: SxProps<Theme>;
}

export const Typewriter: React.FC<TypewriterProps> = ({
  text,
  speed = 50,
  delay = 0,
  onComplete,
  sx = {},
}) => {
  const [displayText, setDisplayText] = React.useState('');
  const [currentIndex, setCurrentIndex] = React.useState(0);

  React.useEffect(() => {
    if (currentIndex < text.length) {
      const timeout = setTimeout(() => {
        setDisplayText(prev => prev + text[currentIndex]);
        setCurrentIndex(prev => prev + 1);
      }, currentIndex === 0 ? delay : speed);

      return () => clearTimeout(timeout);
    } else if (onComplete) {
      onComplete();
    }
  }, [currentIndex, text, speed, delay, onComplete]);

  return (
    <Box component="span" sx={sx}>
      {displayText}
      <Box
        component="span"
        sx={{
          display: 'inline-block',
          width: '2px',
          height: '1em',
          bgcolor: 'text.primary',
          ml: 0.5,
          animation: `${breatheAnimation} 1s infinite`,
        }}
      />
    </Box>
  );
};

// 粒子效果组件
interface ParticleProps {
  count?: number;
  color?: string;
  size?: number;
}

export const ParticleEffect: React.FC<ParticleProps> = ({
  count = 20,
  color = '#667eea',
  size = 4,
}) => {
  const particles = Array.from({ length: count }, (_, i) => ({
    id: i,
    x: Math.random() * 100,
    y: Math.random() * 100,
    delay: Math.random() * 2,
    duration: 2 + Math.random() * 3,
  }));

  const floatAnimation = keyframes`
    0%, 100% {
      transform: translateY(0px) rotate(0deg);
      opacity: 0;
    }
    10% {
      opacity: 1;
    }
    90% {
      opacity: 1;
    }
    100% {
      transform: translateY(-100px) rotate(360deg);
      opacity: 0;
    }
  `;

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {particles.map((particle) => (
        <Box
          key={particle.id}
          sx={{
            position: 'absolute',
            left: `${particle.x}%`,
            top: `${particle.y}%`,
            width: size,
            height: size,
            bgcolor: color,
            borderRadius: '50%',
            animation: `${floatAnimation} ${particle.duration}s ${particle.delay}s infinite`,
          }}
        />
      ))}
    </Box>
  );
};

// 波纹效果组件
interface RippleProps {
  trigger: boolean;
  color?: string;
  duration?: number;
}

export const Ripple: React.FC<RippleProps> = ({
  trigger,
  color = 'rgba(103, 126, 234, 0.3)',
  duration = 600,
}) => {
  const [ripples, setRipples] = React.useState<Array<{ id: number; x: number; y: number }>>([]);

  const rippleAnimation = keyframes`
    0% {
      transform: scale(0);
      opacity: 1;
    }
    100% {
      transform: scale(4);
      opacity: 0;
    }
  `;

  React.useEffect(() => {
    if (trigger) {
      const newRipple = {
        id: Date.now() + Math.random(),
        x: Math.random() * 100,
        y: Math.random() * 100,
      };
      setRipples(prev => [...prev, newRipple]);

      setTimeout(() => {
        setRipples(prev => prev.filter(ripple => ripple.id !== newRipple.id));
      }, duration);
    }
  }, [trigger, duration]);

  return (
    <Box
      sx={{
        position: 'absolute',
        top: 0,
        left: 0,
        width: '100%',
        height: '100%',
        pointerEvents: 'none',
        overflow: 'hidden',
      }}
    >
      {ripples.map((ripple) => (
        <Box
          key={ripple.id}
          sx={{
            position: 'absolute',
            left: `${ripple.x}%`,
            top: `${ripple.y}%`,
            width: 20,
            height: 20,
            bgcolor: color,
            borderRadius: '50%',
            transform: 'translate(-50%, -50%)',
            animation: `${rippleAnimation} ${duration}ms ease-out`,
          }}
        />
      ))}
    </Box>
  );
};

export default {
  AnimatedBox,
  HoverAnimatedBox,
  Skeleton,
  Typewriter,
  ParticleEffect,
  Ripple,
};