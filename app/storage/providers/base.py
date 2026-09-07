from abc import ABC, abstractmethod
import io
from typing import List, Dict, Any, Optional

class StorageProvider(ABC):
    """
    Abstract StorageProvider interface for cloud storage integrations.
    App components interact strictly with this interface.
    """

    @abstractmethod
    def upload(self, file_stream: io.BytesIO, filename: str, folder_id: Optional[str] = None, mime_type: str = 'application/octet-stream') -> str:
        """Uploads a file stream and returns the remote file_id."""
        pass

    @abstractmethod
    def download(self, file_id: str) -> Optional[io.BytesIO]:
        """Downloads a file stream by remote file_id."""
        pass

    @abstractmethod
    def delete(self, file_id: str) -> bool:
        """Permanently deletes a file by remote file_id."""
        pass

    @abstractmethod
    def move_to_trash(self, file_id: str) -> bool:
        """Moves a file to trash by remote file_id."""
        pass

    @abstractmethod
    def restore(self, file_id: str) -> bool:
        """Restores a trashed file by remote file_id."""
        pass

    @abstractmethod
    def list_files(self, query: Optional[str] = None) -> List[Dict[str, Any]]:
        """Lists files matching the query."""
        pass

    @abstractmethod
    def get_metadata(self, file_id: str) -> Dict[str, Any]:
        """Fetches file metadata by remote file_id."""
        pass
