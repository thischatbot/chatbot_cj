import os
from pydantic import BaseModel
from sqlalchemy import text, Column, Integer, String
from sqlalchemy import delete, insert
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.schema import ForeignKey
from fastapi import FastAPI, Depends, HTTPException, Query
from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.schema import BaseRetriever
from langchain.schema import HumanMessage, AIMessage
from langchain.schema import SystemMessage, HumanMessage

from langchain.vectorstores import FAISS
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.chains.retrieval_qa.base import RetrievalQA
from langchain.docstore.document import Document

from transformers import pipeline
from dotenv import load_dotenv
from typing import Dict, List
import json
import datetime

# Load environment variables
load_dotenv()

# API Key and Database Path
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_PATH", "sqlite+aiosqlite:///./emotions.db")

if not OPENAI_API_KEY:
    raise ValueError("🚨 OPENAI_API_KEY is missing.")
OPENAI_API_KEY
#FastAPI app
app = FastAPI(title="Emotion AI Chatbot API", version="1.0")

# Database setup (SQLAlchemy + Async)
engine = create_async_engine(DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(Integer, primary_key=True, index=True)

class EmotionHistory(Base):
    __tablename__ = "emotion_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, nullable=False)
    emotion = Column(String, nullable=False)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)
class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    emotion = Column(String, nullable=False)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)

class Memory(Base):
    __tablename__ = "memory"
    
    id = Column(Integer, primary_key=True, index=True)
    user_name = Column(String, unique=True, nullable=False)
    chat_history = Column(String, nullable=False)

# LLM 모델 설정
llm = ChatOpenAI(model="gpt-4")

@app.on_event("startup")
async def startup():
    #Load Hugging Face sentiment model
    global emotion_classifier
    emotion_classifier = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all, checkfirst=True)

async def get_db():
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()

async def save_emotion(user_name, emotion, db: AsyncSession):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    new_emotion = EmotionHistory(
        user_name = user_name,
        emotion=emotion,
        timestamp=timestamp
    )
    
    db.add(new_emotion)
    await db.commit()
    await db.refresh(new_emotion)
    
async def get_recent_emotions(user_name, db: AsyncSession, limit=5):
    result = await db.execute(
        select(EmotionHistory)
        .where(EmotionHistory.user_name == user_name)
        .order_by(EmotionHistory.timestamp.desc())
        .limit(limit)
    )
    emotions = result.scalars().all() or []
    
    return [
        {
            "emotion": emotion.emotion,
            "timestamp": emotion.timestamp
        }
        for emotion in emotions
    ]

# API 요청 모델
class ChatRequest(BaseModel):
    user_name: str
    message: str
    
class ChatResponse(BaseModel):
    user_name: str
    data: Dict

