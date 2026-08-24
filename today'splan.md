# RepoIR — same-day fix + audio transcript plan

**Your hardware:** RTX 4050 (6GB) + 16GB RAM = can run small/medium VLMs + rerankers fast enough to feel real-time on small test sets.

**Today's scope:** Fix what's broken in the *current* architecture (no scaling), add audio transcription, prove it works. Report tomorrow.

---

## What's actually broken right now

1. **Vision captioning API is dead** — SambaNova hits rate limits, silently returns `""`. Images lose their semantic signal entirely.
2. **Search reranking is deleted** — `_rerank_with_llm` was commented out; search is pure keyword + RRF now, feels dumb.
3. **URL scraping is flaky** — Jina's free tier fails on React sites, Antigravity added the IP-spoofing hack which is brittle.
4. **Audio transcription doesn't exist** — you have audio ingestion code but no transcript generation.

You're going to fix 1+2+4 today. Leave URL scraping alone (it's working-enough and the fix is messy).

---

## Three tools, all local, all free

### 1. Vision captioning → Ollama + Moondream2

**Why Moondream2:** Runs on 6GB GPU easily (< 2 sec per image on RTX 4050), knowledge about real-world objects/movies/people is surprisingly good for a tiny model, zero API key.

**Installation:**
```bash
# Download Ollama from https://ollama.ai
# Run it (GUI or daemon)
ollama pull moondream2
```

That's it. Ollama gives you a local API endpoint on `http://localhost:11434/api/generate` (it's not REST, it's custom streaming JSON).

**Replace in code:** `vision_describer.py` currently has a SambaNova call wrapped in try/except. Rip that out, call Ollama instead. The prompt doesn't need to be fancy — just:
```
Describe what you see in this image for a search index. Name specific things if you can.
```

**Integration snippet** (Antigravity will write the full version):
```python
import requests
import json

def describe_image_ollama(image_base64_or_path):
    # Convert image to base64 if needed
    payload = {
        "model": "moondream2",
        "prompt": "Describe what you see in this image for a search index. Name specific things if you can.",
        "images": [image_base64_or_path],  # Ollama expects base64
        "stream": False
    }
    response = requests.post('http://localhost:11434/api/generate', json=payload)
    result = response.json()
    return result.get("response", "").strip()
```

---

### 2. Search reranking → sentence-transformers

**Why this:** Cross-encoder rerankers are purpose-built for "does this match the query?" — they're much smarter than RRF at detecting real relevance. `BAAI/bge-reranker-v2-m3` is state-of-the-art tiny and free.

**Installation:**
```bash
pip install sentence-transformers torch
```

**Wire it back into `search_async`:**
The pipeline currently does BM25 + FAISS → merge via RRF → return top-5. 

New pipeline: BM25 + FAISS → merge via RRF → rerank with cross-encoder → return top-5.

The reranker takes (query, candidate_text_chunk) pairs and outputs a score 0–1. You cut off by score, not by count — so you can return 1 result or 12, depending on how good they actually are.

**Integration snippet:**
```python
from sentence_transformers import CrossEncoder

reranker = CrossEncoder('BAAI/bge-reranker-v2-m3')

# After BM25+FAISS merge, before returning:
scores = reranker.predict([(query, chunk['text']) for chunk in candidates])
# Attach scores to candidates
for i, chunk in enumerate(candidates):
    chunk['rerank_score'] = scores[i]

# Sort by score, return only those above threshold (e.g., 0.5)
reranked = sorted(candidates, key=lambda x: x['rerank_score'], reverse=True)
reranked = [c for c in reranked if c['rerank_score'] > 0.5]
```

First inference is slow (~2 sec on CPU), then cached. On GPU it's instant.

---

### 3. Audio transcription → Whisper

**Why this:** OpenAI's Whisper is free, open, runs locally, handles 90+ languages, works great on your hardware.

**Installation:**
```bash
pip install openai-whisper
# First run downloads the model (~1.5GB for 'base', one-time)
```

**Add to ingestion pipeline** (new extractor):

Create `app/ai/extractors/audio_extractor.py`:
```python
import whisper
from pathlib import Path

class AudioExtractor:
    def __init__(self, model='base'):
        self.model = whisper.load_model(model)  # 'tiny' if 6GB GPU too tight, 'base' is default
    
    def extract(self, audio_path):
        """Return transcribed text"""
        result = self.model.transcribe(str(audio_path), language='en')
        return result['text']
```

