"""Text embeddings with a deterministic dependency-free fallback."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Iterable

import numpy as np


class Embedder:
    """Embed text with FastEmbed, falling back to signed feature hashing."""

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        dimension: int = 384,
        *,
        prefer_fastembed: bool = True,
    ) -> None:
        self.model_name = model_name
        self.dimension = dimension
        self.backend = "hashing"
        self._model = None
        if prefer_fastembed:
            try:
                from fastembed import TextEmbedding

                self._model = TextEmbedding(model_name=model_name)
                self.backend = "fastembed"
            except (ImportError, OSError, RuntimeError, ValueError):
                self._model = None

    def _hashing_vector(self, text: str) -> np.ndarray:
        vector = np.zeros(self.dimension, dtype=np.float32)
        tokens = re.findall(r"[\w'-]+", text.casefold(), flags=re.UNICODE)
        features = tokens + [
            f"{left}_{right}" for left, right in zip(tokens, tokens[1:])
        ]
        for feature in features:
            digest = hashlib.blake2b(
                feature.encode("utf-8"), digest_size=8, person=b"gestaltx"
            ).digest()
            value = int.from_bytes(digest, "little")
            index = value % self.dimension
            vector[index] += -1.0 if value & (1 << 63) else 1.0
        norm = float(np.linalg.norm(vector))
        if norm:
            vector /= norm
        return vector

    def embed(self, texts: str | Iterable[str]) -> np.ndarray:
        """Return a two-dimensional float32 array for one or more strings."""
        values = [texts] if isinstance(texts, str) else list(texts)
        if not values:
            return np.empty((0, self.dimension), dtype=np.float32)
        if self._model is not None:
            matrix = np.asarray(list(self._model.embed(values)), dtype=np.float32)
            if matrix.ndim == 1:
                matrix = matrix.reshape(1, -1)
            self.dimension = int(matrix.shape[1])
            return matrix
        return np.stack([self._hashing_vector(text) for text in values])

    def embed_query(self, text: str) -> np.ndarray:
        return self.embed([text])[0]

    def embed_documents(self, texts: Iterable[str]) -> np.ndarray:
        return self.embed(texts)


__all__ = ["Embedder"]
