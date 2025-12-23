#!/usr/bin/env python3
"""
데이터 검사 통합 스크립트 (VectorDB + ZIP 분석)

기능:
1. VectorDB 데이터 조회 (사용자별, 날짜별, 중복 확인 등)
2. ZIP 파일 내부 테이블/컬럼/데이터 분석
3. ZIP → 정제 데이터 변환 확인

사용법:
  python inspect_data.py --help
"""

import sys
import os
import json
from datetime import datetime

# 백엔드 경로 추가
sys.path.insert(0, os.path.abspath("."))

# .env 파일 로드 (선택적)
try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass
except Exception:
    pass

from app.core.vector_store import collection


# ============================================================
# 유틸리티 함수
# ============================================================


def print_header(title):
    """헤더 출력"""
    print("\n" + "=" * 100)
    print(f"  {title}")
    print("=" * 100)


def print_subheader(title):
    """서브헤더 출력"""
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


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


# ============================================================
# 1. ZIP 파일 분석 기능
# ============================================================


def inspect_zip(zip_path: str):
    """
    ZIP 파일 내 모든 테이블과 데이터 구조 확인

    Args:
        zip_path: ZIP 파일 경로

    Returns:
        dict: DB JSON 데이터
    """
    from app.core.unzipper import extract_zip_to_temp
    from app.core.db_to_json import db_to_json

    print_header(f"📦 ZIP 파일 분석: {os.path.basename(zip_path)}")

    if not os.path.exists(zip_path):
        print(f"\n❌ 파일이 존재하지 않습니다: {zip_path}")
        return None

    # 1) ZIP → DB 경로 추출
    db_path = extract_zip_to_temp(zip_path)
    print(f"\n✅ DB 경로: {db_path}")

    # 2) DB → JSON 변환
    db_json = db_to_json(db_path)

    print(f"📋 총 테이블 수: {len(db_json)}개\n")

    # 3) 테이블별 요약
    table_summary = []
    for table_name, rows in db_json.items():
        row_count = len(rows)
        columns = list(rows[0].keys()) if rows else []
        table_summary.append(
            {"table": table_name, "rows": row_count, "columns": columns}
        )

    # 레코드 수 기준 정렬
    table_summary.sort(key=lambda x: x["rows"], reverse=True)

    print(f"{'테이블명':<45} {'레코드':<10} {'컬럼 수':<10}")
    print(f"{'-'*45} {'-'*10} {'-'*10}")

    for t in table_summary:
        status = "✅" if t["rows"] > 0 else "⚠️"
        print(f"{status} {t['table']:<43} {t['rows']:<10} {len(t['columns']):<10}")

    return db_json


