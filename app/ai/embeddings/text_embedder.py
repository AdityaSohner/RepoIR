from typing import List, Union
import numpy as np
import torch
from sentence_transformers import SentenceTransformer

# Singleton to prevent OOM by loading model multiple times
_MODEL_INSTANCE = None

class TextEmbedder:
    """
    Text → vector embedding using a fixed, CPU-friendly model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        global _MODEL_INSTANCE
        # Limit torch threads to 1 to reduce memory overhead in container
        torch.set_num_threads(1)
        
        if _MODEL_INSTANCE is None:
            print(f"🧠 Loading AI Model: {model_name}...")
            _MODEL_INSTANCE = SentenceTransformer(model_name)
        self.model = _MODEL_INSTANCE

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return embeddings
