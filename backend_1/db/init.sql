-- ============================================================
-- PostgreSQL 초기 설정 스크립트 (컨테이너 최초 실행 시 자동 적용됨)
-- ============================================================

-- 1. UUID 사용 확장 활성화
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. exercise 테이블 생성 (운동 종목)
CREATE TABLE IF NOT EXISTS exercise (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    category VARCHAR(50),
    difficulty INT,
    description TEXT,
    video_url TEXT
);

-- 3. 운동 종목 17개 초기 데이터 삽입
INSERT INTO exercise (name) VALUES
('스탠딩 사이드 크런치'),
('스탠딩 니업'),
('버피 테스트'),
('스텝 포워드 다이나믹 런지'),
('스텝 백워드 다이나믹 런지'),
('사이드 런지'),
('크로스 런지'),
('굿모닝'),
('라잉 레그 레이즈'),
('크런치'),
('바이시클 크런치'),
('시저크로스'),
('힙쓰러스트'),
('플랭크'),
('푸시업'),
('니푸쉬업'),
('와이 엑서사이즈');

-- (추가) 향후 routine, user 등 스키마를 확장하려면
-- 여기 init.sql에 CREATE TABLE...을 넣거나,
-- 별도 migration tool(Flyway 등)로 관리해도 됨.
