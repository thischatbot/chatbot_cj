import sqlite3
from datetime import datetime
from api_key import OPENAI_API_KEY
import openai

#OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

def analyze_emotion(text):
    """GPT API를 사용해 감정을 분석하는 함수"""
    prompt = f"다음 문장의 감정을 분석해줘: '{text}'\n'긍정', '부정', '중립' 중 하나로 답해줘."
    
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 감정 분석 전문가야."},
                {"role": "user", "content": prompt}]
    )
    
    result = response.choices[0].message.content.strip()
    return result

#실행 테스트
#print(analyze_emotion("오늘 너무 기분이 좋아!"))

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

#데이터 삽입
cursor.execute("INSERT INTO user_emotions (name, emotion, timestamp) VALUES (?, ?, ?)",
            (name, emotion, timestamp))
conn.commit()

print(f"{name}님의 감정 '{emotion}'이(가) 저장되었습니다.")

#최근 감정 기록 불러오기
cursor.execute("SELECT name, emotion, timestamp FROM user_emotions ORDER BY timestamp DESC")
records = cursor.fetchall()

#저장된 데이터 출력
print("\n📌 저장된 감정 기록:")
for row in records:
    print(f"{row[2]} - {row[0]} : {row[1]}")