# Yuzu Memory Rebuild - Colab Script
# ======================================
# Copy & Paste ke Colab cell-by-cell

# ===== CELL 1: SETUP =====
from google.colab import userdata
import os

SUPABASE_URL = userdata.get('SUPABASE_URL')
SUPABASE_KEY = userdata.get('SUPABASE_KEY')
os.environ['SUPABASE_URL'] = SUPABASE_URL
os.environ['SUPABASE_KEY'] = SUPABASE_KEY
print(f"✅ Supabase: {SUPABASE_URL[:30]}...")

# ===== CELL 2: INSTALL =====
!pip install -q duckdb psycopg2-binary sentence-transformers numpy pandas tqdm

# ===== CELL 3: MODEL =====
from sentence_transformers import SentenceTransformer
import torch

device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Device: {device}")

MODEL_NAME = "intfloat/multilingual-e5-base"
EMBEDDING_DIM = 768
model = SentenceTransformer(MODEL_NAME, device=device)
print(f"✅ Model: {MODEL_NAME} ({EMBEDDING_DIM} dims)")

# ===== CELL 4: PULL =====
import psycopg2
import pandas as pd
import duckdb

conn = psycopg2.connect(SUPABASE_URL, sslmode='require')
query = """
  SELECT m.id, m.session_id, m.role, m.content, m.created_at, cs.title
  FROM messages m
  JOIN chat_sessions cs ON m.session_id = cs.id
  WHERE cs.user_id = 1
  ORDER BY m.created_at DESC
"""
df = pd.read_sql(query, conn)
print(f"📥 Pulled {len(df)} messages")
conn.close()

# ===== CELL 5: SAVE LOCAL =====
local_db = duckdb.connect("yuzu_memories.duckdb")

local_db.execute("""
  CREATE TABLE IF NOT EXISTS messages_raw (
    id INTEGER, session_id INTEGER, role VARCHAR,
    content TEXT, created_at TIMESTAMP, session_title VARCHAR
  )
""")

local_db.execute("DELETE FROM messages_raw")
for _, row in df.iterrows():
  local_db.execute(
    "INSERT INTO messages_raw VALUES (?, ?, ?, ?, ?, ?)",
    [row.id, row.session_id, row.role, row.content, row.created_at, row.title]
  )
print(f"💾 Saved {len(df)} messages to local DuckDB")

# ===== CELL 6: EMBED =====
messages = local_db.execute("""
  SELECT id, session_id, role, content, created_at
  FROM messages_raw WHERE length(content) > 10
""").fetchall()
print(f"🧠 Processing {len(messages)} messages...")

batch_size = 32
for i in range(0, len(messages), batch_size):
  batch = messages[i:i+batch_size]
  texts = [m[3] for m in batch]
  embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
  
  for j, emb in enumerate(embeddings):
    msg = batch[j]
    local_db.execute(
      "INSERT INTO memories VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
      [msg[0], 1, msg[1], msg[2], list(emb), 'episodic', 50, msg[4]]
    )
  
  if (i + batch_size) % 1000 == 0:
    print(f"  Progress: {i + batch_size}/{len(messages)}")

mem_count = local_db.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
print(f"✅ Embedded {mem_count} memories")

# ===== CELL 7: PUSH =====
conn = psycopg2.connect(SUPABASE_URL, sslmode='require')
cur = conn.cursor()

memories = local_db.execute("SELECT * FROM memories").fetchall()
print(f"📤 Pushing {len(memories)} memories...")

batch_size = 100
for i in range(0, len(memories), batch_size):
  batch = memories[i:i+batch_size]
  args = []
  for m in batch:
    emb_list = list(m[4]) if not isinstance(m[4], list) else m[4]
    args.extend([m[0], m[1], m[2], m[3], emb_list, m[5], m[6]])
  
  values = ','.join(['(%s,%s,%s,%s,%s::vector(768),%s,%s)'] * len(batch))
  cur.execute(f"""
    INSERT INTO memories (id, user_id, session_id, content, embedding, memory_type, importance)
    VALUES {values}
    ON CONFLICT DO NOTHING
  """, args)
  conn.commit()
  print(f"  Pushed {min(i+batch_size, len(memories))}/{len(memories)}")

cur.close()
conn.close()
print("🎉 Done!")
