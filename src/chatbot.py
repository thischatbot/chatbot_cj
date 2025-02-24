import sqlite3
from datetime import datetime
from api_key import OPENAI_API_KEY
import openai
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

#OpenAI API 키 설정
openai.api_key = OPENAI_API_KEY

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

def generate_response(user_name, emotion_result):
    """사용자의 감정에 따라 GPT가 다른 반응을 하도록 설정"""
    
    # 감정에 따른 프롬프트 설정
    if emotion_result == "긍정":
        prompt = f"{user_name}님, 기분이 좋아 보이네요! 좋은 하루였나 봐요."
    elif emotion_result == "부정":
        prompt = f"{user_name}님, 힘든 하루였나요? 너무 무리하지 마세요."
    else:  # 중립
        prompt = f"{user_name}님, 오늘 하루 무난했나요?"
        
    # GPT API 호출
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "너는 감정을 고려해 대화하는 개인용 AI 챗봇이다. 한 사람을 대상으로 말해라."},
                {"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content.strip()

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
analyzed_emotion = analyze_emotion(emotion)
print(f"🔍 감정 분석 결과: {analyzed_emotion}")

#감정에 맞는 GPT 응답 생성
emotion_result = generate_response(name, analyzed_emotion)
print(f"🤖 챗봇 응답: {emotion_result}")

#데이터 삽입
cursor.execute("INSERT INTO user_emotions (name, emotion, timestamp) VALUES (?, ?, ?)",
            (name, analyzed_emotion, timestamp))
conn.commit()

print(f"{name}님의 감정 '{emotion}' -> 분석 결과: '{analyzed_emotion}'이(가) 저장되었습니다.")

#최근 감정 기록 불러오기
cursor.execute("SELECT timestamp, emotion FROM user_emotions ORDER BY timestamp ASC")
records = cursor.fetchall()

#저장된 데이터 출력
print("\n📌 저장된 감정 기록:")
for row in records:
    print(f"{row[0]} - {row[1]}")
    
# 감정 데이터를 숫자로 변환 (긍정=1, 중립=0, 부정=-1)
emotion_mapping = {"긍정": 1, "중립": 0, "부정": -1}

# 데이터 변환
timestamps = [row[0] for row in records]
emotions = [emotion_mapping[row[1]] for row in records]

# 그래프 그리기
plt.rc('font', family='NanumBarunGothic') #우분투 환경
#plt.rc('font', family='Malgun Gothic') #윈도우 환경

#경고 메시지 제거 (폰트 관련)
plt.rcParams['axes.unicode_minus'] = False

plt.figure(figsize=(10, 5))
plt.plot(timestamps, emotions, marker='o', linestyle='-', color='b')
plt.xlabel("시간")
plt.ylabel("감정 점수 (-1: 부정, 0: 중립, 1: 긍정)")
plt.title("시간별 감정 변화")
plt.xticks(rotation=45)
plt.grid()
plt.show()