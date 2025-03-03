import os
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage
from langchain.schema import SystemMessage, HumanMessage

# OpenAI API Key 설정
os.environ["OPENAI_API_KEY"] = "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"

# FASTAPI 앱 생성
app = FastAPI()

# LLM 모델 설정
llm = ChatOpenAI(model="gpt-4")

def create_database():
    """ SQLite DB 생성 및 테이블 세팅 """
    conn = sqlite3.connect("chat_memory.db")
    cursor = conn.cursor()
    
    # memory 테이블 생성 (user_name 별로 대화 내역 저장)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS memory (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT UNIQUE,
        chat_history TEXT
    )
    """)
    
    conn.commit()
    conn.close()
    print("SQLite DB 및 테이블 생성 완료")


# API 요청 모델
class ChatRequest(BaseModel):
    user_name: str
    message: str

#사용자별 대화 기록 관리 (SQLite 적용 가능)
class Chatbot:
    def __init__(self, user_name):
        self.user_name = user_name
        self.session_id = f"session_{user_name}" # 사용자별 session_id 추가
        self.memory = ChatMessageHistory() #대화 기록 저장용
        self.initialize_chatbot_personality()
        self.load_memory()
    
    def initialize_chatbot_personality(self):
        """처음 실행하는 경우, 챗봇의 성격을 강제로 메모리의 저장"""
        intro_message = (
            "나는 감성적이고 따뜻한 AI 채주야."
            "네 감정을 깊이 이해하고, 언제나 네 편에서 함께할게."
            "잔잔한 위로와 너드미 가득한 대화로, 너에게 소울메이트가 되어줄게."
        )
        
        # 사용자의 입력 없이 기본 성격을 대화 히스토리에 추가
        self.memory.add_user_message("기본 설정")  
        self.memory.add_ai_message(intro_message)
    
    def get_session_history(self, session_id):
        """LangChain에서 요구하는 세션 히스토리 함수"""
        return self.memory
    
    def save_memory(self):
        """ 대화 기록을 SQLite에 저장 """
        conn = sqlite3.connect("chat_memory.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM memory WHERE user_name=?", (self.user_name,))
        cursor.execute("INSERT INTO memory (user_name, chat_history) VALUES (?, ?)",
                    (self.user_name, str(self.memory.messages)))
        conn.commit()
        conn.close()
    
    def load_memory(self):
        """ SQLite에서 대화 기록 불러오기 """
        conn = sqlite3.connect("chat_memory.db")
        cursor = conn.cursor()
        cursor.execute("SELECT chat_history FROM memory WHERE user_name=?", (self.user_name,))
        result = cursor.fetchone()
        conn.close()
        if result:
            self.memory.messages = eval(result[0], {"HumanMessage": HumanMessage, "AIMessage": AIMessage}) # 저장된 메시지 복원
            
    def chat(self, user_input):
        """ 최신 LangChain 방식으로 대화 실행 """
        agent = RunnableWithMessageHistory(llm, get_session_history=self.get_session_history) #callable 함수 전달
        response = agent.invoke(user_input, config={"configurable": {"session_id": self.session_id}}) #invoke() 사용
        
        self.memory.add_user_message(user_input)
        self.memory.add_ai_message(response)
        self.save_memory()
        return response.content

#FastAPI 엔드포인트
@app.post("/chat")
def chat_endpoint(request: ChatRequest):
    chatbot = Chatbot(user_name=request.user_name)
    response = chatbot.chat(request.message)
    return {"user": request.user_name, "message": request.message, "response": response}


# 감정 분석을 위한 LLM 모델
emotion_model = ChatOpenAI(model_name="gpt-4")

def analyze_emotion(text):
    """GPT를 활용한 감정 분석"""
    prompt = [
        SystemMessage(content="사용자의 감정을 분석해줘. 감정을 '긍정', '중립', '부정' 중 하나로 분류하고, 간단한 이유를 설명해."),
        HumanMessage(content=text)
    ]
    
    response = emotion_model.invoke(prompt)
    return response.content

class EmotionRequest(BaseModel):
    text: str

@app.post("/analyze_emotion")
def analyze_emotion_endpoint(request: EmotionRequest):
    """ 감정 분석 API """
    emotion_result = analyze_emotion(request.text)
    return {"text": request.text, "emotion": emotion_result}

def generate_coaching_response(user_text):
    """감정 분석 후, 사용자에게 맞춤형 AI 코칭 제공"""
    emotion_result = analyze_emotion(user_text) # 감정 분석 실행
    prompt = [
        SystemMessage(content=f"사용자가 '{emotion_result}'감정을 보이고 있어. 상황에 맞게 적절한 코칭 메시지를 제공해."),
        HumanMessage(content=user_text)
    ]
    
    coaching_response = emotion_model.invoke(prompt)
    return {"emotion": emotion_result, "coaching": coaching_response.content}

class CoachingRequest(BaseModel):
    text: str

@app.post("/coach")
def coach_endpoint(request: CoachingRequest):
    """ AI 코칭 API """
    coaching_result = generate_coaching_response(request.text)
    return {
        "text": request.text,
        "emotion": coaching_result["emotion"],
        "coaching": coaching_result["coaching"]
    }
# 서버 실행 시 DB 생성
create_database()

