import os, shutil, tempfile, uuid
from fastapi import UploadFile, HTTPException
import asyncio
from concurrent.futures import ThreadPoolExecutor

from app.core.unzipper import extract_zip_to_temp
from app.core.db_to_json import db_to_json
from app.core.db_parser import parse_db_json_to_raw_data_by_day

from app.utils.preprocess import preprocess_health_json
from app.core.vector_store import save_daily_summaries_batch
from app.core.llm_analysis import run_llm_analysis

# 비동기 처리용 Executor
executor = ThreadPoolExecutor(max_workers=4)


class FileUploadService:
    """
    ZIP/DB 파일 업로드 처리 서비스 (날짜 및 플랫폼 정보 개선 버전)

    개선 사항:
    1. 날짜 정보 제대로 전달 (date_int 활용)
    2. 플랫폼 정보 자동 감지 (Apple/Samsung)
    3. VectorDB에 정확한 날짜 저장
    """

    @staticmethod
    def get_or_create_user_id(user_id: str | None):
        if not user_id or not user_id.strip():
            return str(uuid.uuid4())
        return user_id

    @staticmethod
    async def run_blocking(func, *args):
        """동기 함수를 비동기로 실행"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(executor, lambda: func(*args))

    @staticmethod
    def detect_platform(filename: str, db_json: dict) -> str:
        """
        플랫폼 자동 감지

        Returns:
            "apple" or "samsung" or "unknown"
        """
        filename_lower = filename.lower()

        # ✅ 파일명으로 감지
        if "healthconnect" in filename_lower or "samsung" in filename_lower:
            return "samsung"
        elif (
            "export" in filename_lower
            or "apple" in filename_lower
            or "health" in filename_lower
        ):
            return "apple"

        # ✅ DB 구조로 감지 (Samsung Health Connect 특징)
        if db_json:
            # Samsung Health Connect는 특정 테이블 존재
            samsung_tables = [
                "steps_record_table",
                "distance_record_table",
                "heart_rate_record_table",
            ]
            if all(table in db_json for table in samsung_tables):
                return "samsung"

            # Apple Health Export는 다른 구조
            apple_indicators = ["HealthKit", "HKQuantityTypeIdentifier"]
            # (추가 로직 필요 시)

        return "unknown"

    async def process_file(
        self,
        file: UploadFile,
        user_id: str | None,
        difficulty: str,
        duration: int,
    ):
        user_id = self.get_or_create_user_id(user_id)

        temp_dir = tempfile.mkdtemp()
        temp_path = os.path.join(temp_dir, file.filename)

        try:
            print(f"[INFO] 파일 업로드 시작: {file.filename}")

            # 1️⃣ 파일 저장
            with open(temp_path, "wb") as buffer:
                buffer.write(await file.read())

            # 2️⃣ ZIP 또는 DB 판별
            if file.filename.lower().endswith(".zip"):
                print("[INFO] ZIP 파일 압축 해제 중...")
                db_path = await self.run_blocking(extract_zip_to_temp, temp_path)
            elif file.filename.lower().endswith(".db"):
                db_path = temp_path
            else:
                raise HTTPException(400, "ZIP 또는 DB 파일만 업로드 가능합니다.")

            if not db_path:
                raise HTTPException(500, "DB 파일 경로를 찾을 수 없습니다.")

            # 3️⃣ DB → JSON (비동기 처리)
            print("[INFO] DB 파싱 중...")
            raw_db_json = await self.run_blocking(db_to_json, db_path)

            # ✅ 개선: 플랫폼 감지
            platform = self.detect_platform(file.filename, raw_db_json)
            print(f"[INFO] 감지된 플랫폼: {platform}")

            # 4️⃣ 날짜별 raw 추출
            print("[INFO] 날짜별 데이터 추출 중...")
            raw_by_day = await self.run_blocking(
                parse_db_json_to_raw_data_by_day, raw_db_json
            )

            if not raw_by_day:
                raise HTTPException(
                    500, "DB Parser가 건강 데이터를 추출하지 못했습니다."
                )

            total_days = len(raw_by_day)
            print(f"[INFO] 총 {total_days}일치 데이터 추출 완료")

            # 날짜 범위 출력
            dates = sorted(raw_by_day.keys())
            if dates:
                print(f"[INFO] 날짜 범위: {dates[0]} ~ {dates[-1]}")

            # 5️⃣ 최신 날짜 결정
            latest_date = max(raw_by_day.keys())
            latest_raw = raw_by_day[latest_date]

            # 6️⃣ 최신 1일치 summary (분석용)
            print("[INFO] 최신 데이터 전처리 중...")
            # ✅ 개선: 날짜와 플랫폼 정보 전달
            latest_summary = await self.run_blocking(
                preprocess_health_json, latest_raw, latest_date, platform
            )

            # 7️⃣ 전체 날짜 summary → Vector DB 배치 저장 (핵심 개선!)
            print(f"[INFO] VectorDB에 {total_days}일치 데이터 배치 저장 중...")

            # ✅ 개선: 모든 날짜의 summary 생성 (날짜 정보 포함!)
            all_summaries = []
            for date_int, raw in raw_by_day.items():
                daily_summary = await self.run_blocking(
                    preprocess_health_json,
                    raw,
                    date_int,
                    platform,
                    #                             ^^^^^^^^  ^^^^^^^^
                    #                             날짜!     플랫폼!
                )
                all_summaries.append(daily_summary)

            # ✅ 개선: 배치로 한 번에 저장 (source + platform)
            source = f"zip_{platform}"  # "zip_apple" or "zip_samsung"
            await self.run_blocking(
                save_daily_summaries_batch, all_summaries, user_id, source
            )

            print(
                f"[SUCCESS] {total_days}일치 데이터 VectorDB 저장 완료 (플랫폼: {platform})"
            )

            # 8️⃣ LLM 분석 (최신 데이터만)
            print("[INFO] LLM 분석 실행 중...")
            llm_result = await self.run_blocking(
                run_llm_analysis,
                latest_summary,
                user_id,
                difficulty,
                duration,
            )

            print("[SUCCESS] 분석 완료")

            return {
                "message": "ZIP/DB 업로드 및 분석 성공",
                "user_id": user_id,
                "total_days_saved": total_days,
                "date_range": f"{dates[0]} ~ {dates[-1]}" if dates else "",
                "latest_date": latest_date,
                "platform": platform,  # ✅ 플랫폼 정보 반환
                "summary": latest_summary,
                "llm_result": llm_result,
            }

        except HTTPException:
            raise
        except Exception as e:
            print(f"[ERROR] 처리 중 오류: {str(e)}")
            import traceback

            traceback.print_exc()
            raise HTTPException(500, f"ZIP/DB 처리 중 오류 발생: {str(e)}")

        finally:
            # 9️⃣ 임시 디렉토리 정리
            try:
                shutil.rmtree(temp_dir)
            except Exception:
                pass
