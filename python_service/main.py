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

# ── Step 6: Hybrid Search (Dense + Sparse + RRF) ──
print("=" * 60)
query_text = "đại học xây dựng"
print(f'Step 6: Hybrid Search "{query_text}"...')

from knowledge_base.hybrid_retrievel import HybridRetriever

retriever = HybridRetriever()

results = retriever.search(query=query_text, n_results=5)

print(f"  → Mode: {results.mode}")
print(f"  → Dense results: {results.dense_count}")
print(f"  → Sparse results: {results.sparse_count}")
print(f"  → Final results (after RRF): {len(results.documents)}")

if results.is_empty:
    print("  ⚠ Không tìm thấy kết quả nào!")
else:
    for i, (doc_id, doc, meta, score) in enumerate(
        zip(results.ids, results.documents, results.metadatas, results.rrf_scores)
    ):
        print(f"\n  [{i+1}] ID: {doc_id}")
        print(f"      RRF Score: {score:.6f}")
        print(f"      Metadata: {meta}")
        print(f"      Content: {doc[:300]}...")

print("\n" + "=" * 60)
print("Done!")
