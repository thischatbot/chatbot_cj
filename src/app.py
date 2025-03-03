import os
import sqlite3
from fastapi import FastAPI
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.runnables.history import RunnableWithMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import HumanMessage, AIMessage

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
        self.load_memory()
    
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
    
# 서버 실행 시 DB 생성
create_database()

