#!/usr/bin/env python3
"""
VectorDB 데이터 확인 스크립트 (환경변수 독립 버전)
ChromaDB에 저장된 데이터의 날짜, 출처, 플랫폼, 상세 내용을 확인합니다.
OpenAI API 없이 직접 ChromaDB에 접근합니다.
"""

import sys
import os
import json
from datetime import datetime

# 백엔드 경로 추가
sys.path.insert(0, os.path.abspath("."))

# ✅ .env 파일 로드 (선택적)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass
except Exception as e:
    pass

from app.core.vector_store import collection


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)


def format_data_value(key, value):
    """데이터 값 포맷팅"""
    if isinstance(value, (int, float)):
        if key in ["weight", "bmi", "body_fat", "lean_body"]:
            return f"{value:.1f}"
        elif key in ["distance_km"]:
            return f"{value:.2f} km"
        elif key in ["steps", "flights"]:
            return f"{value:,}"
        elif key in ["active_calories", "total_calories", "calories_intake"]:
            return f"{value} kcal"
        elif key in ["sleep_hr"]:
            return f"{value} 시간"
        elif key in ["sleep_min", "exercise_min"]:
            return f"{value} 분"
        else:
            return str(value)
    return str(value)


def get_date(user_id: str, date: str):
    """
    특정 날짜 데이터 조회 (함수로 제공)

    Args:
        user_id: 사용자 ID
        date: 날짜 (YYYY-MM-DD)

    Returns:
        dict: 데이터 딕셔너리 또는 None

    Usage:
        from check_vectordb import get_date
        data = get_date("user@example.com", "2025-12-16")
        print(data['summary_text'])
    """
    try:
        result = collection.get(where={"$and": [{"user_id": user_id}, {"date": date}]})

        if not result or not result["metadatas"]:
            return None

        metadata = result["metadatas"][0]
        summary_json = metadata.get("summary_json", "{}")

        try:
            summary_dict = json.loads(summary_json)
        except:
            summary_dict = {}

        return {
            "date": metadata.get("date"),
            "source": metadata.get("source"),
            "platform": metadata.get("platform"),
            "health_score": metadata.get("health_score"),
            "recommended_intensity": metadata.get("recommended_intensity"),
            "updated_at": metadata.get("updated_at"),
            "summary_text": summary_dict.get("summary_text", ""),
            "raw": summary_dict.get("raw", {}),
        }
    except Exception as e:
        print(f"[ERROR] {e}")
        return None


def view_specific_date(user_id: str, target_date: str):
    """특정 날짜 데이터 상세 출력"""
    print_header(f"🔍 특정 날짜 조회: {target_date}")

    data = get_date(user_id, target_date)

    if not data:
        print(f"\n⚠️ {target_date} 데이터가 없습니다!")
        return

    print(f"\n📅 날짜: {data['date']}\n")

    # 메타 정보
    print(f"📌 메타 정보:")
    print(f"   출처(Source):     {data['source']}")
    print(f"   플랫폼(Platform): {data['platform']}")
    print(f"   업데이트:         {data['updated_at']}")
    print(f"   건강 점수:        {data['health_score']}점")
    print(f"   권장 강도:        {data['recommended_intensity']}\n")

    # 요약
    if data["summary_text"]:
        print(f"📝 요약:")
        print(f"   {data['summary_text']}\n")

    # 상세 데이터 (0이 아닌 값만)
    raw = data["raw"]
    if raw:
        print(f"📊 상세 데이터 (0이 아닌 값만):\n")

        has_data = False
        for key, value in sorted(raw.items()):
            if value and value != 0:
                has_data = True
                formatted_value = format_data_value(key, value)
                print(f"   {key:25s}: {formatted_value}")

        if not has_data:
            print("   (모든 값이 0입니다)")

    print(f"\n{'='*100}\n")