#사용자별 대화 기록 관리 (SQLite 적용 가능)
class Chatbot:
    def __init__(self, user_name):
        self.user_name = user_name
        self.session_id = f"session_{user_name}" # 사용자별 session_id 추가
        self.memory = ChatMessageHistory() #대화 기록 저장용
        self.memory_buffer : ConversationBufferMemory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
    
        if not self.memory_buffer.chat_memory.messages:
            self.set_chatbot_personality()
    
    async def async_init(self, db: AsyncSession):
        await self.load_memory(db)
        if not self.memory.messages:
            self.set_chatbot_personality()
    
    def set_chatbot_personality(self):
        """챗봇의 성격을 강제로 저장"""
        intro_message = (
            "나는 감성적이고 따뜻한 AI 채주야."
            "네 감정을 깊이 이해하고, 언제나 네 편에서 함께할게."
            "잔잔한 위로와 너드미 가득한 대화로, 너에게 소울메이트가 되어줄게."
            "난 반말, 구어체로 말해."
        )
        
        # 성격 메시지가 이미 추가되어 있는지 확인 후 중복 추가 방지
        if not any(isinstance(msg, SystemMessage) for msg in self.memory_buffer.chat_memory.messages):
            system_message = SystemMessage(content="기본 설정")
            ai_message = AIMessage(content=intro_message)
            self.memory_buffer.chat_memory.messages.extend([system_message, ai_message])
    
    def get_session_history(self, session_id):
        """LangChain에서 요구하는 세션 히스토리 함수"""
        return self.memory
    
    async def save_memory(self, db: AsyncSession):
        """대화 기록을 SQLAlchemy 기반 DB에 저장"""
        # 기존 기록 삭제
        await db.execute(delete(Memory).where(Memory.user_name == self.user_name))
        
        # Langchain의 BaseMessage 객체는 JSON 직렬화 불가 → dict로 변환 후 저장
        messages = [
            {
                "type": type(msg).__name__,
                "content": msg.content
            }
            for msg in self.memory_buffer.chat_memory.messages
        ]
        
        # 새 기록 저장
        new_memory = Memory(
            user_name=self.user_name,
            chat_history=json.dumps(messages)
        )
        db.add(new_memory)
        await db.commit()
        await db.refresh(new_memory)

    
    async def load_memory(self, db: AsyncSession):
        """SQLAlchemy에서 대화 기록 불러오기"""
        result = await db.execute(
            select(Memory.chat_history).where(Memory.user_name == self.user_name)
        )
        record = result.scalar()

        if record:
            try:
                # 기존 성격 메시지가 있으면 덮어쓰지 않음
                loaded_messages = json.loads(record)
                self.memory_buffer.chat_memory.messages = [
                    AIMessage(content=msg["content"]) if msg["type"] == "AIMessage" 
                    else HumanMessage(content=msg["content"]) if msg["type"] == "HumanMessage"
                    else SystemMessage(content=msg["content"]) if msg["type"] == "SystemMessage"
                    else None
                    for msg in loaded_messages
                ]

                # 성격 메시지가 없으면 기본 설정 추가
                if not any(isinstance(msg, SystemMessage) for msg in self.memory_buffer.chat_memory.messages):
                    self.set_chatbot_personality()
                    
            except json.JSONDecodeError:
                self.memory_buffer.chat_memory.messages = []
                self.set_chatbot_personality()
        else:
            # 기록이 없으면 성격 설정
            self.set_chatbot_personality()

                
    
    async def chat(self, user_input, db: AsyncSession):
        """최신 LangChain 방식으로 대화 실행"""
        await self.load_memory(db)  # 대화 시작 전에 히스토리 로드
        
        # 사용자 입력 추가
        self.memory_buffer.chat_memory.messages.append(HumanMessage(content=user_input))
        
        retriever = await setup_faiss_rag(db)
        qa_chain = RetrievalQA.from_chain_type(llm, retriever=retriever, memory=self.memory_buffer)
        
        docs = retriever.get_relevant_documents(user_input)
        
        if docs:
            response = qa_chain.run(user_input)
        else:
            response = llm(user_input).content
        
        # AI 응답 추가
        self.memory_buffer.chat_memory.messages.append(AIMessage(content=response))
        
        # 저장 전 성격 메시지 유지
        await self.save_memory(db)
        
        return response



class EmotionRequest(BaseModel):
    user_name: str
    text: str
    
class EmotionResponse(BaseModel):
    status: str
    data: Dict

