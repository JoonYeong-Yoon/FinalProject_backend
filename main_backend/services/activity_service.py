# app/services/activity_service.py
"""
업로드된 영상 비동기 처리 서비스 (배치/백그라운드 방식)
- enqueue_video_processing(file_path, activity_id, user_id): 외부 워커/내부 작업 큐로 작업 등록
- process_uploaded_video(file_path, activity_id): 실제 분석 파이프라인(플레이스홀더)
주의: 실시간이 아닌 배치 처리 방식.
"""
import os
from core.db import get_db_connection

def enqueue_video_processing(file_path: str, activity_id: str, user_id: str):
    """
    실제 환경에서는 Celery/RQ/Kafka 같은 워커에게 작업을 enqueue 함.
    현재는 간단히 바로 처리(또는 placeholder)로 두고, 추후 외부 워커 연결 권장.
    """
    # placeholder: 바로 처리 함수를 호출하면 동기 blocking이 될 수 있으므로, 실제로는 외부 워커 사용
    # 예: celery.send_task("tasks.process_video", args=[file_path, activity_id, user_id])
    process_uploaded_video(file_path, activity_id, user_id)

def process_uploaded_video(file_path: str, activity_id: str, user_id: str):
    """
    업로드된 영상 분석(플레이스홀더)
    - 실제 파이프라인: 영상에서 프레임 추출 → 모델(포즈분석)으로 점수 산출 → DB 저장
    """
    # 간단히 DB에 '완료' 처리 및 예시 score 저장 (임시)
    conn = get_db_connection()
    cur = conn.cursor()
    # 예시: activity_logs.status = 'COMPLETED', activity_detail_logs 추가 등
    cur.execute("UPDATE activity_logs SET status=%s WHERE id=%s;", ("FINISHED", activity_id))
    conn.commit()
    conn.close()
    # 실제 분석 결과를 activity_detail_logs, pose_analysis 등에 기록해야 함.
