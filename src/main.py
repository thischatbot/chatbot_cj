from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from api_key import OPENAI_API_KEY
import openai
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

app = FastAPI()

#OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

# SQListe DB 연결
DB_PATH = "../emotions.db"

# 요청 데이터 모델 정의 (JSON Body에서 받기)
class EmotionRequest(BaseModel):
    user_name: str
    text: str

def analyze_emotion(text):
    """GPT API를 사용해 감정을 분석하는 함수"""
    prompt = f"""
    다음 문장의 감정을 분석해줘.
    오직 아래 중 하나만 출력해:
    - 긍정
    - 부정
    - 중립
    
    문장: "{text}"
    답변:
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 감정 분석 AI다. 반드시 '긍정', '부정', '중립' 중 하나만 출력해."},
                {"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    #print(f"GPT 함수 응답 결과 : {result}")
    # 사용한 토큰 수 출력
    #print(f"총 사용 토큰 수: {response.usage.total_tokens}")
    
    #혹시라도 GPT가 이상한 응답을 하면 기본값 설정
    if result not in ["긍정", "부정", "중립"]:
        print(f"⚠ 경고: GPT가 이상한 응답을 반환함 -> {result}") # 디버깅용
        result = "중립"
    
    return result

#감정 분석 API
@app.post("/analyze_emotion/")
def analyze_emotion_api(request: EmotionRequest):
    """FastAPI 감정 분석 엔드포인트"""
    user_name = request.user_name
    text = request.text
    emotion_result = analyze_emotion(text)
    
    # 감정 기록 저장
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute("INSERT INTO user_emotions (name, emotion, timestamp) VALUES (?, ?, ?)",
            (user_name, emotion_result, timestamp))
    conn.commit()
    conn.close()
    
    return {
        "user": user_name,
        "input_text": text,
        "analyzed_emotion": emotion_result,
        "timestamp": timestamp
    }
    
