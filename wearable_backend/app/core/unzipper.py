import zipfile
import os
import tempfile


def is_sqlite_file(path: str) -> bool:
    """SQLite 파일인지 시그니처로 검사"""
    try:
        with open(path, "rb") as f:
            header = f.read(16)
            return header.startswith(b"SQLite format 3")
    except:
        return False


def extract_zip_to_temp(zip_path: str) -> str:
    """
    ZIP 파일을 임시 폴더에 압축해제하고,
    그 안에서 SQLite DB 파일(.db 확장자 여부와 상관 없음)을 찾아 반환한다.
    """

    # 1) 임시 디렉토리 생성
    temp_dir = tempfile.mkdtemp()

    # 2) ZIP 해제
    with zipfile.ZipFile(zip_path, "r") as zip_ref:
        zip_ref.extractall(temp_dir)

    # 2) SQLite 파일 탐색
    for root, dirs, files in os.walk(temp_dir):
        for f in files:
            file_path = os.path.join(root, f)

            # 확장자 확인 대신 SQLite signature 검사
            if is_sqlite_file(file_path):
                return file_path

    # 못 찾으면 에러
    raise FileNotFoundError("ZIP 안에서 SQLite DB 파일을 찾지 못했습니다.")
