import sys
import os
os.environ["PYTHONIOENCODING"] = "utf-8"
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from knowledge_base.vector_store import VectorStore
from knowledge_base.embed import Embedder
from knowledge_base.document_loader import LoaderRegistry


# ── Step 1: Khởi tạo các components ──
print("=" * 60)
print("Step 1: Khởi tạo VectorStore, Embedder, Loader...")
vector_store = VectorStore()
embedder = Embedder()
loader = LoaderRegistry.get_loader(".pdf")
print(f"  → Collection hiện có: {vector_store.count()} documents")

# ── Step 2: Load PDF thành chunks ──
print("=" * 60)
print("Step 2: Load PDF → chunks...")
documents = loader.load("data.pdf")
print(f"  → Loaded {len(documents)} chunks từ data.pdf")

# ── Step 3: Chuẩn bị dữ liệu để add vào ChromaDB ──
print("=" * 60)
print("Step 3: Chuẩn bị dữ liệu...")
ids = [doc.doc_id for doc in documents]
contents = [doc.content for doc in documents]
metadatas = [doc.metadata for doc in documents]

# ── Step 4: Embed tất cả chunks ──
print("=" * 60)
print("Step 4: Embedding chunks...")
embeddings = embedder.embed_batch(contents)
print(f"  → Embedded {len(embeddings)} vectors ({len(embeddings[0])}D each)")

# ── Step 5: Add vào ChromaDB ──
print("=" * 60)
print("Step 5: Add documents vào ChromaDB...")
vector_store.add_documents(
    ids=ids,
    documents=contents,
    metadatas=metadatas,
    embeddings=embeddings,
)
print(f"  → Tổng documents trong ChromaDB: {vector_store.count()}")

# ── Step 6: Query thử ──
print("=" * 60)
query_text = "đại học xây dựng"
print(f'Step 6: Query "{query_text}"...')
query_embedding = embedder.embed(query_text)
results = vector_store.query(query_embedding=query_embedding, n_results=5)

print(f"  → Tìm thấy {len(results.documents)} kết quả:")
for i, (doc_id, doc, dist) in enumerate(zip(results.ids, results.documents, results.distances)):
    print(f"\n  [{i+1}] ID: {doc_id}")
    print(f"      Distance: {dist:.4f}")
    print(f"      Content: {doc[:200]}...")

print("\n" + "=" * 60)
print("Done!")