def inspect_zip_table(
    zip_path: str, table_name: str = None, limit: int = 5, summary_only: bool = False
):
    """
    ZIP 파일 내 특정 테이블 상세 확인

    Args:
        zip_path: ZIP 파일 경로
        table_name: 테이블명 (None이면 데이터 있는 모든 테이블)
        limit: 샘플 데이터 개수
        summary_only: True면 핵심 데이터만 표시
    """
    from app.core.unzipper import extract_zip_to_temp
    from app.core.db_to_json import db_to_json
    from app.utils.preprocess import epoch_day_to_date_string

    print_header(f"📦 ZIP 테이블 상세: {os.path.basename(zip_path)}")

    db_path = extract_zip_to_temp(zip_path)
    db_json = db_to_json(db_path)

    if table_name:
        # 특정 테이블만
        tables_to_show = {table_name: db_json.get(table_name, [])}
        if not db_json.get(table_name):
            print(f"\n❌ 테이블 '{table_name}'이 존재하지 않습니다.")
            print(f"📋 사용 가능한 테이블: {list(db_json.keys())}")
            return
    else:
        # 데이터 있는 테이블만
        tables_to_show = {k: v for k, v in db_json.items() if v}

    # 테이블별 핵심 필드 매핑
    table_key_fields = {
        "steps_record_table": ["local_date", "count"],
        "distance_record_table": ["local_date", "distance"],
        "heart_rate_record_table": ["local_date", "value"],
        "resting_heart_rate_record_table": ["local_date", "value"],
        "sleep_session_record_table": ["local_date", "start_time", "end_time"],
        "weight_record_table": ["local_date", "weight"],
        "height_record_table": ["local_date", "height"],
        "total_calories_burned_record_table": ["local_date", "energy"],
        "active_calories_burned_record_table": ["local_date", "energy"],
        "oxygen_saturation_record_table": ["local_date", "percentage"],
    }

    for tbl_name, rows in tables_to_show.items():
        print_subheader(f"📁 {tbl_name} ({len(rows)}개 레코드)")

        if not rows:
            print("   (데이터 없음)")
            continue

        # 컬럼 정보
        columns = list(rows[0].keys())

        if not summary_only:
            print(f"\n   📌 컬럼 ({len(columns)}개):")
            print(f"      {columns}")

        # 날짜 기준 최신순 정렬 (local_date 또는 date 컬럼)
        date_col = None
        if "local_date" in columns:
            date_col = "local_date"
        elif "date" in columns:
            date_col = "date"

        if date_col:
            sorted_rows = sorted(rows, key=lambda x: x.get(date_col, 0), reverse=True)
        else:
            sorted_rows = rows

        # 요약 모드
        if summary_only:
            key_fields = table_key_fields.get(tbl_name, ["local_date"])
            print(f"\n   📊 핵심 데이터 (최신 {limit}개):\n")

            for i, row in enumerate(sorted_rows[:limit], 1):
                # 날짜 변환
                local_date = row.get("local_date", 0)
                try:
                    date_str = epoch_day_to_date_string(local_date)
                except:
                    date_str = str(local_date)

                # 테이블별 핵심 값 추출
                if tbl_name == "steps_record_table":
                    count = row.get("count", 0)
                    print(f"      [{i}] 📅 {date_str} | 👣 {count:,}보")

                elif tbl_name == "distance_record_table":
                    distance = row.get("distance", 0)
                    print(f"      [{i}] 📅 {date_str} | 📏 {distance/1000:.2f}km")

                elif tbl_name in [
                    "heart_rate_record_table",
                    "resting_heart_rate_record_table",
                ]:
                    value = row.get("value", 0)
                    print(f"      [{i}] 📅 {date_str} | ❤️ {value}bpm")

                elif tbl_name == "sleep_session_record_table":
                    start = row.get("start_time", 0)
                    end = row.get("end_time", 0)
                    duration_min = (end - start) / 1000 / 60 if start and end else 0
                    duration_hr = duration_min / 60
                    print(
                        f"      [{i}] 📅 {date_str} | 😴 {duration_hr:.1f}시간 ({duration_min:.0f}분)"
                    )

                elif tbl_name == "weight_record_table":
                    weight = row.get("weight", 0) / 1000  # gram → kg
                    print(f"      [{i}] 📅 {date_str} | ⚖️ {weight:.1f}kg")

                elif tbl_name == "height_record_table":
                    height = row.get("height", 0)
                    print(f"      [{i}] 📅 {date_str} | 📐 {height:.2f}m")

                elif tbl_name in [
                    "total_calories_burned_record_table",
                    "active_calories_burned_record_table",
                ]:
                    energy = row.get("energy", 0) / 1000  # millikcal → kcal
                    print(f"      [{i}] 📅 {date_str} | 🔥 {energy:.0f}kcal")

                elif tbl_name == "oxygen_saturation_record_table":
                    percentage = row.get("percentage", 0)
                    print(f"      [{i}] 📅 {date_str} | 🫁 {percentage}%")

                else:
                    # 기타 테이블
                    print(f"      [{i}] 📅 {date_str}")

        else:
            # 전체 필드 모드
            print(f"\n   📊 샘플 데이터 (최신 {limit}개):")
            for i, row in enumerate(sorted_rows[:limit], 1):
                print(f"\n      [{i}]")
                for col, val in row.items():
                    val_str = str(val)
                    if len(val_str) > 50:
                        val_str = val_str[:50] + "..."
                    print(f"         {col}: {val_str}")

    print("\n" + "=" * 100)


