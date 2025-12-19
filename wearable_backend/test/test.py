from chromadb import PersistentClient

chroma_client = PersistentClient(path="./chroma_data")

collection = chroma_client.get_or_create_collection(
    name="summaries", metadata={"hnsw:space": "cosine"}
)

data = collection.get()
data.keys()
data.keys()
data["ids"]
data["included"]

data["metadatas"][0]
data["documents"][:4]

collection.add(
    ids=["user_abc_20251204"],
    documents=[
        "User health activity record"
    ],
    metadatas=[{
        "user_id": "abc@aaaa.com",        # ✅ 이메일
        "created_at": "2025-12-04T01:29:58.169745+00:00",
        "sleep_min": 5993,
        "distance_km": 17.79,
        "steps": 112226,
        "heart_rate": 79
    }]
)
