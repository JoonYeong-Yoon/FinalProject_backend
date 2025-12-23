"""
VectorDB 중복 방지 + 검색 개선 버전
- 같은 날짜, 같은 출처의 데이터는 덮어쓰기
- 검색 시 같은 날짜 중복 제거 + 최신 날짜 우선 정렬
- 날짜 필터링 함수 추가 (개선)
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
# 6) 유사 Summary 검색 (개선: 중복 제거 + 최신 우선)
# ------------------------------------------------
def search_similar_summaries(query_dict: dict, user_id: str, top_k: int = 3) -> dict:
    """
    유사한 과거 Summary 검색 (개선 버전)

    개선 사항:
    1. 같은 날짜에 여러 데이터가 있으면 updated_at이 최신인 것만 유지
    2. 결과를 최신 날짜순으로 정렬
    3. top_k 개수만큼 반환
    """
    try:
        query_parts = []
        for k, v in query_dict.items():
            if v:
                query_parts.append(f"{k}: {v}")

        query_text = ", ".join(query_parts) if query_parts else "health summary"

        query_embedding = get_cached_embedding(query_text)

        # 더 많이 가져와서 중복 제거 후 top_k 반환
        fetch_count = max(top_k * 3, 10)

        results = collection.query(
            query_embeddings=[query_embedding],
            n_results=fetch_count,
            where={"user_id": user_id},
        )

        # 1단계: 결과 파싱
        raw_results = []
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

                raw_results.append(
                    {
                        "document_id": doc_id,
                        "user_id": metadata.get("user_id"),
                        "date": metadata.get("date"),
                        "timestamp": metadata.get("timestamp", 0),
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

        # 2단계: 같은 날짜 중복 제거 (updated_at 최신 유지)
        deduplicated = _deduplicate_by_date(raw_results)

        # 3단계: 최신 날짜순 정렬
        sorted_results = sorted(
            deduplicated,
            key=lambda x: (x.get("timestamp", 0), x.get("updated_at", "")),
            reverse=True,
        )

        # 4단계: top_k 개수만큼 반환
        similar_days = sorted_results[:top_k]

        return {"similar_days": similar_days, "query": query_text}

    except Exception as e:
        print(f"[ERROR] VectorDB 검색 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return {"similar_days": [], "query": query_dict, "error": str(e)}


def _deduplicate_by_date(results: list) -> list:
    """
    같은 날짜의 데이터가 여러 개면 updated_at이 최신인 것만 유지

    Args:
        results: 검색 결과 리스트

    Returns:
        중복 제거된 리스트
    """
    if not results:
        return []

    # 날짜별로 그룹화
    date_groups = {}
    for item in results:
        date = item.get("date", "")
        if not date:
            continue

        if date not in date_groups:
            date_groups[date] = []
        date_groups[date].append(item)

    # 각 날짜에서 최신 데이터만 선택
    deduplicated = []
    for date, items in date_groups.items():
        if len(items) == 1:
            deduplicated.append(items[0])
        else:
            # updated_at 기준 최신 선택
            latest = max(items, key=lambda x: x.get("updated_at", ""))
            deduplicated.append(latest)

            # 로그 출력 (디버깅용)
            sources = [
                f"{i.get('source')}({i.get('updated_at', '')[:8]})" for i in items
            ]
            print(f"[INFO] {date} 중복 제거: {sources} → {latest.get('source')}")

    return deduplicated


# ------------------------------------------------
# 7) 최신 데이터 조회 (고정형 챗봇용)
# ------------------------------------------------
def get_recent_summaries(user_id: str, limit: int = 7) -> list:
    """
    최신 날짜순으로 데이터 조회 (유사도 검색 없이)
    고정형 챗봇의 주간 리포트 등에 사용

    Args:
        user_id: 사용자 ID
        limit: 가져올 개수 (기본 7일)

    Returns:
        최신 날짜순 정렬된 summary 리스트
    """
    try:
        # 전체 데이터 조회 (해당 사용자)
        results = collection.get(
            where={"user_id": user_id},
            include=["metadatas", "documents"],
        )

        if not results or not results["ids"]:
            return []

        # 파싱
        all_items = _parse_collection_results(results)

        # 중복 제거
        deduplicated = _deduplicate_by_date(all_items)

        # 최신 날짜순 정렬
        sorted_items = sorted(
            deduplicated,
            key=lambda x: (x.get("timestamp", 0), x.get("updated_at", "")),
            reverse=True,
        )

        return sorted_items[:limit]

    except Exception as e:
        print(f"[ERROR] 최신 데이터 조회 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return []


# ------------------------------------------------
# 8) 특정 날짜 데이터 조회 (NEW)
# ------------------------------------------------
def get_summaries_by_date(user_id: str, target_date: str) -> list:
    """
    특정 날짜의 데이터 조회

    Args:
        user_id: 사용자 ID
        target_date: YYYY-MM-DD 형식

    Returns:
        해당 날짜의 summary 리스트
    """
    try:
        # timestamp 변환 (YYYYMMDD 정수)
        target_timestamp = int(target_date.replace("-", ""))

        results = collection.get(
            where={"$and": [{"user_id": user_id}, {"timestamp": target_timestamp}]},
            include=["metadatas", "documents"],
        )

        if not results or not results["ids"]:
            return []

        # 파싱
        all_items = _parse_collection_results(results)

        # 중복 제거 (같은 날짜에 여러 소스가 있을 수 있음)
        deduplicated = _deduplicate_by_date(all_items)

        return deduplicated

    except Exception as e:
        print(f"[ERROR] 특정 날짜 데이터 조회 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return []


# ------------------------------------------------
# 9) 날짜 범위 데이터 조회 (NEW)
# ------------------------------------------------
def get_summaries_by_date_range(user_id: str, start_date: str, end_date: str) -> list:
    """
    날짜 범위 내 데이터 조회

    Args:
        user_id: 사용자 ID
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)

    Returns:
        해당 기간의 summary 리스트 (최신순 정렬)
    """
    try:
        # timestamp 변환 (YYYYMMDD 정수)
        start_timestamp = int(start_date.replace("-", ""))
        end_timestamp = int(end_date.replace("-", ""))

        results = collection.get(
            where={
                "$and": [
                    {"user_id": user_id},
                    {"timestamp": {"$gte": start_timestamp}},
                    {"timestamp": {"$lte": end_timestamp}},
                ]
            },
            include=["metadatas", "documents"],
        )

        if not results or not results["ids"]:
            return []

        # 파싱
        all_items = _parse_collection_results(results)

        # 중복 제거
        deduplicated = _deduplicate_by_date(all_items)

        # 최신순 정렬
        sorted_items = sorted(
            deduplicated,
            key=lambda x: (x.get("timestamp", 0), x.get("updated_at", "")),
            reverse=True,
        )

        return sorted_items

    except Exception as e:
        print(f"[ERROR] 날짜 범위 데이터 조회 실패: {str(e)}")
        import traceback

        traceback.print_exc()
        return []


# ------------------------------------------------
# 10) 공통 파싱 함수 (NEW)
# ------------------------------------------------
def _parse_collection_results(results: dict) -> list:
    """
    ChromaDB 결과를 통일된 포맷으로 파싱

    Args:
        results: collection.get() 결과

    Returns:
        파싱된 리스트
    """
    all_items = []

    for i in range(len(results["ids"])):
        doc_id = results["ids"][i]
        metadata = results["metadatas"][i]

        summary_json = metadata.get("summary_json", "{}")
        try:
            summary_dict = json.loads(summary_json)
        except:
            summary_dict = {}

        raw = summary_dict.get("raw", {})
        summary_text = summary_dict.get("summary_text", "")

        all_items.append(
            {
                "document_id": doc_id,
                "user_id": metadata.get("user_id"),
                "date": metadata.get("date"),
                "timestamp": metadata.get("timestamp", 0),
                "health_score": metadata.get("health_score"),
                "recommended_intensity": metadata.get("recommended_intensity"),
                "source": metadata.get("source", "unknown"),
                "platform": metadata.get("platform", "unknown"),
                "updated_at": metadata.get("updated_at", ""),
                "raw": raw,
                "summary_text": summary_text,
            }
        )

    return all_items