def inspect_zip_parsed(zip_path: str):
    """
    ZIP → 날짜별 정제된 데이터로 변환 후 확인
    db_parser.py가 실제로 추출하는 데이터 확인

    Args:
        zip_path: ZIP 파일 경로

    Returns:
        dict: 날짜별 raw 데이터
    """
    from app.core.unzipper import extract_zip_to_temp
    from app.core.db_to_json import db_to_json
    from app.core.db_parser import parse_db_json_to_raw_data_by_day
    from app.utils.preprocess import epoch_day_to_date_string

    print_header(f"📦 ZIP → 정제 데이터 변환: {os.path.basename(zip_path)}")

    db_path = extract_zip_to_temp(zip_path)
    db_json = db_to_json(db_path)
    raw_by_day = parse_db_json_to_raw_data_by_day(db_json)

    if not raw_by_day:
        print("\n❌ 파싱된 데이터가 없습니다!")
        print("   → db_parser.py가 인식하는 테이블/컬럼이 없을 수 있습니다.")
        return None

    print(f"\n📅 총 {len(raw_by_day)}일치 데이터 추출됨\n")

    # 날짜 정렬 (최신순)
    sorted_dates = sorted(raw_by_day.keys(), reverse=True)

    # 어떤 필드에 데이터가 있는지 집계
    field_stats = {}
    for date_int, raw in raw_by_day.items():
        for k, v in raw.items():
            if v and v != 0:
                field_stats[k] = field_stats.get(k, 0) + 1

    # 데이터 있는 필드 출력
    print(f"📊 데이터가 있는 필드 (총 {len(field_stats)}개):")
    for field, count in sorted(field_stats.items(), key=lambda x: -x[1]):
        print(f"   {field:<25}: {count}일")

    # 날짜별 상세
    print(f"\n📅 날짜별 데이터 (최근 10일):")
    for date_int in sorted_dates[:10]:
        raw = raw_by_day[date_int]
        non_zero = {k: v for k, v in raw.items() if v and v != 0}

        # Epoch Day → YYYY-MM-DD 변환
        try:
            date_str = epoch_day_to_date_string(date_int)
        except:
            date_str = str(date_int)

        print(f"\n   {'─'*50}")
        print(f"   📅 {date_str}")
        if non_zero:
            for k, v in non_zero.items():
                print(f"      {k}: {format_data_value(k, v)}")
        else:
            print(f"      (모든 값이 0)")

    print("\n" + "=" * 100)
    return raw_by_day


def list_zip_files(directory: str = "./zip_data/uploads"):
    """
    ZIP 파일 목록 조회

    Args:
        directory: ZIP 파일이 저장된 디렉토리

    Returns:
        list: ZIP 파일 정보 리스트 (최신순 정렬)
    """
    print_header(f"📁 ZIP 파일 목록: {directory}")

    if not os.path.exists(directory):
        print(f"\n❌ 디렉토리가 존재하지 않습니다: {directory}")
        return []

    zip_files = []
    for f in os.listdir(directory):
        if f.endswith(".zip"):
            path = os.path.join(directory, f)
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            zip_files.append({"name": f, "path": path, "size": size, "modified": mtime})

    if not zip_files:
        print("\n⚠️ ZIP 파일이 없습니다.")
        return []

    # 수정일 기준 정렬
    zip_files.sort(key=lambda x: x["modified"], reverse=True)

    print(f"\n📊 총 {len(zip_files)}개 파일\n")

    for i, zf in enumerate(zip_files, 1):
        size_kb = zf["size"] / 1024
        print(f"   [{i}] {zf['name']}")
        print(
            f"       크기: {size_kb:.1f} KB | 수정: {zf['modified'].strftime('%Y-%m-%d %H:%M')}"
        )
        print(f"       경로: {zf['path']}")
        print()

    return zip_files


def get_latest_zip(directory: str = "./zip_data/uploads", user_id: str = None):
    """
    가장 최근 ZIP 파일 경로 반환

    Args:
        directory: ZIP 파일이 저장된 디렉토리
        user_id: 특정 사용자 필터 (예: "11@aa.com" → "11_aa_com" 패턴 매칭)

    Returns:
        str: 최신 ZIP 파일 경로 또는 None
    """
    if not os.path.exists(directory):
        return None

    # user_id를 파일명 패턴으로 변환
    user_pattern = None
    if user_id:
        user_pattern = user_id.replace("@", "_").replace(".", "_")

    zip_files = []
    for f in os.listdir(directory):
        if f.endswith(".zip"):
            # 사용자 필터링
            if user_pattern and not f.startswith(user_pattern):
                continue

            path = os.path.join(directory, f)
            mtime = os.path.getmtime(path)
            zip_files.append({"path": path, "mtime": mtime, "name": f})

    if not zip_files:
        return None

    # 최신 파일 반환
    zip_files.sort(key=lambda x: x["mtime"], reverse=True)
    return zip_files[0]["path"]


