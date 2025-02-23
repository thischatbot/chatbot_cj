import sqlite3
from datetime import datetime
from api_key import OPENAI_API_KEY
import openai

#OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

def analyze_emotion(text):
    """GPT API를 사용해 감정을 분석하는 함수"""
    prompt = f"""다음 문장의 감정을 분석해줘: '{text}'
    반드시 아래 중 하나만 답변해:
    - 긍정
    - 부정
    - 중립
    
    **다른 설명 없이** 위 단어 중 하나만 출력해.
    """
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 감정 분석 전문가야."},
                {"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    
    #혹시라도 GPT가 이상한 응답을 하면 기본값 설정
    if result not in ["긍정", "부정", "중립"]:
        print(f"⚠ 경고: GPT가 이상한 응답을 반환함 -> {result}") # 디버깅용
        result = "중립"
    
    return result

# SQLite DB 연결 (없으면 자동 생성됨)
conn = sqlite3.connect("emotions.db")
cursor = conn.cursor()

# 테이블 생성 (한 번만 실행하면 됨)
cursor.execute("""
CREATE TABLE IF NOT EXISTS user_emotions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    emotion TEXT,
    timestamp TEXT
)               
""")
conn.commit()

# 사용자 입력받기
name = input("이름을 입력하세요: ")
emotion = input("현재 감정을 입력하세요: ")
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S") # 현재 시간 기록

#GPT를 사용한 감정 분석 
analyzed_emotion = analyze_emotion("emotion")

#데이터 삽입
cursor.execute("INSERT INTO user_emotions (name, emotion, timestamp) VALUES (?, ?, ?)",
            (name, analyzed_emotion, timestamp))
conn.commit()

print(f"{name}님의 감정 '{emotion}' -> 분석 결과: '{analyzed_emotion}'이(가) 저장되었습니다.")

#최근 감정 기록 불러오기
cursor.execute("SELECT name, emotion, timestamp FROM user_emotions ORDER BY timestamp DESC")
records = cursor.fetchall()

#저장된 데이터 출력
print("\n📌 저장된 감정 기록:")
for row in records:
    print(f"{row[2]} - {row[0]} : {row[1]}")