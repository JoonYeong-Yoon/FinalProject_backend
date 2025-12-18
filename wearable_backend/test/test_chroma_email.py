# test_chroma_email.py
import json
from chromadb import PersistentClient
from openai import OpenAI

# === 1) Chroma Client 로드 ===
client = PersistentClient(path="./chroma_data")

collection = client.get_or_create_collection(
    name="summaries",
    metadata={"hnsw:space": "cosine"}
)

# === 2) OpenAI Embedding 설정 ===
def embed(text: str):
    client = OpenAI()
    emb = client.embeddings.create(
        model="text-embedding-3-large",
        input=text
    )
    return emb.data[0].embedding


# === 3) 테스트 데이터 ===
user_email = "testuser@example.com"
sample_summary = {
    "steps": 12345,
    "calories": 321,
    "distance": 10.2,
    "timestamp": "2025-12-02T10:00:00"
}

doc_text = json.dumps(sample_summary, ensure_ascii=False)
vector = embed(doc_text)

# === 4) 저장 ===
collection.add(
    ids=[f"{user_email}_summary_test"],
    embeddings=[vector],
    metadatas=[{"user_id": user_email}],
    documents=[doc_text]
)

print("저장 완료!")

# === 5) 쿼리 테스트 ===
query_vec = embed("걸음 수 12000 정도의 활동")

result = collection.query(
    query_embeddings=[query_vec],
    where={"user_id": user_email},   # ← 이메일 필터가 핵심
    n_results=3
)

print("\n=== 검색 결과 ===")
for idx, doc in enumerate(result["documents"][0]):
    print(f"{idx+1}. {doc}")

