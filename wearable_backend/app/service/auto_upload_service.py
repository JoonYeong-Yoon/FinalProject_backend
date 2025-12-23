import uuid
import asyncio
from fastapi import HTTPException
from concurrent.futures import ThreadPoolExecutor

from app.utils.preprocess import preprocess_health_json
from app.utils.platform_detection import detect_platform
from app.core.vector_store import save_daily_summary
from app.core.llm_analysis import run_llm_analysis


executor = ThreadPoolExecutor(max_workers=4)


async def run_blocking(func, *args):
    """동기 함수를 비동기로 실행"""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(executor, lambda: func(*args))


class AutoUploadService:
    """
    앱에서 직접 전송한 JSON Health 데이터를 처리하는 서비스 (날짜별 처리)

    ✅ 개선 사항:
    1. 날짜별 개별 처리 (ZIP과 동일한 방식)
    2. 각 날짜마다 VectorDB에 별도 저장
    3. platform 자동 감지 (samsung/apple)
    """

    @staticmethod
    def get_or_create_user_id(user_id: str | None):
        if not user_id or not user_id.strip():
            return str(uuid.uuid4())
        return user_id

    async def process_json(
        self,
        json_data: dict,
        user_id: str | None,
        date: str,  # ✅ YYYY-MM-DD 형식
        difficulty: str = "중",
        duration: int = 30,
    ):
        user_id = self.get_or_create_user_id(user_id)

        # ✅ 플랫폼 자동 감지
        platform = detect_platform(json_data)

        print(f"\n{'='*60}")
        print(f"📥 API 데이터 처리 시작: {date}")
        print(f"{'='*60}")
        print(f"User ID: {user_id}")
        print(f"Date: {date}")
        print(f"Platform: {platform}")  # ✅ 감지된 플랫폼 출력
        print(f"Difficulty: {difficulty}, Duration: {duration}분")
        print(f"Raw data keys: {list(json_data.keys())}")

        # 1️⃣ Summary 생성 (날짜 포함)
        try:
            print(f"\n[STEP 1] Summary 생성 중... (날짜: {date})")

            # ✅ 날짜 문자열을 date_int로 변환 (YYYYMMDD)
            # 예: "2025-12-17" → 20251217
            date_int = int(date.replace("-", ""))

            latest_summary = await run_blocking(
                preprocess_health_json,
                json_data,
                date_int,
                platform,  # ✅ 자동 감지된 플랫폼 사용
            )

            print(f"✅ Summary 생성 완료")
            print(f"   created_at: {latest_summary.get('created_at')}")
            print(f"   platform: {platform}")
            print(f"   date: {date}")

        except Exception as e:
            print(f"❌ Summary 생성 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            raise HTTPException(500, f"Summary 생성 실패: {str(e)}")

        # 2️⃣ Vector DB 저장
        try:
            print(f"\n[STEP 2] Vector DB 저장 중...")

            # ✅ 플랫폼별 source 구분
            source = f"api_{platform}"  # "api_samsung" or "api_apple"

            print(f"   플랫폼: {platform}")
            print(f"   Source: {source}")

            save_result = await run_blocking(
                save_daily_summary, latest_summary, user_id, source
            )
            print(f"✅ Vector DB 저장 완료 (source: {source}): {save_result}")

        except Exception as e:
            print(f"❌ Vector DB 저장 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            raise HTTPException(500, f"Vector DB 저장 실패: {str(e)}")

        # 3️⃣ LLM 분석
        try:
            print(f"\n[STEP 3] LLM 분석 시작...")
            print(f"   summary keys: {list(latest_summary.keys())}")
            print(f"   user_id: {user_id}")
            print(f"   difficulty: {difficulty}")
            print(f"   duration: {duration}")

            llm_result = await run_blocking(
                run_llm_analysis,
                latest_summary,
                user_id,
                difficulty,
                duration,
            )

            print(f"✅ LLM 분석 완료")
            print(f"   result keys: {list(llm_result.keys())}")

            # 결과 검증
            if "analysis" not in llm_result:
                print("[WARN] LLM 결과에 'analysis' 필드가 없습니다.")
            if "ai_recommended_routine" not in llm_result:
                print("[WARN] LLM 결과에 'ai_recommended_routine' 필드가 없습니다.")

        except Exception as e:
            print(f"❌ LLM 분석 실패: {str(e)}")
            import traceback

            traceback.print_exc()
            # ✅ LLM 분석 실패해도 데이터는 저장됨
            llm_result = {
                "analysis": "LLM 분석 실패",
                "ai_recommended_routine": {},
                "detailed_health_report": "",
            }

        # 4️⃣ 최종 응답
        print(f"\n{'='*60}")
        print(f"✅ {date} 데이터 처리 완료 (플랫폼: {platform})")
        print(f"{'='*60}\n")

        return {
            "success": True,
            "user_id": user_id,
            "date": date,
            "platform": platform,  # ✅ 응답에 플랫폼 포함
            "summary": latest_summary,
            "analysis": llm_result.get("analysis", ""),
            "ai_recommended_routine": llm_result.get("ai_recommended_routine", {}),
            "detailed_health_report": llm_result.get("detailed_health_report", ""),
        }
