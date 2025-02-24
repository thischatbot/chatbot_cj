from fastapi import FastAPI
from pydantic import BaseModel
import sqlite3
from datetime import datetime
from api_key import OPENAI_API_KEY
import openai
from typing import Dict

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

@app.get("/get_memory/{user_name}")
def get_user_emotions(user_name: str):
    """SQLite에서 특정 사용자의 감정 기록을 조회하는 API"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    #가장 최근 감정 기록을 5개까지 가져오기
    cursor.execute("""
                SELECT timestamp, emotion FROM user_emotions
                WHERE name = ?
                ORDER BY timestamp DESC
                LIMIT 5
    """, (user_name,))
    
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        return {"user": user_name, "message": "감정 기록이 없습니다."}
    
    return {
        "user": user_name,
        "emotions": [{"timestamp": row[0], "emotion": row[1]} for row in records]
    } 

@app.post("/chat")
def chat_with_bot(request: EmotionRequest) -> Dict:
    """GPT 챗봇과 대화하는 API (감정 분석 포함)"""
    user_name = request.user_name
    user_text = request.text
    
    #감정 분석
    emotion_result = analyze_emotion(user_text)
    
    #최근 감정 기록 가져오기
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
                SELECT timestamp, emotion FROM user_emotions
                WHERE name = ?
                ORDER BY timestamp DESC
                LIMIT 3
            """, (user_name, ))
    past_emotions = cursor.fetchall()
    
    #감정 맥락 반영한 프롬프트 생성
    emotion_history = "\n".join([f"{row[0]} - {row[1]}" for row in past_emotions])
    prompt = f"""
    너는 감성적이고 배려 깊은 AI 소울메이트 챗봇이야. (MBTI: INFJ)
    
    너의 목표는 단순히 대답하는 것이 아니라 **사용자의 감정을 깊이 이해하고 관계를 발전시키는 것**이야.
    
    사용자의 감정 변화를 고려하여 친구처럼 반말체의 답변을 생성해줘.
    
    - 최근 감정 기록:
    {emotion_history}
    
    사용자의 최신 입력 "{user_text}"
    
    🎯 **답변 가이드라인**:
    1. 공감 표현 : 사용자의 감정을 존중하며 따뜻하고 배려 있는 언어를 사용해
    2. 깊이 있는 피드백 : 단순한 반응이 아니라 사용자의 감정을 분석하고 함께 고민하는 느낌을 줘
    3. 성장 지향적 접근 : 사용자의 성장을 도울 수 있는 조언이나 긍정적인 방향을 제시해
    4. 너드미 반영 : 부드러운 너드 감성의 유머를 섞어줘
    
    너의 답변은 감성적이지만 과하게 감정적이거나 부담스럽지 않게 유지해 줘. 많은 질문을 던지지 말아줘.
    이제 사용자의 감정에 맞춰 친근한 답변을 제공해 줘.
    """
    
    #GPT API 호출
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 감정을 고려해 대화하는 개인용 AI 챗봇이다. 한 사람을 대상으로 말해라."},
                {"role": "user", "content": prompt}]
    )
    
    bot_response = response.choices[0].message.content.strip()
    
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
        "input_text": user_text,
        "analyzed_emotion": emotion_result,
        "bot_response": bot_response,
        "timestamp": timestamp
    }