def view_all_data(show_summary=False):
    """VectorDB의 모든 데이터 확인 (출처 및 플랫폼 포함)"""
    print_header("🔍 VectorDB 전체 데이터 조회")

    try:
        count = collection.count()
        print(f"\n📊 총 저장된 데이터: {count}개\n")

        if count == 0:
            print("⚠️ VectorDB에 데이터가 없습니다!")
            return

        # 모든 데이터 가져오기
        all_data = collection.get()

        # 사용자별 그룹화
        user_data = {}
        for metadata in all_data["metadatas"]:
            user_id = metadata.get("user_id", "unknown")
            if user_id not in user_data:
                user_data[user_id] = []
            user_data[user_id].append(metadata)

        # 사용자별 출력
        for user_id, data_list in user_data.items():
            print(f"\n👤 User: {user_id}")
            print(f"   데이터 개수: {len(data_list)}개\n")

            # 날짜별 정렬
            sorted_data = sorted(
                data_list, key=lambda x: x.get("date", ""), reverse=True
            )

            # 날짜별 그룹화 (같은 날짜 여러 건 확인)
            date_groups = {}
            for item in sorted_data:
                date = item.get("date", "unknown")
                if date not in date_groups:
                    date_groups[date] = []
                date_groups[date].append(item)

            # 날짜별 출력 (최대 20개만)
            displayed = 0
            for date, items in list(date_groups.items())[:20]:
                if len(items) == 1:
                    item = items[0]
                    source = item.get("source", "unknown")
                    platform = item.get("platform", "unknown")
                    score = item.get("health_score", 0)
                    updated = item.get("updated_at", "")

                    print(f"   📅 {date}")
                    print(
                        f"      출처: {source:15s} | 플랫폼: {platform:8s} | 건강점수: {score}점 | 업데이트: {updated}"
                    )
                else:
                    # 같은 날짜에 여러 건
                    print(f"   📅 {date} ⚠️ 중복 {len(items)}건:")
                    for idx, item in enumerate(items, 1):
                        source = item.get("source", "unknown")
                        platform = item.get("platform", "unknown")
                        score = item.get("health_score", 0)
                        updated = item.get("updated_at", "")
                        print(
                            f"      [{idx}] 출처: {source:15s} | 플랫폼: {platform:8s} | 건강점수: {score}점 | 업데이트: {updated}"
                        )

                displayed += 1

            if len(date_groups) > 20:
                print(f"\n   ... 외 {len(date_groups) - 20}개 날짜")

            if show_summary:
                print(
                    f"\n   💡 상세 보기: python check_vectordb.py --user {user_id} --detail"
                )

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def view_user_data(user_id: str, detailed=False, show_all_fields=False):
    """특정 사용자의 데이터 상세 조회 (출처 및 플랫폼 포함) - OpenAI API 불필요"""
    print_header(f"🔍 User '{user_id}' 데이터 상세 조회")

    try:
        # ✅ OpenAI API 없이 직접 조회
        all_data = collection.get(where={"user_id": user_id})

        if not all_data or not all_data["metadatas"]:
            print("\n⚠️ 데이터가 없습니다!")
            return

        metadatas = all_data["metadatas"]
        print(f"\n📊 총 {len(metadatas)}개 데이터\n")

        # 날짜별 정렬
        sorted_data = sorted(metadatas, key=lambda x: x.get("date", ""), reverse=True)

        for i, metadata in enumerate(sorted_data, 1):
            date = metadata.get("date", "unknown")
            source = metadata.get("source", "unknown")
            platform = metadata.get("platform", "unknown")
            updated = metadata.get("updated_at", "")
            health_score = metadata.get("health_score", 0)
            intensity = metadata.get("recommended_intensity", "중")

            # summary_json 파싱
            summary_json = metadata.get("summary_json", "{}")
            try:
                summary_dict = json.loads(summary_json)
            except:
                summary_dict = {}

            raw = summary_dict.get("raw", {})
            summary_text = summary_dict.get("summary_text", "")

            print(f"\n{'='*100}")
            print(f"📅 [{i}] 날짜: {date}")
            print(f"{'='*100}")

            # ✅ 메타 정보
            print(f"\n📌 메타 정보:")
            print(f"   출처(Source):     {source}")
            print(f"   플랫폼(Platform): {platform}")
            print(f"   업데이트:         {updated}")
            print(f"   건강 점수:        {health_score}점")
            print(f"   권장 강도:        {intensity}")

            # 요약 텍스트
            if summary_text:
                print(f"\n📝 요약:")
                if len(summary_text) > 200:
                    print(f"   {summary_text[:200]}...")
                else:
                    print(f"   {summary_text}")

            if detailed and raw:
                # 상세 데이터 출력
                print(f"\n📊 상세 데이터 ({len(raw)}개 항목):")

                if show_all_fields:
                    # 모든 필드 출력
                    for key, value in sorted(raw.items()):
                        formatted_value = format_data_value(key, value)
                        print(f"   {key:25s}: {formatted_value}")
                else:
                    # 주요 필드만 출력
                    key_fields = [
                        "sleep_hr",
                        "sleep_min",
                        "steps",
                        "distance_km",
                        "active_calories",
                        "heart_rate",
                        "resting_heart_rate",
                        "weight",
                        "bmi",
                        "exercise_min",
                    ]

                    available_fields = [k for k in key_fields if k in raw]
                    other_fields = [k for k in raw.keys() if k not in key_fields]

                    if available_fields:
                        print("\n   📌 주요 지표:")
                        for key in available_fields:
                            value = raw[key]
                            if value and value != 0:  # 0이 아닌 값만 표시
                                formatted_value = format_data_value(key, value)
                                print(f"      {key:25s}: {formatted_value}")

                    if other_fields:
                        non_zero_others = [
                            k for k in other_fields if raw.get(k) and raw.get(k) != 0
                        ]
                        if non_zero_others:
                            print(
                                f"\n   💡 기타 {len(non_zero_others)}개 항목: {', '.join(non_zero_others[:5])}..."
                            )
                            print(f"      (전체 보기: --all-fields 옵션 사용)")

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def check_duplicates(user_id: str = None):
    """같은 날짜 중복 데이터 확인"""
    print_header("🔍 중복 데이터 확인")

    try:
        all_data = collection.get()

        if user_id:
            # 특정 사용자만 필터링
            filtered_metadatas = [
                m for m in all_data["metadatas"] if m.get("user_id") == user_id
            ]
        else:
            filtered_metadatas = all_data["metadatas"]

        # 날짜별 그룹화
        date_groups = {}
        for metadata in filtered_metadatas:
            uid = metadata.get("user_id", "unknown")
            date = metadata.get("date", "unknown")
            key = f"{uid}_{date}"

            if key not in date_groups:
                date_groups[key] = []
            date_groups[key].append(metadata)

        # 중복 찾기
        duplicates = {k: v for k, v in date_groups.items() if len(v) > 1}

        if not duplicates:
            print("\n✅ 중복 데이터 없음!")
            return

        print(f"\n⚠️ 총 {len(duplicates)}개 날짜에 중복 데이터 발견:\n")

        for key, items in duplicates.items():
            user_id, date = key.split("_", 1)
            print(f"\n👤 User: {user_id} | 📅 날짜: {date} | 중복: {len(items)}건")

            for idx, item in enumerate(items, 1):
                source = item.get("source", "unknown")
                platform = item.get("platform", "unknown")
                updated = item.get("updated_at", "")
                score = item.get("health_score", 0)
                print(
                    f"   [{idx}] 출처: {source:15s} | 플랫폼: {platform:8s} | 건강점수: {score}점 | 업데이트: {updated}"
                )

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def check_chroma_location():
    """ChromaDB 저장 위치 확인"""
    print_header("📁 ChromaDB 저장 위치 확인")

    try:
        chroma_dir = "./chroma_data"
        abs_path = os.path.abspath(chroma_dir)

        print(f"\n경로: {abs_path}")

        if os.path.exists(abs_path):
            print(f"상태: ✅ 존재함")

            # 디렉토리 크기
            total_size = 0
            file_count = 0
            for root, dirs, files in os.walk(abs_path):
                for file in files:
                    file_path = os.path.join(root, file)
                    total_size += os.path.getsize(file_path)
                    file_count += 1

            print(f"파일: {file_count}개")
            print(
                f"크기: {total_size / 1024:.2f} KB ({total_size / (1024*1024):.2f} MB)"
            )
        else:
            print(f"상태: ❌존재하지 않음")

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")


