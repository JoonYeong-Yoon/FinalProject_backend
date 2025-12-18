"""
VectorDB 중복 방지 개선 버전
같은 날짜, 같은 출처의 데이터는 덮어쓰기
"""

import os, json, chromadb
from chromadb import PersistentClient
from openai import OpenAI
from datetime import datetime
from app.utils.preprocess_for_embedding import summary_to_natural_text
from app.core.health_interpreter import (
    calculate_health_score,
    recommend_exercise_intensity,
)


# ------------------------------------------------
# 1) OpenAI Client
# ------------------------------------------------
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("❌ OPENAI_API_KEY가 설정되지 않았습니다.")
    return OpenAI(api_key=api_key)


# ------------------------------------------------
# 2) ChromaDB Client
# ------------------------------------------------
chroma_client = PersistentClient(path="./chroma_data")

collection = chroma_client.get_or_create_collection(
    name="summaries", metadata={"hnsw:space": "cosine"}
)


# ------------------------------------------------
# 3) 임베딩 + 캐싱
# ------------------------------------------------
embedding_cache = {}


def embed_text(text: str):
    """단일 텍스트 임베딩"""
    if not text or not text.strip():
        text = "데이터 없음"

    if len(text) > 8000:
        text = text[:8000]

    client = get_openai_client()
    response = client.embeddings.create(input=text, model="text-embedding-3-small")
    return response.data[0].embedding


def get_cached_embedding(text: str):
    """캐시된 임베딩 반환"""
    if text not in embedding_cache:
        embedding_cache[text] = embed_text(text)
    return embedding_cache[text]


def batch_embed_texts(texts: list[str]):
    """배치 임베딩"""
    if not texts:
        return []

    processed_texts = []
    for text in texts:
        if not text or not text.strip():
            processed_texts.append("데이터 없음")
        elif len(text) > 8000:
            processed_texts.append(text[:8000])
        else:
            processed_texts.append(text)

    client = get_openai_client()
    response = client.embeddings.create(
        input=processed_texts, model="text-embedding-3-small"
    )

    return [item.embedding for item in response.data]


# ------------------------------------------------
# 4) Summary 단일 저장 (중복 방지!)
# ------------------------------------------------
def save_daily_summary(summary: dict, user_id: str, source: str = "api"):
    """
    단일 요약 데이터를 VectorDB에 저장 (중복 방지 개선!)

    개선 사항:
    - doc_id에서 timestamp 제거 → 같은 날짜/출처는 덮어쓰기
    - upsert 사용으로 자동 중복 방지
    """
    raw = summary.get("raw", {})

    health_score = calculate_health_score(raw)
    intensity = recommend_exercise_intensity(raw)

    created_at = summary.get("created_at")
    if not created_at:
        raise ValueError("❌ summary['created_at']가 존재하지 않습니다.")

    date = created_at[:10]  # yyyy-mm-dd
    platform = summary.get("platform", "unknown")

    # ✅ 개선: timestamp 제거 - 중복 방지!
    # 같은 날짜, 같은 출처는 하나만 저장
    doc_id = f"{user_id}_{date}_{source}"
    # 예: "user_1@aaa.com_2024-10-01_zip_samsung"

    # Natural embedding 텍스트 생성
    embedding_text = summary_to_natural_text(summary)

    # 임베딩 생성
    embedding = get_cached_embedding(embedding_text)

    # Metadata 준비
    try:
        summary_json = json.dumps(summary, ensure_ascii=False)
    except Exception as e:
        print(f"[WARN] Summary JSON 직렬화 실패: {e}")
        summary_json = str(summary)

    # 현재 시간 (업데이트 시간)
    update_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    metadata = {
        "user_id": user_id,
        "date": date,
        "timestamp": int(date.replace("-", "")),
        "health_score": health_score.get("score", 0),
        "recommended_intensity": intensity.get("recommended_level", "중"),
        "fallback": False,
        "summary_json": summary_json,
        "source": source,
        "platform": platform,
        "updated_at": update_timestamp,  # ✅ 마지막 업데이트 시간
    }

    # ✅ upsert: 같은 doc_id면 덮어쓰기, 없으면 추가
    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[embedding_text],
        metadatas=[metadata],
    )

    print(f"[INFO] VectorDB 저장: {doc_id} (플랫폼: {platform})")

    return {
        "status": "saved",
        "document_id": doc_id,
        "date": date,
        "user_id": user_id,
        "source": source,
        "platform": platform,
    }


