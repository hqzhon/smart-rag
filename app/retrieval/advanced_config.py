"""Advanced RAG Configuration for Multi-Path Retrieval

This module provides configuration classes for advanced RAG retrieval,
supporting multi-path recall with dynamic weight adjustment.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class FusionMethod(Enum):
    """Fusion methods for combining retrieval results"""
    WEIGHTED_RRF = "weighted_rrf"  # Weighted Reciprocal Rank Fusion
    SIMPLE_RRF = "simple_rrf"      # Simple RRF without weights
    WEIGHTED_SUM = "weighted_sum"  # Weighted score summation
    MAX_SCORE = "max_score"        # Maximum score selection


class RetrievalPath(Enum):
    """Available retrieval paths"""
    VECTOR = "vector"              # Vector similarity search
    KEYWORDS = "keywords"          # BM25 on keywords field
    SUMMARY = "summary"            # BM25 on summary field
    CONTENT = "content"            # BM25 on full content field


@dataclass
class PathConfig:
    """Configuration for individual retrieval path"""
    enabled: bool = True
    weight: float = 1.0
    top_k: int = 50
    min_score: float = 0.0
    boost_factor: float = 1.0  # Additional boost for this path
    
    def __post_init__(self):
        """Validate configuration values"""
        if self.weight < 0:
            raise ValueError("Weight must be non-negative")
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.min_score < 0:
            raise ValueError("min_score must be non-negative")
        if self.boost_factor <= 0:
            raise ValueError("boost_factor must be positive")


@dataclass
class FusionConfig:
    """Configuration for result fusion"""
    method: FusionMethod = FusionMethod.WEIGHTED_RRF
    rrf_k: int = 60  # RRF parameter
    normalize_scores: bool = True
    final_top_k: int = 20
    score_threshold: float = 0.0
    diversity_penalty: float = 0.0  # Penalty for similar results
    
    def __post_init__(self):
        """Validate fusion configuration"""
        if self.rrf_k <= 0:
            raise ValueError("rrf_k must be positive")
        if self.final_top_k <= 0:
            raise ValueError("final_top_k must be positive")
        if not 0 <= self.diversity_penalty <= 1:
            raise ValueError("diversity_penalty must be between 0 and 1")


@dataclass
class PerformanceConfig:
    """Performance and monitoring configuration"""
    enable_timing: bool = True
    enable_caching: bool = True
    cache_ttl: int = 3600  # Cache TTL in seconds
    max_concurrent_paths: int = 4
    timeout_per_path: float = 30.0  # Timeout per path in seconds
    enable_fallback: bool = True  # Enable fallback to single path on failure
    
    def __post_init__(self):
        """Validate performance configuration"""
        if self.cache_ttl <= 0:
            raise ValueError("cache_ttl must be positive")
        if self.max_concurrent_paths <= 0:
            raise ValueError("max_concurrent_paths must be positive")
        if self.timeout_per_path <= 0:
            raise ValueError("timeout_per_path must be positive")


@dataclass
class RerankConfig:
    """Configuration for reranking"""
    enabled: bool = True
    api_key: Optional[str] = None
    model: str = "qianwen"
    top_k: int = 10
    batch_size: int = 32
    max_concurrent: int = 4
    
    def __post_init__(self):
        """Validate rerank configuration"""
        if self.top_k <= 0:
            raise ValueError("top_k must be positive")
        if self.batch_size <= 0:
            raise ValueError("batch_size must be positive")
        if self.max_concurrent <= 0:
            raise ValueError("max_concurrent must be positive")


@dataclass
class AdvancedRAGConfig:
    """Advanced RAG configuration for multi-path retrieval
    
    This class provides comprehensive configuration for multi-path RAG retrieval,
    including individual path settings, fusion methods, and performance tuning.
    """
    
    # Path configurations
    paths: Dict[RetrievalPath, PathConfig] = field(default_factory=lambda: {
        RetrievalPath.VECTOR: PathConfig(enabled=True, weight=0.4, top_k=50),
        RetrievalPath.KEYWORDS: PathConfig(enabled=True, weight=0.3, top_k=30),
        RetrievalPath.SUMMARY: PathConfig(enabled=True, weight=0.2, top_k=20),
        RetrievalPath.CONTENT: PathConfig(enabled=True, weight=0.1, top_k=20)
    })
    
    # Fusion configuration
    fusion: FusionConfig = field(default_factory=FusionConfig)
    
    # Performance configuration
    performance: PerformanceConfig = field(default_factory=PerformanceConfig)
    
    # Reranking configuration
    rerank: RerankConfig = field(default_factory=RerankConfig)
    
    # Legacy reranking properties for backward compatibility
    enable_reranking: bool = True
    rerank_top_k: int = 10
    rerank_model: str = "qianwen"
    
    def __post_init__(self):
        """Validate and normalize configuration"""
        self._validate_weights()
        self._normalize_weights()
    
    def _validate_weights(self):
        """Validate that at least one path is enabled with positive weight"""
        enabled_paths = [path for path, config in self.paths.items() 
                        if config.enabled and config.weight > 0]
        if not enabled_paths:
            raise ValueError("At least one retrieval path must be enabled with positive weight")
    
    def _normalize_weights(self):
        """Normalize weights to sum to 1.0 for enabled paths"""
        enabled_weights = {path: config.weight for path, config in self.paths.items() 
                          if config.enabled}
        
        if not enabled_weights:
            return
        
        total_weight = sum(enabled_weights.values())
        if total_weight > 0:
            for path, config in self.paths.items():
                if config.enabled:
                    config.weight = config.weight / total_weight
    
    def get_enabled_paths(self) -> List[RetrievalPath]:
        """Get list of enabled retrieval paths"""
        return [path for path, config in self.paths.items() if config.enabled]
    
    def get_path_weight(self, path: RetrievalPath) -> float:
        """Get weight for specific path"""
        return self.paths.get(path, PathConfig()).weight
    
    def set_path_weight(self, path: RetrievalPath, weight: float):
        """Set weight for specific path and renormalize"""
        if path in self.paths:
            self.paths[path].weight = weight
            self._normalize_weights()
    
    def enable_path(self, path: RetrievalPath, enabled: bool = True):
        """Enable or disable specific retrieval path"""
        if path in self.paths:
            self.paths[path].enabled = enabled
            if enabled:
                self._normalize_weights()
    
    def update_fusion_method(self, method: FusionMethod, **kwargs):
        """Update fusion method and parameters"""
        self.fusion.method = method
        for key, value in kwargs.items():
            if hasattr(self.fusion, key):
                setattr(self.fusion, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        return {
            'paths': {
                path.value: {
                    'enabled': config.enabled,
                    'weight': config.weight,
                    'top_k': config.top_k,
                    'min_score': config.min_score,
                    'boost_factor': config.boost_factor
                } for path, config in self.paths.items()
            },
            'fusion': {
                'method': self.fusion.method.value,
                'rrf_k': self.fusion.rrf_k,
                'normalize_scores': self.fusion.normalize_scores,
                'final_top_k': self.fusion.final_top_k,
                'score_threshold': self.fusion.score_threshold,
                'diversity_penalty': self.fusion.diversity_penalty
            },
            'performance': {
                'enable_timing': self.performance.enable_timing,
                'enable_caching': self.performance.enable_caching,
                'cache_ttl': self.performance.cache_ttl,
                'max_concurrent_paths': self.performance.max_concurrent_paths,
                'timeout_per_path': self.performance.timeout_per_path,
                'enable_fallback': self.performance.enable_fallback
            },
            'reranking': {
                'enable_reranking': self.enable_reranking,
                'rerank_top_k': self.rerank_top_k,
                'rerank_model': self.rerank_model
            },
            'rerank': {
                'enabled': self.rerank.enabled,
                'api_key': self.rerank.api_key,
                'model': self.rerank.model,
                'top_k': self.rerank.top_k,
                'batch_size': self.rerank.batch_size,
                'max_concurrent': self.rerank.max_concurrent
            }
        }
    
    @classmethod
    def from_dict(cls, config_dict: Dict[str, Any]) -> 'AdvancedRAGConfig':
        """Create configuration from dictionary"""
        # Parse paths
        paths = {}
        if 'paths' in config_dict:
            for path_name, path_config in config_dict['paths'].items():
                path = RetrievalPath(path_name)
                paths[path] = PathConfig(**path_config)
        
        # Parse fusion config
        fusion_config = FusionConfig()
        if 'fusion' in config_dict:
            fusion_data = config_dict['fusion'].copy()
            if 'method' in fusion_data:
                fusion_data['method'] = FusionMethod(fusion_data['method'])
            fusion_config = FusionConfig(**fusion_data)
        
        # Parse performance config
        performance_config = PerformanceConfig()
        if 'performance' in config_dict:
            performance_config = PerformanceConfig(**config_dict['performance'])
        
        # Parse rerank config
        rerank_config = RerankConfig()
        if 'rerank' in config_dict:
            rerank_config = RerankConfig(**config_dict['rerank'])
        
        # Create main config
        config = cls(
            paths=paths if paths else cls().paths,
            fusion=fusion_config,
            performance=performance_config,
            rerank=rerank_config
        )
        
        # Set legacy reranking config for backward compatibility
        if 'reranking' in config_dict:
            legacy_rerank_config = config_dict['reranking']
            config.enable_reranking = legacy_rerank_config.get('enable_reranking', True)
            config.rerank_top_k = legacy_rerank_config.get('rerank_top_k', 10)
            config.rerank_model = legacy_rerank_config.get('rerank_model', 'qianwen')
        
        return config
    
    def save_to_file(self, file_path: str):
        """Save configuration to JSON file"""
        config_dict = self.to_dict()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    
    @classmethod
    def load_from_file(cls, file_path: str) -> 'AdvancedRAGConfig':
        """Load configuration from JSON file"""
        with open(file_path, 'r', encoding='utf-8') as f:
            config_dict = json.load(f)
        return cls.from_dict(config_dict)
    
    def clone(self) -> 'AdvancedRAGConfig':
        """Create a deep copy of the configuration"""
        return self.from_dict(self.to_dict())
    
    @classmethod
    def get_preset_config(cls, config_name: str) -> 'AdvancedRAGConfig':
        """Get preset configuration by name
        
        Args:
            config_name: Name of the preset configuration
                       ('balanced', 'vector_focused', 'keyword_focused', 
                        'fast_retrieval', 'high_precision')
        
        Returns:
            AdvancedRAGConfig: The requested preset configuration
        
        Raises:
            ValueError: If config_name is not recognized
        """
        preset_map = {
            'balanced': PresetConfigs.balanced,
            'vector_focused': PresetConfigs.vector_focused,
            'keyword_focused': PresetConfigs.keyword_focused,
            'fast_retrieval': PresetConfigs.fast_retrieval,
            'high_precision': PresetConfigs.high_precision
        }
        
        if config_name not in preset_map:
            available_configs = list(preset_map.keys())
            raise ValueError(f"Unknown config name '{config_name}'. Available configs: {available_configs}")
        
        return preset_map[config_name]()


# Predefined configurations for different scenarios
class PresetConfigs:
    """Predefined configurations for common use cases"""
    
    @staticmethod
    def balanced() -> AdvancedRAGConfig:
        """Balanced configuration for general use"""
        return AdvancedRAGConfig()
    
    @staticmethod
    def vector_focused() -> AdvancedRAGConfig:
        """Vector-focused configuration for semantic search"""
        config = AdvancedRAGConfig()
        config.set_path_weight(RetrievalPath.VECTOR, 0.7)
        config.set_path_weight(RetrievalPath.KEYWORDS, 0.2)
        config.set_path_weight(RetrievalPath.SUMMARY, 0.1)
        config.enable_path(RetrievalPath.CONTENT, False)
        return config
    
    @staticmethod
    def keyword_focused() -> AdvancedRAGConfig:
        """Keyword-focused configuration for exact matching"""
        config = AdvancedRAGConfig()
        config.set_path_weight(RetrievalPath.VECTOR, 0.2)
        config.set_path_weight(RetrievalPath.KEYWORDS, 0.5)
        config.set_path_weight(RetrievalPath.SUMMARY, 0.2)
        config.set_path_weight(RetrievalPath.CONTENT, 0.1)
        return config
    
    @staticmethod
    def fast_retrieval() -> AdvancedRAGConfig:
        """Fast retrieval configuration with reduced paths"""
        config = AdvancedRAGConfig()
        config.enable_path(RetrievalPath.SUMMARY, False)
        config.enable_path(RetrievalPath.CONTENT, False)
        config.set_path_weight(RetrievalPath.VECTOR, 0.7)
        config.set_path_weight(RetrievalPath.KEYWORDS, 0.3)
        config.performance.max_concurrent_paths = 2
        config.enable_reranking = False
        return config
    
    @staticmethod
    def high_precision() -> AdvancedRAGConfig:
        """High precision configuration with all paths enabled"""
        config = AdvancedRAGConfig()
        config.fusion.method = FusionMethod.WEIGHTED_RRF
        config.fusion.rrf_k = 30  # Lower k for more aggressive ranking
        config.enable_reranking = True
        config.rerank_top_k = 15
        return config