def show_date_range(user_id: str = None):
    """날짜 범위 확인"""
    print_header("📅 날짜 범위 확인")

    try:
        if user_id:
            all_data = collection.get(where={"user_id": user_id})
        else:
            all_data = collection.get()

        metadatas = all_data.get("metadatas", [])

        if not metadatas:
            print("\n⚠️ 데이터가 없습니다!")
            return

        dates = [m.get("date") for m in metadatas if m.get("date")]
        dates = sorted(set(dates))

        if dates:
            print(f"\n📊 총 {len(dates)}개 날짜")
            print(f"📅 범위: {dates[0]} ~ {dates[-1]}")
            print(f"\n최근 10개 날짜:")
            for date in dates[-10:]:
                date_items = [m for m in metadatas if m.get("date") == date]
                sources = set([m.get("source", "unknown") for m in date_items])
                platforms = set([m.get("platform", "unknown") for m in date_items])
                print(
                    f"   {date} | 건수: {len(date_items)} | 출처: {', '.join(sources)} | 플랫폼: {', '.join(platforms)}"
                )

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="VectorDB 데이터 확인 (출처 및 플랫폼 정보 포함)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python check_vectordb.py --all                          # 전체 데이터 요약
  python check_vectordb.py --user a@aaa.com               # 특정 사용자 데이터
  python check_vectordb.py --user a@aaa.com --detail      # 상세 정보
  python check_vectordb.py --user a@aaa.com --detail --all-fields  # 모든 필드
  python check_vectordb.py --date 2025-12-16 --user a@aaa.com      # 특정 날짜
  python check_vectordb.py --duplicates                   # 중복 데이터 확인
  python check_vectordb.py --dates                        # 날짜 범위 확인
  python check_vectordb.py --location                     # ChromaDB 위치

