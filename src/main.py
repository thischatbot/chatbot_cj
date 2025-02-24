from fastapi import FastAPI

app = FastAPI()

@app.get("/")
def read_roof():
    return {"message": "FastAPI 서버가 정상적으로 실행 중!"}