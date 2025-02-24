# 1. Python 3.12.3 기반 이미지 사용
FROM python:3.12.3

# 2. 작업 디렉토리 설정
WORKDIR /app

# 3. 필요한 파일 복사
COPY ./src /app/src
COPY ./requirements.txt /app/

# 4. 패키지 설치
RUN pip install --no-cache-dir -r requirements.txt

# 5. FASTAPI 서버 실행 (포트 8000)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]