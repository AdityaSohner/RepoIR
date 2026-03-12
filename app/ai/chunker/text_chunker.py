import re


class TextChunker:
    """
    Splits a long document text into overlapping word-based chunks.
    Each chunk is a self-contained window of text suitable for embedding.
    """

    def __init__(self, chunk_size: int = 300, overlap: int = 50):
        """
        Args:
            chunk_size: Number of words per chunk.
            overlap:    Number of words to repeat at the start of the next chunk.
                        This prevents losing context at chunk boundaries.
        """
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk(self, text: str) -> list[str]:
        """
        Split text into overlapping chunks.

        Args:
            text: The full normalized document text.

        Returns:
            List of chunk strings. Empty list if text is too short.
        """
        if not text or not text.strip():
            return []

        # Normalize whitespace
        text = re.sub(r"\s+", " ", text).strip()

        words = text.split(" ")

        # If the whole text is smaller than one chunk, return it as-is
        if len(words) <= self.chunk_size:
            return [text]

        chunks = []
        start = 0

        while start < len(words):
            end = start + self.chunk_size
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)
            chunks.append(chunk_text)

            # Move forward by (chunk_size - overlap) to create overlap
            start += self.chunk_size - self.overlap

            # Stop if remaining words are too few to be useful (< 30 words)
            if start < len(words) and len(words) - start < 30:
                # Grab the last bit as a final chunk
                last_chunk = " ".join(words[start:])
                if last_chunk.strip():
                    chunks.append(last_chunk)
                break

        return chunks
