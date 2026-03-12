import numpy as np
import os
import json
import asyncio
from app.ai.embeddings.text_embedder import TextEmbedder
from app.storage.db_store import DBStore
from app.storage.faiss_store import FAISSStore


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


class SearchPipeline:
    def __init__(self, user_id: str = "default"):
        self.embedder = TextEmbedder()
        self.db = DBStore(user_id=user_id)
        self.faiss = FAISSStore(user_id=user_id)

    async def _rerank_with_llm(self, query: str, candidates: list[dict]) -> list[dict]:
        """Uses SambaNova Online LLM to filter and rank candidates strictly."""
        from app_server import call_llm
        
        if not candidates:
            return []

        # Prepare a condensed list for the LLM
        candidate_list = []
        for i, c in enumerate(candidates):
            candidate_list.append({
                "id": c["object_id"],
                "index": i,
                "name": c["source"],
                "type": c["type"]
            })

        prompt = (
            f"User Query: '{query}'\n"
            f"Candidates: {json.dumps(candidate_list)}\n\n"
            "Task: Rank these files by strict relevance to the query. "
            "Rule 1: If a file does NOT directly and specifically relate to the user's explicit query, you MUST completely EXCLUDE it. Do not include loosely related noise. "
            "Rule 2: Prioritize files that exact-match the core intent. If a URL or file only lightly touches on it, drop it. "
            "Return ONLY a JSON array of object_ids in the new ranked order. "
            "Example Output: ['id1', 'id2']"
        )

        try:
            response_text = await call_llm(prompt)
            # Find JSON array in response
            import re
            match = re.search(r"\[.*\]", response_text.replace("\n", ""))
            if match:
                ordered_ids = json.loads(match.group(0))
                # Map back to full objects
                id_map = {c["object_id"]: c for c in candidates}
                return [id_map[oid] for oid in ordered_ids if oid in id_map]
        except Exception as e:
            print(f"⚠️ Re-ranking failed: {e}")
        
        return candidates # Fallback to original rank

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
        1. Retrieval: BM25 + Vector + Filename Boosting
        2. Re-Ranking: Online LLM Quality filter
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

        # ── Stage 2: Strategy (Boosting) ────────────────────────
        # Filename Boosting
        boosted = []
        others = []
        for c in candidates:
            source_lower = c["source"].lower()
            if any(word in source_lower for word in q_lower.split()):
                boosted.append(c)
            else:
                others.append(c)
        
        candidates = boosted + others

        # By removing the LLM filter, we eliminate the logical error 
        # where perfectly valid files with non-descriptive names were dropped.
        return candidates[:top_k]