# GPT + Langchain Chatbot API
@app.post("/chat", response_model=EmotionResponse, summary="Chat with AI")
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_db)):
    chatbot = Chatbot(user_name=request.user_name)
    await chatbot.async_init(db)
    
    #사용자 감정 분석
    emotion_result = analyze_emotion(request.message)
    await save_emotion(request.user_name, emotion_result, db) # 감정 저장
    
    #최근 감정 변화 가져오기
    recent_emotions = await get_recent_emotions(request.user_name,db)
    
    #최근 대화 기록 불러오기
    #chatbot.load_memory()
    #conversation_history = chatbot.memory.messages
    
    #연속된 부정 감정 감지 (최근 3개 중 2개 이상이 "부정"이면 경고)
    recent_negative_emotions = [e for e in recent_emotions if "super negative" in e.get("emotion")]
    if len(recent_negative_emotions) >= 2:
        warning_message = f"요즘 계속 힘들어 보이네, 조금 쉬면서 자신을 돌보는 게 중요해. ({', '.join([e['timestamp'] for e in recent_negative_emotions])})"
    else:
        warning_message = None
    
    #최종 GPT 응답 생성
    prompt_with_emotion_history = f"사용자 입력:{request.message}\n (참고: 최근 감정 변화 {recent_emotions})"
    
    response = await chatbot.chat(prompt_with_emotion_history, db)

    return {
        "status": "success",
        "data": {
            "user": request.user_name,
            "message": request.message,
            "emotion" : emotion_result,
            "recent_emotions": recent_emotions,
            "warning": warning_message,
            "response": response
        }
    }


# 감정 분석을 위한 LLM 모델
emotion_model = ChatOpenAI(model_name="gpt-4")

def analyze_emotion(text):
    """Analyze emotion using Hugging Face model."""
    if not text.strip():
        return "neutral"  # 빈 입력일 경우 중립 처리
    
    try:
        result = emotion_classifier(text)[0]
        sentiment = result.get("label", "").lower()
        
        if "1 star" in sentiment:
            return "super negative"
        elif "2 stars" in sentiment:
            return "negative"
        elif "3 stars" in sentiment:
            return "neutral"
        elif "4 stars" in sentiment:
            return "positive"
        elif "5 stars" in sentiment:
            return "super positive"
        else:
            # 예상되지 않은 값이 반환될 경우 기본값 처리
            return "neutral"
    
    except Exception as e:
        # 예외 발생 시 기본값 반환
        print(f"Error in emotion analysis: {e}")
        return "neutral"


# Emotion Analysis API
@app.post("/analyze_emotion/", response_model=EmotionResponse, summary="Analyze Emotion")
async def analyze_emotion_endpoint(request: EmotionRequest, db: AsyncSession = Depends(get_db)):
    """ Analyze user emotion and save it to the database """
    try:
        user_name = request.user_name
        text = request.text
        emotion_result = analyze_emotion(request.text)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_emotion = Emotion(conversation_id=1, emotion=emotion_result, timestamp=timestamp)
        db.add(new_emotion)
        await db.commit()
        await db.refresh(new_emotion)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")
        
    return {
        "status": "success",
        "data": {
            "user": user_name,
            "input_text": text,
            "analyzed_emotion": emotion_result,
            "timestamp": timestamp
        }
    }

def generate_coaching_response(user_text):
    """감정 분석 후, 사용자에게 맞춤형 AI 코칭 제공"""
    emotion_result = analyze_emotion(user_text) # 감정 분석 실행
    prompt = [
        SystemMessage(content=f"사용자가 '{emotion_result}'감정을 보이고 있어. 감정 강도에 맞게 적절한 코칭 메시지를 제공해."),
        HumanMessage(content=user_text)
    ]
    
    coaching_response = emotion_model(prompt)
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


#RAG를 위한 FAISS 벡터 DB 설정
async def setup_faiss_rag(db: AsyncSession):
    """ 대화 기록을 벡터화하여 저장 """
    result = await db.execute(select(Memory.user_name, Memory.chat_history))
    data = result.fetchall()
    
    documents = []
    for row in data:
        user_name, chat_history = row
        emotion = analyze_emotion(chat_history)
        doc = Document(page_content=chat_history, metadata={"user": user_name, "emotion": emotion})
        documents.append(doc)

    if not documents:
        class EmptyRetriever(BaseRetriever):
            def get_relevant_documents(self, query : str):
                return []
        return EmptyRetriever()
    
    vectorstore = FAISS.from_documents(documents, OpenAIEmbeddings())
    return vectorstore.as_retriever()