# ============================================================
# 2. VectorDB 조회 기능 (기존 기능)
# ============================================================


def get_date(user_id: str, date: str):
    """
    특정 날짜 데이터 조회 (함수로 제공)

    Args:
        user_id: 사용자 ID
        date: 날짜 (YYYY-MM-DD)

    Returns:
        dict: 데이터 딕셔너리 또는 None

    Usage:
        from inspect_data import get_date
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
    print_header(f"🔍 특정 날짜 조회: {user_id} | {target_date}")

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
                    f"\n   💡 상세 보기: python inspect_data.py --user {user_id} --detail"
                )

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def view_user_data(user_id: str, detailed=False, show_all_fields=False):
    """특정 사용자의 데이터 상세 조회 (출처 및 플랫폼 포함)"""
    print_header(f"🔍 User '{user_id}' 데이터 상세 조회")

    try:
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

            # 메타 정보
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
                            if value and value != 0:
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


# ============================================================
# 3. 데이터 삭제 기능
# ============================================================


def delete_user_data(user_id: str, confirm: bool = False):
    """특정 사용자의 모든 데이터 삭제"""
    print_header(f"🗑️ 사용자 데이터 삭제: {user_id}")

    try:
        result = collection.get(where={"user_id": user_id})
        ids = result.get("ids", [])

        if not ids:
            print(f"\n⚠️ '{user_id}' 사용자의 데이터가 없습니다.")
            return

        print(f"\n📊 삭제 대상: {len(ids)}개 레코드")

        if not confirm:
            print("\n⚠️ 실제 삭제하려면 --confirm 옵션을 추가하세요.")
            print(f"   예: python inspect_data.py --delete-user {user_id} --confirm")
            return

        collection.delete(ids=ids)
        print(f"\n✅ {len(ids)}개 레코드 삭제 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def delete_old_format_data(user_id: str = None, confirm: bool = False):
    """
    예전 형식 데이터 삭제 (source가 'api', 'zip' 등 플랫폼 없는 것)
    새 형식: 'api_samsung', 'api_apple', 'zip_samsung', 'zip_apple'
    """
    print_header("🗑️ 예전 형식 데이터 삭제")

    try:
        if user_id:
            result = collection.get(where={"user_id": user_id})
        else:
            result = collection.get()

        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])

        # 예전 형식 찾기 (source가 플랫폼 정보 없는 것)
        old_format_sources = ["api", "zip", "unknown", None, ""]

        to_delete = []
        for doc_id, meta in zip(ids, metadatas):
            source = meta.get("source", "")
            platform = meta.get("platform", "")

            # 예전 형식 조건
            is_old = (
                source in old_format_sources
                or platform in ["unknown", None, ""]
                or (source and "_" not in source)  # api_samsung 형식이 아닌 것
            )

            if is_old:
                to_delete.append(
                    {
                        "id": doc_id,
                        "user_id": meta.get("user_id"),
                        "date": meta.get("date"),
                        "source": source,
                        "platform": platform,
                    }
                )

        if not to_delete:
            print("\n✅ 예전 형식 데이터가 없습니다!")
            return

        print(f"\n📊 삭제 대상: {len(to_delete)}개 레코드\n")

        # 사용자별 그룹화해서 출력
        by_user = {}
        for item in to_delete:
            uid = item["user_id"]
            if uid not in by_user:
                by_user[uid] = []
            by_user[uid].append(item)

        for uid, items in by_user.items():
            print(f"👤 {uid}: {len(items)}개")
            for item in items[:5]:  # 최대 5개만 표시
                print(
                    f"   📅 {item['date']} | 출처: {item['source']} | 플랫폼: {item['platform']}"
                )
            if len(items) > 5:
                print(f"   ... 외 {len(items) - 5}개")

        if not confirm:
            print("\n⚠️ 실제 삭제하려면 --confirm 옵션을 추가하세요.")
            print(f"   예: python inspect_data.py --delete-old --confirm")
            return

        # 삭제 실행
        delete_ids = [item["id"] for item in to_delete]
        collection.delete(ids=delete_ids)
        print(f"\n✅ {len(delete_ids)}개 레코드 삭제 완료!")

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


def delete_by_source(source: str, user_id: str = None, confirm: bool = False):
    """특정 출처(source)의 데이터 삭제"""
    print_header(f"🗑️ 출처별 데이터 삭제: {source}")

    try:
        if user_id:
            result = collection.get(
                where={"$and": [{"user_id": user_id}, {"source": source}]}
            )
        else:
            result = collection.get(where={"source": source})

        ids = result.get("ids", [])
        metadatas = result.get("metadatas", [])

        if not ids:
            print(f"\n⚠️ 출처 '{source}'의 데이터가 없습니다.")
            return

        print(f"\n📊 삭제 대상: {len(ids)}개 레코드\n")

        for meta in metadatas[:10]:
            print(
                f"   📅 {meta.get('date')} | 사용자: {meta.get('user_id')} | 플랫폼: {meta.get('platform')}"
            )
        if len(metadatas) > 10:
            print(f"   ... 외 {len(metadatas) - 10}개")

        if not confirm:
            print("\n⚠️ 실제 삭제하려면 --confirm 옵션을 추가하세요.")
            return

        collection.delete(ids=ids)
        print(f"\n✅ {len(ids)}개 레코드 삭제 완료!")

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
            print(f"상태: ❌ 존재하지 않음")

        print("\n" + "=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")


def list_users():
    """VectorDB에 저장된 사용자(이메일) 목록 조회"""
    print_header("👥 사용자 목록")

    try:
        all_data = collection.get()
        metadatas = all_data.get("metadatas", [])

        if not metadatas:
            print("\n⚠️ 데이터가 없습니다!")
            return

        # 사용자별 집계
        user_stats = {}
        for meta in metadatas:
            user_id = meta.get("user_id", "unknown")
            source = meta.get("source", "unknown")
            platform = meta.get("platform", "unknown")

            if user_id not in user_stats:
                user_stats[user_id] = {
                    "count": 0,
                    "sources": set(),
                    "platforms": set(),
                }

            user_stats[user_id]["count"] += 1
            user_stats[user_id]["sources"].add(source)
            user_stats[user_id]["platforms"].add(platform)

        print(f"\n📊 총 {len(user_stats)}명의 사용자\n")

        # 데이터 개수 기준 정렬
        sorted_users = sorted(user_stats.items(), key=lambda x: -x[1]["count"])

        for i, (user_id, stats) in enumerate(sorted_users, 1):
            sources = ", ".join(stats["sources"])
            platforms = ", ".join(stats["platforms"])
            print(f"   [{i}] {user_id}")
            print(
                f"       데이터: {stats['count']}개 | 출처: {sources} | 플랫폼: {platforms}"
            )
            print()

        print("=" * 100)

    except Exception as e:
        print(f"❌ 오류 발생: {str(e)}")
        import traceback

        traceback.print_exc()


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


# ============================================================
# 메인 (CLI)
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="데이터 검사 통합 스크립트 (VectorDB + ZIP 분석)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 ZIP 파일 분석
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python inspect_data.py --zip-list                     # ZIP 파일 목록
  python inspect_data.py --zip-latest                   # 최신 ZIP 테이블 요약
  python inspect_data.py --zip-latest --parsed          # 최신 ZIP 정제 데이터
  python inspect_data.py --zip-latest --table <테이블>  # 최신 ZIP 특정 테이블
  python inspect_data.py --zip <경로>                   # 특정 ZIP 테이블 요약
  python inspect_data.py --zip <경로> --table <테이블>  # 특정 ZIP 특정 테이블
  python inspect_data.py --zip <경로> --parsed          # 특정 ZIP 정제 데이터

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🗄️ VectorDB 조회
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  python inspect_data.py --all                          # 전체 데이터 요약
  python inspect_data.py --user <이메일>                # 특정 사용자 데이터
  python inspect_data.py --user <이메일> --detail       # 상세 정보
  python inspect_data.py --user <이메일> --detail --all-fields  # 모든 필드
  python inspect_data.py --date <YYYY-MM-DD> --user <이메일>    # 특정 날짜
  python inspect_data.py --duplicates                   # 중복 데이터 확인
  python inspect_data.py --dates                        # 날짜 범위 확인
  python inspect_data.py --location                     # ChromaDB 위치

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🐍 Python에서 import해서 사용
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  from inspect_data import get_date, inspect_zip, get_latest_zip
  
  # VectorDB 조회
  data = get_date("user@example.com", "2025-12-16")
  print(data['raw'])
  
  # ZIP 분석
  latest = get_latest_zip()  # 최신 ZIP 경로
  db_json = inspect_zip(latest)
        """,
    )

    # ZIP 관련 인자
    parser.add_argument("--zip", type=str, help="ZIP 파일 경로 (테이블 요약)")
    parser.add_argument("--zip-list", action="store_true", help="ZIP 파일 목록 조회")
    parser.add_argument(
        "--zip-latest", action="store_true", help="가장 최근 ZIP 파일 분석"
    )
    parser.add_argument(
        "--table", type=str, help="특정 테이블 상세 (--zip과 함께 사용)"
    )
    parser.add_argument(
        "--summary", action="store_true", help="핵심 데이터만 표시 (날짜, 값)"
    )
    parser.add_argument(
        "--parsed", action="store_true", help="정제된 데이터 확인 (--zip과 함께 사용)"
    )
    parser.add_argument(
        "--limit", type=int, default=5, help="샘플 데이터 개수 (기본: 5)"
    )

    # VectorDB 관련 인자
    parser.add_argument("--all", action="store_true", help="전체 데이터 요약 보기")
    parser.add_argument("--users", action="store_true", help="사용자(이메일) 목록 보기")
    parser.add_argument("--user", type=str, help="특정 사용자 데이터 확인")
    parser.add_argument("--date", type=str, help="특정 날짜 조회 (YYYY-MM-DD)")
    parser.add_argument("--detail", action="store_true", help="상세 정보 보기")
    parser.add_argument(
        "--all-fields", action="store_true", help="모든 데이터 필드 보기"
    )
    parser.add_argument("--duplicates", action="store_true", help="중복 데이터 확인")
    parser.add_argument("--dates", action="store_true", help="날짜 범위 확인")
    parser.add_argument("--location", action="store_true", help="ChromaDB 위치 확인")

    # 삭제 관련 인자
    parser.add_argument("--delete-user", type=str, help="특정 사용자 데이터 삭제")
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="예전 형식 데이터 삭제 (source에 플랫폼 없는 것)",
    )
    parser.add_argument(
        "--delete-source", type=str, help="특정 출처 데이터 삭제 (예: api, zip)"
    )
    parser.add_argument("--confirm", action="store_true", help="삭제 실행 확인")

    args = parser.parse_args()

    # ─────────────────────────────────────────────
    # ZIP 분석
    # ─────────────────────────────────────────────
    if args.zip_list:
        list_zip_files()
    elif args.zip_latest:
        # 가장 최근 ZIP 파일 자동 선택
        latest_path = get_latest_zip()
        if not latest_path:
            print("❌ ZIP 파일이 없습니다.")
        else:
            print(f"📦 최신 ZIP: {os.path.basename(latest_path)}\n")
            if args.parsed:
                inspect_zip_parsed(latest_path)
            elif args.table:
                inspect_zip_table(latest_path, args.table, args.limit, args.summary)
            else:
                inspect_zip(latest_path)
    elif args.zip:
        if args.parsed:
            inspect_zip_parsed(args.zip)
        elif args.table:
            inspect_zip_table(args.zip, args.table, args.limit, args.summary)
        else:
            inspect_zip(args.zip)

    # ─────────────────────────────────────────────
    # VectorDB 조회
    # ─────────────────────────────────────────────
    elif args.date and args.user:
        view_specific_date(args.user, args.date)
    elif args.all:
        view_all_data(show_summary=True)
    elif args.users:
        list_users()
    elif args.user:
        view_user_data(args.user, detailed=args.detail, show_all_fields=args.all_fields)
    elif args.duplicates:
        check_duplicates()
    elif args.dates:
        show_date_range()
    elif args.location:
        check_chroma_location()

    # ─────────────────────────────────────────────
    # 삭제 기능
    # ─────────────────────────────────────────────
    elif args.delete_user:
        delete_user_data(args.delete_user, confirm=args.confirm)
    elif args.delete_old:
        delete_old_format_data(user_id=args.user, confirm=args.confirm)
    elif args.delete_source:
        delete_by_source(args.delete_source, user_id=args.user, confirm=args.confirm)

    else:
        # 기본: 도움말 + 전체 요약
        check_chroma_location()
        print()
        view_all_data(show_summary=True)
