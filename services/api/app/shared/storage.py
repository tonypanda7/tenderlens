"""
TenderLens — MinIO Storage Client Wrapper
"""
import io
from minio import Minio
from app.config import settings

class StorageClient:
    def __init__(self):
        # minio_endpoint is something like "storage:9000" or "localhost:9000"
        self.client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_root_user,
            secret_key=settings.minio_root_password,
            secure=settings.minio_use_ssl
        )
        self.bucket_name = settings.minio_bucket
        self._ensure_bucket()

    def _ensure_bucket(self):
        try:
            if not self.client.bucket_exists(self.bucket_name):
                self.client.make_bucket(self.bucket_name)
        except Exception as e:
            # Depending on timing, the MinIO server might not be ready yet
            print(f"Failed to create bucket {self.bucket_name}: {e}")

    def upload_file(self, file_data: bytes, object_name: str, content_type: str = "application/octet-stream") -> str:
        """Uploads a file to MinIO and returns the object path."""
        self._ensure_bucket()
        data_stream = io.BytesIO(file_data)
        self.client.put_object(
            bucket_name=self.bucket_name,
            object_name=object_name,
            data=data_stream,
            length=len(file_data),
            content_type=content_type
        )
        return object_name

    def download_file(self, object_name: str) -> bytes:
        """Downloads a file from MinIO and returns the raw bytes."""
        try:
            response = self.client.get_object(self.bucket_name, object_name)
            return response.read()
        finally:
            response.close()
            response.release_conn()

storage_client = StorageClient()
