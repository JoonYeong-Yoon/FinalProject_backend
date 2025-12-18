import io, cv2, tempfile, os
import numpy as np 
from fastapi import UploadFile
from typing import Tuple
import subprocess
import imageio_ffmpeg

from utils.video_model import kneepushup_model

async def _get_video_props(video):
    await video.seek(0)
    video_bytes = await video.read()
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp.close()
        cap = cv2.VideoCapture(tmp.name)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps is None or fps <= 0:
        fps = 30.0
    return width, height, fps

async def _get_video_frames(video):
    await video.seek(0)
    video_bytes = await video.read()
    frames = []
    with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as tmp:
        tmp.write(video_bytes)
        tmp.close()
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise RuntimeError("Failed to open video")
        fps = cap.get(cv2.CAP_PROP_FPS)
        if fps is None or fps <= 0 or np.isnan(fps):
            fps = 30
        while True:
            ret, frame = cap.read()
            if not ret:
                break
            # frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            frames.append(frame)
        cap.release()
    frames = np.array(frames)
    return frames

async def analyze_exercise_video(video:UploadFile):
    width, height, fps = await _get_video_props(video)
    frames = await _get_video_frames(video)
    # 추론하기
    keypoints = kneepushup_model.get_keypoints(frames)
    scores = kneepushup_model.get_score(frames, keypoints)
    out_frames = kneepushup_model.vis_frame(frames, keypoints, scores)
    
    # 영상 저장하기
    tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
    output_path = tmp.name
    tmp.close()
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    out = cv2.VideoWriter(
        output_path, fourcc, fps, (width, height))

    for img in out_frames:
        out.write(img.astype(np.uint8))
    out.release()
    
    # 인코딩 변경하기
    fixed_path = output_path.replace(".mp4", "_fast.mp4")
    ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()
    subprocess.run([
        ffmpeg_path,
        "-y",
        "-i", output_path,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        fixed_path
    ], check=True)
    return fixed_path
