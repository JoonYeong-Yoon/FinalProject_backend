
```bash
# main backend 설치
cd main_backend
conda create -n final_backend_main python==3.10 -y
conda activate final_backend_main
cd FinalProject_backend
cd main_backend
pip install -r requirements.txt
```

```bash
# FinalProject_backend/main_backend/utils/weights 에 model_kneepushup.pth 추가할 것 해당파일은 단톡에 수진님이 업로드한 자료
```
```bash
# main backend 실행
cd FinalProject_backend
cd main_backend
python main.py
```


```bash
# wearable backend 설치
conda create -n final_backend_wearable python==3.10 -y
conda activate final_backend_wearable
cd FinalProject_backend
cd wearable_backend
pip install -r requirements.txt
```

wearable_backend 경로 안에 .env 파일 생성
```bash
# .env 파일 안에 아래 내용 기재
OPENAI_API_KEY=sk-xxx
LLM_MODEL=gpt-4o-mini
LLM_TEMPERATURE=0.3
LLM_MAX_TOKENS=2048
ALLOWED_ORIGINS=http://localhost:3000
```


```bash
# wearable backend 실행
cd FinalProject_backend
cd wearable_backend
python main.py
```