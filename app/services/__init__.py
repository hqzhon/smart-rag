"""
服务层模块
"""

from .document_service import DocumentService
from .chat_service import ChatService

try:
    from .search_service import SearchService
    __all__ = [
        "DocumentService",
        "ChatService", 
        "SearchService"
    ]
except ImportError:
    __all__ = [
        "DocumentService",
        "ChatService"
    ]
