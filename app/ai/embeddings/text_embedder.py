from typing import List, Union
import numpy as np
from sentence_transformers import SentenceTransformer


class TextEmbedder:
    """
    Text → vector embedding using a fixed, CPU-friendly model.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: Union[str, List[str]]) -> np.ndarray:
        if isinstance(texts, str):
            texts = [texts]

        embeddings = self.model.encode(
            texts,
            normalize_embeddings=True,
            show_progress_bar=False
        )

        return embeddings
