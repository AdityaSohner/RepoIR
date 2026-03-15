from app.ai.extractors.doc_extractor import DocumentExtractor
from app.ai.extractors.img_extractor import ImageExtractor
from app.ai.extractors.url_extractor import LinkExtractor
from app.ai.extractors.vision_describer import VisionDescriber
from app.ai.chunker.text_chunker import TextChunker
from app.ai.embeddings.text_embedder import TextEmbedder
from app.storage.id_generator import generate_object_id
from app.storage.object_store import save_file
from app.storage.db_store import DBStore
from app.storage.faiss_store import FAISSStore
from app.ai.normalizers.pdf import normalize_pdf
from app.ai.normalizers.docx import normalize_docx
from app.ai.normalizers.excel import normalize_excel
from app.config import DEFAULT_USER_ID
import os
import io
import base64
from PIL import Image
import numpy as np
import threading

# Global lock to prevent parallel ingestion race conditions
_ingestion_lock = threading.Lock()

class IngestionPipeline:
    def __init__(self, user_id: str = "default"):
        self.chunker = TextChunker(chunk_size=300, overlap=50)
        self.embedder = TextEmbedder()
        self.db = DBStore(user_id=user_id)
        self.faiss = FAISSStore(user_id=user_id)
        self.vision = VisionDescriber()
        self.link_extractor = LinkExtractor()

    def ingest(self, source, source_type: str, extension: str = None, 
               original_name: str = None, object_id: str = None, 
               skip_local_storage: bool = False) -> dict:
        if source_type in ("document", "text"):
            extractor = DocumentExtractor()
        elif source_type == "image":
            extractor = ImageExtractor()
        elif source_type == "url":
            extractor = LinkExtractor()
        else:
            raise ValueError(f"Unsupported source type: {source_type}")

        user_id = self.db.user_dir.name 
        extraction_result = extractor.extract(source, extension=extension)
        raw_text = extraction_result["raw_text"]
        file_type = extraction_result["metadata"]["file_type"]

        if file_type == ".pdf":
            semantic_text = normalize_pdf(raw_text)
        elif file_type == ".docx":
            semantic_text = normalize_docx(raw_text)
        elif file_type in [".xlsx", ".xls"]:
            semantic_text = normalize_excel(raw_text)
        elif file_type == "url":
            title = extraction_result["metadata"].get("title", "Webpage")
            if not raw_text.strip():
                semantic_text = ""
            else:
                semantic_text = f"TITLE: {title}\n\nCONTENT: {raw_text}"
        else:
            semantic_text = raw_text

        if source_type == "image":
            try:
                if hasattr(source, 'seek'):
                    source.seek(0)
                vision_text = self.vision.describe(source)
                if vision_text:
                    semantic_text = (semantic_text + "\n\n" + vision_text).strip()
            except Exception as vision_err:
                print(f"⚠️ Vision description failed: {vision_err}")
            
            if not semantic_text.strip():
                # Fallback to filename if vision and OCR both fail
                semantic_text = original_name or "Untitled Image"
                print(f"⚠️ Image content extraction failed. Falling back to filename: {semantic_text}")
        elif not semantic_text.strip():
            # Fallback to filename for other documents too
            semantic_text = original_name or "Untitled Document"
            print(f"⚠️ Document content extraction failed. Falling back to filename: {semantic_text}")

        chunks = self.chunker.chunk(semantic_text)
        if not chunks:
            raise ValueError("No chunks generated")

        embeddings = self.embedder.embed(chunks)
        if not object_id:
            object_id = generate_object_id()
        chunk_ids = [f"{object_id}_chunk_{i}" for i in range(len(chunks))]

        # Calculate Size
        file_size = 0

        if isinstance(source, bytes):
            file_size = len(source)
        elif hasattr(source, 'seek'):
            source.seek(0, 2)
            file_size = source.tell()
            source.seek(0)
        elif isinstance(source, str) and os.path.exists(source):
            file_size = os.path.getsize(source)
        elif source_type == "url":
            file_size = len(semantic_text.encode('utf-8'))


        file_path = None
        if source_type in ("document", "image", "text") and not skip_local_storage:
            file_path = save_file(source, object_id, f"{source_type}s", original_filename=original_name)

        self.db.store_object(
            object_id, user_id, original_name or str(source), 
            source_type, file_type, file_path, len(chunks), 
            file_size, thumbnail_url=None
        )
        self.db.store_chunks(object_id, chunks)
        with _ingestion_lock:
            start_id = self.db.get_next_vector_id()
            vector_ids = np.arange(start_id, start_id + len(embeddings)).astype("int64")
            self.faiss.add(embeddings, ids=vector_ids)
            self.db.store_vectors(start_id, chunk_ids)
        
        # Log Activity
        self.db.log_activity(user_id, "UPLOAD", f"Uploaded {original_name or source_type}")

        # self.check_against_categories(object_id, semantic_text)
        
        return {
            "object_id": object_id,
            "source": original_name or str(source),
            "type": source_type,
            "chunk_count": len(chunks),
            "file_size": file_size,
            "file_path": file_path
        }
        
    def check_against_categories(self, object_id: str, semantic_text: str):
        """Runs after ingestion to see if new file belongs to any 'Virtual Folders'."""
        categories = self.db.get_all_categories()
        if not categories:
            return
            
        file_vector = self.embedder.embed(semantic_text)
        
        for cat in categories:
            desc = cat.get('description', '') or cat.get('name', '')
            if not desc.strip():
                continue
            cat_vector = self.embedder.embed(desc).astype(np.float32).flatten()
            v1 = file_vector.flatten().astype(np.float32)
            
            n1, n2 = np.linalg.norm(v1), np.linalg.norm(cat_vector)
            if n1 and n2:
                similarity = float(np.dot(v1, cat_vector) / (n1 * n2))
            else:
                similarity = 0.0
            
            if similarity > 0.40:
                self.db.map_files_to_category(cat['category_id'], [object_id])

