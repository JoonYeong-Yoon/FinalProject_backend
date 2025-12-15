# AI Trainer Backend - 프로젝트 구조 및 파일 설명

## 1. 폴더별 역할

### `config/`

* 환경 설정 관련

#### `settings.py`

* BaseSettings 사용, 환경변수(.env) 지원
* DB URL, JWT 시크릿, 토큰 만료 시간 등 정의

---

### `controllers/` - 서비스 로직

* 모델(DB)과 라우터(API) 사이 로직
* 유저, 구독 등 비즈니스 로직 처리

#### `user/login_controller.py`

* 로그인 처리, 비밀번호 검증

#### `user/register_controller.py`

* 회원가입 처리, 초기 user_info 레코드 생성

#### `user/update_controller.py`

* 사용자 정보 업데이트 로직
* users / user_body_info / user_info 통합 처리

#### `subscription_controller.py`

* 구독 시작/취소 로직

---

### `db/`

* 데이터베이스 관련 설정

#### `database.py`

* SQLAlchemy Engine 생성
* DB 커넥션 yield 함수 제공 (`get_db`)

---

### `models/` - DB 모델 및 쿼리

* 실제 DB 쿼리와 CRUD 처리
* 각 모델별로 테이블 단위로 나눔

#### `__init__.py`

* 모델 함수들을 패키지 단위로 편리하게 import 가능하게 재노출

#### `helpers.py`

* update_record 등 공통 CRUD 헬퍼
* JSON 변환, set_clause 생성 등

#### `subscription_model.py`

* users 테이블의 is_subscribed 필드 관리
* 구독 상태 변경
* `tables.py`의 `users` 객체 사용 가능

#### `tables.py`

* DB 테이블 스키마 정의
* SQLAlchemy `Table` 객체로 각 테이블 정의
* 기존 모델에서 사용되는 테이블 구조를 중앙 관리
* 예: `users`, `user_info`, `user_body_info` 테이블 정의
* 모든 모델(`users_model.py`, `user_info_model.py` 등)은 이 테이블 객체를 import하여 사용
* **장점**
  * 테이블 구조 변경 시 중앙에서 관리 가능
  * SQLAlchemy Core 또는 ORM 활용 가능
* **단점**
  * 소규모 프로젝트에서는 모델과 테이블 정의가 분리되어 있어 관리가 약간 번거로울 수 있음

#### `user_body_model.py`

* user_body_info 테이블 CRUD
* 키, 몸무게, BMI, 통증 정보 등
* `tables.py`의 `user_body_info` 객체 사용

#### `user_info_model.py`

* user_info 테이블 CRUD
* 개인 정보, 활동, 선호 정보 등 관리
* `update_record` 헬퍼 사용 가능
* `tables.py`의 `user_info` 객체 사용

#### `users_model.py`

* users 테이블 CRUD
* 이메일/ID 조회, 생성, 업데이트, 삭제
* `tables.py`의 `users` 객체 사용

---

### `routes/` - API 라우터 모음

* 클라이언트 요청을 처리하기 위한 엔드포인트 정의
* 폴더 구조에 따라 기능별 라우터를 분리

#### `routes/users/`

* 사용자 관련 API
* 하위 라우터로 기능을 분리

  * `__init__.py` : 하위 라우터들을 통합하여 하나의 APIRouter 객체로 제공
  * `auth_route.py` : 로그인, 회원가입
  * `manage_route.py` : 회원 탈퇴, 계정 관리
  * `profile_route.py` : 프로필 조회, 수정

#### `subscription_route.py`

* 구독 시작/취소 API 제공
* `start`, `cancel` 엔드포인트

#### `video_route.py`

* 비디오 업로드 API
* `UploadFile`로 파일 수신 후 임시 처리

---

### `services/` - 공통 기능

* 비밀번호 해싱, JWT 인증 등 공통 유틸

#### `hashing_service.py`

* bcrypt 기반 비밀번호 해싱 및 검증

#### `oauth2_service.py`

* JWT 토큰 생성 및 검증
* OAuth2PasswordBearer 기반 의존성

---

### `main.py`

* FastAPI 앱 초기화
* CORS 설정
* 라우터 등록
* 루트 엔드포인트 제공
* uvicorn 실행 설정

---

## 2. 프로젝트 구조 요약

```
AI-Trainer-Backend/
│
├─ config/
│  └─ settings.py
│
├─ controllers/
│  ├─ user/
│  │  ├─ login_controller.py
│  │  ├─ register_controller.py
│  │  └─ update_controller.py
│  │
│  └─ subscription_controller.py
│
├─ db/
│  └─ database.py
│
├─ models/
│  ├─ __init__.py
│  ├─ helpers.py
│  ├─ subscription_model.py
│  ├─ tables.py
│  ├─ user_body_model.py
│  ├─ user_info_model.py
│  └─ users_model.py
│
├─ routes/
│  ├─ users/
│  │  ├─ __init__.py
│  │  ├─ auth_route.py
│  │  ├─ manage_route.py
│  │  └─ profile_route.py
│  │
│  ├─ subscription_route.py
│  └─ video_route.py
│
├─ services/
│  ├─ hashing_service.py
│  └─ oauth2_service.py
│
└─ main.py

```

---

> 🔹 목적
>
> * 새로운 개발자가 프로젝트 구조를 빠르게 이해할 수 있음
> * 각 폴더, 파일의 역할 명확화
> * 패키지 사용 방법과 import 관례 이해 도움
> * `tables.py`를 활용하면 테이블 변경 시 중앙에서 관리 가능


> 🔹 백엔드 실행
> 
> * conda activate ai_trainer
> * python main.py
uvicorn main:app --reload
uvicorn main:app --host 0.0.0.0 --reload
