import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Switch,
  TextField,
  Button,
  Grid,
  Card,
  CardContent,
  Divider,
  Alert,
  Snackbar,
  FormControlLabel,
  CircularProgress,
} from '@mui/material';
import {
  Settings as SettingsIcon,
  Analytics as AnalyticsIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { documentApi } from '@/services/api';

interface ChunkingStats {
  total_chunks: number;
  avg_chunk_size: number;
  semantic_merges: number;
  cache_hits: number;
  cache_misses: number;
  processing_time: number;
}

interface ChunkingConfig {
  chunk_size: number;
  chunk_overlap: number;
  enable_semantic: boolean;
}

const ChunkingConfigComponent: React.FC = () => {
  const [config, setConfig] = useState<ChunkingConfig>({
    chunk_size: 1000,
    chunk_overlap: 200,
    enable_semantic: true,
  });
  
  const [stats, setStats] = useState<ChunkingStats | null>(null);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // 加载统计信息
  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const response = await documentApi.getChunkingStats();
      setStats(response.data || null);
    } catch (err) {
      console.error('Failed to load chunking stats:', err);
      setError('加载统计信息失败');
    } finally {
      setStatsLoading(false);
    }
  };

  // 保存配置
  const saveConfig = async () => {
    setLoading(true);
    setError(null);
    
    try {
      await documentApi.updateChunkingConfig(config);
      setSuccess('配置保存成功');
    } catch (err) {
      console.error('Failed to save config:', err);
      setError('保存配置失败');
    } finally {
      setLoading(false);
    }
  };

  // 重置统计
  const resetStats = async () => {
    setStatsLoading(true);
    try {
      await documentApi.resetChunkingStats();
      setSuccess('统计信息已重置');
      await loadStats();
    } catch (err) {
      console.error('Failed to reset stats:', err);
      setError('重置统计失败');
    } finally {
      setStatsLoading(false);
    }
  };

  // 页面加载时获取统计信息
  useEffect(() => {
    loadStats();
  }, []);

  // 处理配置变更
  const handleConfigChange = (field: keyof ChunkingConfig, value: any) => {
    setConfig(prev => ({
      ...prev,
      [field]: value,
    }));
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h5" gutterBottom sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <SettingsIcon />
        智能分块配置
      </Typography>

        <Grid container spacing={3}>
        <Grid xs={12} md={6}>
          <Card>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  分块配置
                </Typography>
                <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                  <TextField
                    label="块大小"
                    type="number"
                    value={config.chunk_size}
                    onChange={(e) => setConfig({ ...config, chunk_size: parseInt(e.target.value) || 1000 })}
                    helperText="每个文本块的最大字符数"
                    fullWidth
                  />
                  <TextField
                    label="块重叠"
                    type="number"
                    value={config.chunk_overlap}
                    onChange={(e) => setConfig({ ...config, chunk_overlap: parseInt(e.target.value) || 200 })}
                    helperText="相邻文本块之间的重叠字符数"
                    fullWidth
                  />
                  <FormControlLabel
                    control={
                      <Switch
                        checked={config.enable_semantic}
                        onChange={(e) => setConfig({ ...config, enable_semantic: e.target.checked })}
                      />
                    }
                    label="启用语义分块"
                  />
                  <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
                    <Button
                      variant="contained"
                      onClick={saveConfig}
                      disabled={loading}
                    >
                      保存配置
                    </Button>
                    <Button
                      variant="outlined"
                      onClick={resetStats}
                      disabled={loading}
                    >
                      重置统计
                    </Button>
                  </Box>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        
        <Grid xs={12} md={6}>
          <Card>
              <CardContent>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h6" sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <AnalyticsIcon />
                    分块统计
                  </Typography>
                  <Box>
                    <Button
                      size="small"
                      startIcon={<RefreshIcon />}
                      onClick={loadStats}
                      disabled={statsLoading}
                      sx={{ mr: 1 }}
                    >
                      刷新
                    </Button>
                    <Button
                      size="small"
                      variant="outlined"
                      onClick={resetStats}
                      disabled={statsLoading}
                    >
                      重置
                    </Button>
                  </Box>
                </Box>

                {statsLoading ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', p: 3 }}>
                    <CircularProgress />
                  </Box>
                ) : stats ? (
                  <Grid container spacing={2}>
                    <Grid xs={6}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" color="primary">
                            {stats.total_chunks || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            总分块数
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid xs={6}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" color="secondary">
                            {Math.round(stats.avg_chunk_size || 0)}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            平均分块大小
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid xs={6}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" color="success.main">
                            {stats.semantic_merges || 0}
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            语义合并次数
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                    <Grid xs={6}>
                      <Card variant="outlined">
                        <CardContent sx={{ textAlign: 'center' }}>
                          <Typography variant="h4" color="info.main">
                            {((stats.cache_hits || 0) / Math.max((stats.cache_hits || 0) + (stats.cache_misses || 0), 1) * 100).toFixed(1)}%
                          </Typography>
                          <Typography variant="body2" color="text.secondary">
                            缓存命中率
                          </Typography>
                        </CardContent>
                      </Card>
                    </Grid>
                  </Grid>
                ) : (
                  <Alert severity="info">
                    暂无统计数据
                  </Alert>
                )}
              </CardContent>
            </Card>
          </Grid>
      </Grid>

      {/* 成功/错误提示 */}
      <Snackbar
        open={!!success}
        autoHideDuration={3000}
        onClose={() => setSuccess(null)}
      >
        <Alert severity="success" onClose={() => setSuccess(null)}>
          {success}
        </Alert>
      </Snackbar>

      <Snackbar
        open={!!error}
        autoHideDuration={5000}
        onClose={() => setError(null)}
      >
        <Alert severity="error" onClose={() => setError(null)}>
          {error}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default ChunkingConfigComponent;