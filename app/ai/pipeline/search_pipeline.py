import numpy as np
import asyncio
from app.ai.embeddings.text_embedder import TextEmbedder
from app.storage.db_store import DBStore
from app.storage.faiss_store import FAISSStore
from sentence_transformers import CrossEncoder


def _reciprocal_rank_fusion(ranked_lists: list[list[str]], k: int = 60) -> list[str]:
    """
    Merge multiple ranked lists using Reciprocal Rank Fusion.

    RRF score = sum(1 / (rank + k)) for each list where the item appears.
    Higher score = better result.

    Args:
        ranked_lists: Each inner list is a ranked list of chunk_ids
        k:            Smoothing constant (60 is standard)

    Returns:
        Single merged + re-ranked list of chunk_ids
    """
    scores: dict[str, float] = {}
    for ranked in ranked_lists:
        for rank, item in enumerate(ranked):
            if item not in scores:
                scores[item] = 0.0
            scores[item] += 1.0 / (rank + k)

    return sorted(scores, key=lambda x: scores[x], reverse=True)


# ── Module-level CrossEncoder singleton (loads once, cached for the process) ──
_reranker: CrossEncoder | None = None

def _get_reranker() -> CrossEncoder:
    global _reranker
    if _reranker is None:
        print("[*] Loading CrossEncoder reranker (BAAI/bge-reranker-v2-m3)...")
        _reranker = CrossEncoder("BAAI/bge-reranker-v2-m3")
        print("[+] CrossEncoder reranker ready.")
    return _reranker


class SearchPipeline:
    def __init__(self, user_id: str = "default"):
        self.embedder = TextEmbedder()
        self.db = DBStore(user_id=user_id)
        self.faiss = FAISSStore(user_id=user_id)

    def _rerank_with_cross_encoder(self, query: str, candidates: list[dict]) -> list[dict]:
        """
        Reranks candidates using a local BAAI/bge-reranker-v2-m3 CrossEncoder.
        Returns candidates with rerank_score attached, filtered to score > 0.5.
        Falls back to pre-rerank order on any error.
        """
        if not candidates:
            return []

        try:
            reranker = _get_reranker()

            pairs = []
            valid_candidates = []
            for c in candidates:
                chunk_text = self.db.get_best_chunk_text_for_object(c["object_id"])
                if chunk_text:
                    pairs.append((query, chunk_text))
                    valid_candidates.append(c)
                else:
                    c["rerank_score"] = 0.0

            if not pairs:
                print("[WARNING] Reranker: no chunk text found for any candidate, skipping rerank.")
                return candidates

            scores = reranker.predict(pairs)
            print(f"[*] Reranker scored {len(pairs)} candidates. Scores: {[round(float(s), 3) for s in scores]}")

            for c, score in zip(valid_candidates, scores):
                c["rerank_score"] = float(score)

            for c in candidates:
                if "rerank_score" not in c:
                    c["rerank_score"] = 0.0

            reranked = [c for c in candidates if c["rerank_score"] > 0.5]
            reranked.sort(key=lambda x: x["rerank_score"], reverse=True)
            print(f"[*] Reranker: {len(reranked)}/{len(candidates)} candidates passed >0.5 threshold.")

            if not reranked:
                print("[WARNING] Reranker: no candidates passed threshold, returning all scored.")
                reranked = sorted(candidates, key=lambda x: x["rerank_score"], reverse=True)

            return reranked

        except Exception as e:
            print(f"[ERROR] CrossEncoder reranker failed: {e}. Falling back to pre-rerank ordering.")
            return candidates

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """Wrapper to run the async search in a synchronous context if needed,
        but in our FastAPI app we will call it properly."""
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # This is tricky in FastAPI, but main search is called async in app_server
            return loop.create_task(self.search_async(query, top_k))
        else:
            return loop.run_until_complete(self.search_async(query, top_k))

    async def search_async(self, query: str, top_k: int = 10) -> list[dict]:
        """
        Two-Stage Intelligent Search:
        1. Retrieval: BM25 + Vector + RRF merge
        2. Re-Ranking: Local CrossEncoder (BAAI/bge-reranker-v2-m3) quality filter
        """
        if not query.strip():
            return []

        candidate_count = 30
        q_lower = query.lower()

        # ── Stage 1: Retrieval ─────────────────────────────────────────────
        bm25_chunk_ids = self.db.keyword_search(query, k=candidate_count)

        query_vector = self.embedder.embed(query)
        distances, vector_ids = self.faiss.search_with_scores(query_vector, k=candidate_count)

        # Relaxed threshold to maintain semantic connections without grabbing complete noise
        valid_vids = [vid for dist, vid in zip(distances, vector_ids) if dist < 1.3]
        faiss_chunk_ids = [self.db.get_chunk_id_by_vector(vid) for vid in valid_vids]
        faiss_chunk_ids = [cid for cid in faiss_chunk_ids if cid]

        # Merge with RRF
        merged_chunk_ids = _reciprocal_rank_fusion([bm25_chunk_ids, faiss_chunk_ids])

        # Convert chunks to Objects
        object_ids = []
        seen = set()
        for cid in merged_chunk_ids:
            oid = cid.rsplit("_chunk_", 1)[0] if "_chunk_" in cid else cid
            if oid not in seen:
                object_ids.append(oid)
                seen.add(oid)

        # Fetch metadata
        candidates = self.db.get_objects_by_ids(object_ids)

        if not candidates:
            return []

        # ── Stage 2: Filename Boosting ───────────────────────────────────
        boosted = []
        others = []
        for c in candidates:
            source_lower = c["source"].lower()
            if any(word in source_lower for word in q_lower.split()):
                boosted.append(c)
            else:
                others.append(c)

        candidates = boosted + others

        # ── Stage 3: CrossEncoder Reranking ──────────────────────────────
        # Run in a thread so we don't block the async event loop
        reranked = await asyncio.to_thread(
            self._rerank_with_cross_encoder, query, candidates
        )

        return reranked