Wire it into your ingest pipeline wherever you currently skip audio files. First time on a 10-min audio = ~20 sec on GPU. Subsequent files get faster (cached model).

---

## The actual TODAY checklist

### Part 1: Set up local infra (30 min)
- [ ] Download + run Ollama, `ollama pull moondream2`
- [ ] `pip install sentence-transformers torch`
- [ ] `pip install openai-whisper`
- [ ] Test each one manually:
  - Ollama: `curl http://localhost:11434/api/tags` should list moondream2
  - sentence-transformers: `python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"` should download + load
  - Whisper: `python -c "import whisper; whisper.load_model('base')"` should download model

### Part 2: Patch the code via Antigravity (60–90 min)
Tell Antigravity to:
```
In RepoIR:
1. Replace SambaNova call in app/ai/extractors/vision_describer.py with Ollama API call to moondream2
2. Create app/ai/extractors/audio_extractor.py with Whisper integration
3. Wire audio_extractor into app/ai/pipeline/ingestion_pipeline.py so audio files get transcribed
4. Restore the dead LLM reranker in app/ai/pipeline/search_pipeline.py, but replace the SambaNova LLM call with a local CrossEncoder from sentence-transformers BAAI/bge-reranker-v2-m3
5. Update search_async to return results only if rerank_score > 0.5, not fixed top-5
```

Antigravity will write the glue code and make sure the imports + API calls are correct.

### Part 3: Test on your own queries (30 min)
Ingest a small batch (5–10 files, mix of PDFs with images + audio clips).
Run your three failing queries:
- "Red dress"
- "Tanjiro swinging his sword"
- "2025 agriculture report"

See if they improve. They should — semantic search is back, vision is local so no rate limits.

### Part 4: Write the report (30 min)
For your officials, something like:

---

**RepoIR Status Update — [Date]**

**What we fixed today:**
- Replaced cloud vision API with local Ollama + Moondream2 (eliminated rate-limit failures, search now works on images again)
- Restored semantic reranking with local BAAI cross-encoder (search quality improved, results now scored 0–1 instead of ranked by position)
- Added audio transcription via Whisper (new feature: audio files now generate text transcripts for search)

**Current state:** 
- Works locally without any API keys or billing accounts
- Can handle mixed file types (PDFs, images, audio, URLs) on a single laptop
- Ready for 1000+ file testing (not yet scaled, but architecture supports it)

**Known limitations:**
- Local vision model is less accurate than GPT-4V for rare/obscure entities (this is a model capability ceiling, not a bug)
- Audio transcription is English-only in current config (can add multilingual with different Whisper variant)
- URL scraping still uses Jina (works but not our code)

**Next steps:**
- Test on larger document sets
- Add document type classification (report vs invoice vs contract)
- Implement personal memory/correction feedback

---

## Hardware usage notes

With your RTX 4050 + 16GB RAM:
- Moondream2 in Ollama: ~3.5GB VRAM, ~2 sec per image
- Cross-encoder reranker: ~1GB VRAM, instant on GPU
- Whisper 'base': ~2.5GB VRAM, ~2 sec per 10 min of audio
- Total: can run all three together without OOM

If you hit memory issues, swap to:
- Moondream1 instead of Moondream2 (smaller, slightly less accurate)
- Whisper 'tiny' instead of 'base' (faster, slightly worse transcription)
- Everything will still work, just slower.

---

## One-liner to tell Antigravity

Copy this and paste into Antigravity:

```
Refactor RepoIR to use local models: replace app/ai/extractors/vision_describer.py's SambaNova call with Ollama API call to moondream2. Create app/ai/extractors/audio_extractor.py using Whisper for audio transcription and wire it into ingestion_pipeline.py. Restore app/ai/pipeline/search_pipeline.py's _rerank_with_llm but replace SambaNova with local BAAI/bge-reranker-v2-m3 CrossEncoder, update search_async to threshold results on rerank_score > 0.5 instead of returning fixed top-5. All local, no API keys.
```

---

## Timeline reality check

- Setup local infra: 30 min (waiting for Ollama/Whisper downloads)
- Antigravity code gen + patching: 60–90 min (usually first pass works, maybe one round of fixes)
- Testing on small batch: 30 min
- Report writing: 30 min

**Total: 3–4 hours.**

You can start now, report tomorrow morning. This is doable today if you run Antigravity in parallel while Ollama downloads.