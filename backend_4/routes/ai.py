from fastapi import APIRouter
from controllers import ai

router = APIRouter()
router.add_api_route("/analyze-video",ai.analyze_exercise_video, methods=["POST"])