# ------------------------------------------------
# 5) Summary 배치 저장 (중복 방지!)
# ------------------------------------------------
def save_daily_summaries_batch(
    summaries: list[dict], user_id: str, source: str = "zip"
):
    """
    여러 요약 데이터를 한 번에 VectorDB에 저장 (중복 방지 개선!)
    """
    if not summaries:
        print("[WARN] summaries가 비어 있어서 저장하지 않습니다.")
        return {"status": "skipped", "reason": "empty summaries"}

    ids = []
    embeddings_list = []
    documents = []
    metadatas = []
    embedding_texts = []

    update_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

    # 1단계: 데이터 준비
    for summary in summaries:
        raw = summary.get("raw", {})
        health_score = calculate_health_score(raw)
        intensity = recommend_exercise_intensity(raw)

        created_at = summary.get("created_at")
        if not created_at:
            print(f"[WARN] summary에 created_at이 없어서 건너뜁니다")
            continue

        date = created_at[:10]
        platform = summary.get("platform", "unknown")

        # ✅ 개선: timestamp 제거 - 중복 방지!
        doc_id = f"{user_id}_{date}_{source}"
        ids.append(doc_id)

        # Natural embedding 텍스트
        embedding_text = summary_to_natural_text(summary)
        embedding_texts.append(embedding_text)
        documents.append(embedding_text)

        # Metadata
        try:
            summary_json = json.dumps(summary, ensure_ascii=False)
        except Exception as e:
            print(f"[WARN] Summary JSON 직렬화 실패: {e}")
            summary_json = str(summary)

        metadata = {
            "user_id": user_id,
            "date": date,
            "timestamp": int(date.replace("-", "")),
            "health_score": health_score.get("score", 0),
            "recommended_intensity": intensity.get("recommended_level", "중"),
            "fallback": False,
            "summary_json": summary_json,
            "source": source,
            "platform": platform,
            "updated_at": update_timestamp,
        }
        metadatas.append(metadata)

    if not ids:
        print("[WARN] 유효한 summary가 없어서 저장하지 않습니다.")
        return {"status": "skipped", "reason": "no valid summaries"}

    # 2단계: 배치 임베딩 생성
    print(f"[INFO] 배치 임베딩 생성 중... ({len(embedding_texts)}개)")
    embeddings_list = batch_embed_texts(embedding_texts)

    # 3단계: ChromaDB에 한 번에 저장 (upsert로 중복 방지)
    print(f"[INFO] ChromaDB에 {len(ids)}개 데이터 저장 중...")
    collection.upsert(
        ids=ids,
        embeddings=embeddings_list,
        documents=documents,
        metadatas=metadatas,
    )

    # ✅ 중복 체크
    unique_dates = len(set([m["date"] for m in metadatas]))
    print(f"[SUCCESS] {len(ids)}개 데이터 VectorDB 저장 완료")
    print(
        f"[INFO] 고유 날짜: {unique_dates}개 (플랫폼: {metadatas[0].get('platform', 'unknown')})"
    )

    return {
        "status": "batch_saved",
        "count": len(ids),
        "unique_dates": unique_dates,
        "user_id": user_id,
        "source": source,
    }


# ------------------------------------------------
# 6) 유사 Summary 검색
# ------------------------------------------------
def search_similar_summaries(query_dict: dict, user_id: str, top_k: int = 3) -> dict:
    """유사한 과거 Summary 검색"""
    try:
        query_parts = []
        for k, v in query_dict.items():
            if v:
                query_parts.append(f"{k}: {v}")

        query_text = ", ".join(query_parts) if query_parts else "health summary"

        query_embedding = get_cached_embedding(query_text)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"user_id": user_id},
        )

        similar_days = []
        if results and results["ids"] and len(results["ids"][0]) > 0:
            for i in range(len(results["ids"][0])):
                doc_id = results["ids"][0][i]
                metadata = results["metadatas"][0][i]
                distance = (
                    results["distances"][0][i] if "distances" in results else None
                )

                summary_json = metadata.get("summary_json", "{}")
                try:
                    summary_dict = json.loads(summary_json)
                except:
                    summary_dict = {}

                raw = summary_dict.get("raw", {})
                summary_text = summary_dict.get("summary_text", "")

                similar_days.append(
                    {
                        "document_id": doc_id,
                        "user_id": metadata.get("user_id"),
                        "date": metadata.get("date"),
                        "health_score": metadata.get("health_score"),
                        "recommended_intensity": metadata.get("recommended_intensity"),
                        "source": metadata.get("source", "unknown"),
                        "platform": metadata.get("platform", "unknown"),
                        "updated_at": metadata.get("updated_at", ""),
                        "raw": raw,
                        "summary_text": summary_text,
                        "similarity_distance": distance,
                    }
                )

        return {"similar_days": similar_days, "query": query_text}

    except Exception as e:
        print(f"[ERROR] VectorDB 검색 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"similar_days": [], "query": query_dict, "error": str(e)}