Python 인터프리터에서 사용:
  from check_vectordb import get_date
  data = get_date("user@example.com", "2025-12-16")
  print(data['summary_text'])
        """,
    )

    parser.add_argument("--all", action="store_true", help="전체 데이터 요약 보기")
    parser.add_argument("--user", type=str, help="특정 사용자 데이터 확인")
    parser.add_argument("--date", type=str, help="특정 날짜 조회 (YYYY-MM-DD)")
    parser.add_argument("--detail", action="store_true", help="상세 정보 보기")
    parser.add_argument(
        "--all-fields", action="store_true", help="모든 데이터 필드 보기"
    )
    parser.add_argument("--duplicates", action="store_true", help="중복 데이터 확인")
    parser.add_argument("--dates", action="store_true", help="날짜 범위 확인")
    parser.add_argument("--location", action="store_true", help="ChromaDB 위치 확인")

    args = parser.parse_args()

    if args.date and args.user:
        # 특정 날짜 조회
        view_specific_date(args.user, args.date)
    elif args.all:
        view_all_data(show_summary=True)
    elif args.user:
        view_user_data(args.user, detailed=args.detail, show_all_fields=args.all_fields)
    elif args.duplicates:
        check_duplicates()
    elif args.dates:
        show_date_range()
    elif args.location:
        check_chroma_location()
    else:
        # 기본: 전체 요약
        check_chroma_location()
        print()
        view_all_data(show_summary=True)
