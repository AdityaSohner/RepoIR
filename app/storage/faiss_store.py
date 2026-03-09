import faiss
import numpy as np
from pathlib import Path

DIM = 384
FAISS_PATH = Path("data/faiss.index")


class FAISSStore:
    """
    Handles only the vector similarity operations.
    The vector_id → chunk_id mapping is stored in SQLite (DBStore.vectors).
    """

    def __init__(self, user_id: str = "default"):
        self.user_dir = Path(f"data/users/{user_id}")
        self.index_path = self.user_dir / "faiss.index"
        self.index = self._load()

    def _load(self):
        if self.index_path.exists():
            return faiss.read_index(str(self.index_path))
        return faiss.IndexFlatL2(DIM)

    def _persist(self):
        self.user_dir.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))

    def add(self, embeddings: np.ndarray):
        """Add a batch of embedding vectors. Persists immediately."""
        self.index.add(embeddings.astype("float32"))
        self._persist()

    def search(self, query: np.ndarray, k: int) -> list[int]:
        """
        Search for top-k nearest vectors.
        Reloads from disk first (so newly ingested files are always visible).
        Returns list of FAISS integer IDs.
        """
        self.index = self._load()   # always fresh
        emb = query.astype("float32").reshape(1, -1)
        _, ids = self.index.search(emb, k)
        return [int(i) for i in ids[0] if i >= 0]

    def total_vectors(self) -> int:
        return self.index.ntotal

    def search_with_scores(self, query: np.ndarray, k: int):
        """Returns both distances and vector IDs."""
        self.index = self._load()
        emb = query.astype("float32").reshape(1, -1)
        distances, ids = self.index.search(emb, k)
        return distances[0], [int(i) for i in ids[0] if i >= 0]



