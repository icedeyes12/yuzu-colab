# Yuzu Memory Rebuild - Google Colab

🚀 **Run on Google Colab with FREE GPU!**

## Quick Start

1. Open: https://colab.research.google.com
2. Upload `yuzu_memory_colab.ipynb`
3. Set secrets (🔐 → Add secret):
   - `SUPABASE_URL` - Your Supabase project URL
   - `SUPABASE_KEY` - Your Supabase anon key
   - `HF_TOKEN` - HuggingFace token (for model download)
4. Run all cells (▶️ → Run all)

## What it does

```
Phase 1: Export    → Supabase → DuckDB (local)
Phase 2: Embed     → Generate embeddings (GPU accelerated!)
Phase 3: Migrate   → DuckDB → Supabase
```

## Requirements

- **FREE** Google Colab account
- **GPU** (Colab provides free GPU!)
- Supabase project (free tier works)

## Model

Uses `intfloat/multilingual-e5-large` (1024 dim)
- ~1.5GB download
- Fast on GPU

## Time Estimate

| Phase | Time |
|-------|------|
| Export | ~2 min |
| Embed (GPU) | ~10-15 min |
| Migrate | ~5 min |
| **Total** | ~20 min |
