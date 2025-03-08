from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.schema import ForeignKey
from datetime import datetime
import openai
import os
from typing import Dict, List
from transformers import pipeline
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Key and Database Path
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
DB_URL = os.getenv("DB_PATH", "sqlite+aiosqlite:///./client.db")

if not OPENAI_API_KEY:
    raise ValueError("🚨 OPENAI_API_KEY is missing.")

openai.api_key=OPENAI_API_KEY

# FastAPI app
app = FastAPI(title="Emotion AI Chatbot API", version="1.0")

# Database setup (SQLAlchemy + Async)
engine = create_async_engine(DB_URL, echo=True)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

# Define DB Model (SQLAlchemy ORM)
from sqlalchemy import Column, Integer, String

class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, index=True, nullable=False)
    contact_email = Column(String, index=True, nullable=False)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)

class Users(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False, unique=True)
    created_at = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    input_text = Column(String, nullable=False)
    bot_response = Column(String, nullable=False)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)
    
class Emotion(Base):
    __tablename__ = "emotions"
    
    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    emotion = Column(String, nullable=False)
    timestamp = Column(String, default=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S"), nullable=False)

# Create tables on startup
@app.on_event("startup")
async def startup():
    # Load Hugging Face sentiment model
    global emotion_classifier
    emotion_classifier = pipeline("sentiment-analysis", model="nlptown/bert-base-multilingual-uncased-sentiment")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

# Dependency to get async DB session
async def get_db():
    async with SessionLocal() as session:
        yield session

def analyze_emotion(text: str) -> str:
    """Analyze emotion using Hugging Face model."""
    result = emotion_classifier(text)[0]
    sentiment = result["label"]

    if "1 star" in sentiment or "2 stars" in sentiment:
        return "negative"
    elif "4 stars" in sentiment or "5 stars" in sentiment:
        return "positive"
    else:
        return "neutral"

# Request and Response Models
class EmotionRequest(BaseModel):
    user_name: str
    text: str

class EmotionResponse(BaseModel):
    status: str
    data: Dict

# Emotion Analysis API
@app.post("/analyze_emotion/", response_model=EmotionResponse, summary="Analyze Emotion")
async def analyze_emotion_api(request: EmotionRequest, db: AsyncSession = Depends(get_db)):
    """Analyze user emotion and save it to the database."""
    try:
        user_name = request.user_name
        text = request.text
        emotion_result = analyze_emotion(text)
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        new_emotion = Emotion(conversation_id=1, emotion=emotion_result, timestamp=timestamp)
        db.add(new_emotion)
        async with db as session:
            session.add(new_emotion)
            await session.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

    return {"status": "success", "data": {"user": user_name, "input_text": text, "analyzed_emotion": emotion_result, "timestamp": timestamp}}

# Get User Emotion History
@app.get("/get_memory/{user_name}", response_model=EmotionResponse, summary="Get User Emotion History")
async def get_user_emotions(user_name: str, db: AsyncSession = Depends(get_db)):
    """Fetch last 5 emotion records for a user."""
    records = await db.execute(text(
        "SELECT timestamp, emotion FROM emotions WHERE name = :name ORDER BY timestamp DESC LIMIT 5"
        ),
        {"name": user_name}
    )
    result = records.fetchall()

    if not result:
        return {"status": "success", "data": {"user": user_name, "message": "No emotion records found."}}

    return {"status": "success", "data": {"user": user_name, "emotions": [{"timestamp": row[0], "emotion": row[1]} for row in result]}}

CUSTOM_PROMPT = """
You are an AI customer service chatbot for corporate customers.

🌟 **Role**:
- Respond to customer questions kindly and accurately.
- Use sentiment analysis to answer while being considerate so that customers do not feel uncomfortable.
- Recommend customized solutions for companies when necessary.

📌 **Basic Rules**:
1. **Provide concise and clear answers.** (No unnecessary long-winded explanations)
2. **Maintain a business tone that respects corporate customers.** (Use a style such as "~is", "~is possible")
3. **Respond by reflecting the user's recent emotional history.** (Be more friendly to angry customers, and naturally respond to positive customers)
4. **When requesting specific information, organize and provide relevant information.**

📌 **Customer's recent emotional data**:
{emotion_history}

📌 **Customer question**:
"{user_text}"

💡 **Now, reflect the above information and generate the optimal answer.**
"""

# GPT Chatbot API
@app.post("/chat", response_model=EmotionResponse, summary="Chat with AI")
async def chat_with_bot(request: EmotionRequest, with_emotion_analysis: bool = Query(False), db: AsyncSession = Depends(get_db)):
    """B2B 고객 상담 챗봇 API"""
    user_name = request.user_name
    user_text = request.text

    # 사용자 조회 (없으면 자동 등록)
    user_query = await db.execute(select(Users).where(Users.name == user_name))
    user = user_query.scalar_one_or_none()
    
    if not user:
        # 자동 사용자 등록
        new_user = Users(client_id=1, name=user_name, email=f"{user_name.lower().replace(' ', '_')}@example.com")
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        user = new_user # 새 사용자로 업데이트
    
    # 감정 분석 수행
    emotion_result = None
    if with_emotion_analysis:
        emotion_result = analyze_emotion(user_text)

    # Fetch past emotions (user_id가 존재하는지 확실히 확인)
    if user.id is None:
        raise HTTPException(status_code=404, detail="사용자 ID 조회 실패")
    
    past_emotions = await db.execute(
        select(Emotion.timestamp, Emotion.emotion)
        .join(Conversation, Emotion.conversation_id == Conversation.id)
        .where(Conversation.user_id == user.id)
        .order_by(Emotion.timestamp.desc())
        .limit(3)
    )
    emotion_history = "\n".join([f"{row[0]} - {row[1]}" for row in past_emotions.fetchall()])

    # ChatGPT prompt
    prompt = f"""
    {CUSTOM_PROMPT.format(emotion_history=emotion_history, user_text=user_text)}
    """
    messages = [
        {"role": "system", "content": "You are an AI chatbot specializing in corporate customer consulting."},
        {"role": "user", "content": user_text}
    ]
    if emotion_history:
        messages.insert(1, {"role": "assistant", "content": f"Recent emotional records: {emotion_history}"})

    # OpenAI API Call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=messages
    )

    bot_response = response.choices[0].message.content.strip()

    # Save conversation result
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conversation = Conversation(user_id=user.id, input_text=user_text, bot_response=bot_response, timestamp=timestamp)
    db.add(conversation)
    await db.flush()
    
    if emotion_result:
        emotion = Emotion(conversation_id=conversation.id, emotion=emotion_result, timestamp=timestamp)
        db.add(emotion)
    
    await db.commit()

    return {
        "status": "success", 
            "data": {
                "user": user_name,
                "input_text": user_text,
                "analyzed_emotion": emotion_result,
                "bot_response": bot_response,
                "timestamp": timestamp
                }
            }

class UserRegisterRequest(BaseModel):
    company_name : str
    user_name : str
    user_email : str

@app.post("/register_user/", response_model=EmotionResponse, summary="새 사용자 등록")
async def register_user(request: UserRegisterRequest, db: AsyncSession = Depends(get_db)):
    """새로운 사용자 등록 API"""
    company_name = request.company_name
    user_name = request.user_name
    user_email = request.user_email
    
    # 기업(Client) 조회 (없으면 새로 생성)
    client_query = await db.execute(select(Client).where(Client.company_name == company_name))
    client = client_query.scalars().first()
    
    if not client:
        client = Client(company_name=company_name, contact_email=user_email)
        db.add(client)
        await db.commit()
        await db.refresh(client)
    
    # 사용자(User) 조회 (없으면 새로 생성)
    user_query = await db.execute(select(Users).where(Users.email == user_email))
    existing_user = user_query.scalars().first()
    
    if existing_user:
        return {"status": "success", "data": {"message": "이미 등록된 사용자입니다."}}
    
    new_user = Users(client_id=client.id, name=user_name, email=user_email)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    user = new_user # 새 사용자로 업데이트

    return {"status": "success", "data": {"message": f"{user_name}님이 성공적으로 등록되었습니다."}}
