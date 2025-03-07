from fastapi import FastAPI, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker, declarative_base
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
DB_URL = os.getenv("DB_URL", "sqlite+aiosqlite:///./emotions.db")

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

class UserEmotion(Base):
    __tablename__ = "user_emotions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    emotion = Column(String, index=True, nullable=False)
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

        new_emotion = UserEmotion(name=user_name, emotion=emotion_result, timestamp=timestamp)
        db.add(new_emotion)
        async with db as session:
            session.add(new_emotion)
            await session.commit()
        await db.commit()

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {e}")

    return {"status": "success", "data": {"user": user_name, "input_text": text, "analyzed_emotion": emotion_result, "timestamp": timestamp}}

# Get User Emotion History
@app.get("/get_memory/{user_name}", response_model=EmotionResponse, summary="Get User Emotion History")
async def get_user_emotions(user_name: str, db: AsyncSession = Depends(get_db)):
    """Fetch last 5 emotion records for a user."""
    records = await db.execute(text(
        "SELECT timestamp, emotion FROM user_emotions WHERE name = :name ORDER BY timestamp DESC LIMIT 5"
        ),
        {"name": user_name}
    )
    result = records.fetchall()

    if not result:
        return {"status": "success", "data": {"user": user_name, "message": "No emotion records found."}}

    return {"status": "success", "data": {"user": user_name, "emotions": [{"timestamp": row[0], "emotion": row[1]} for row in result]}}

# GPT Chatbot API
@app.post("/chat", response_model=EmotionResponse, summary="Chat with AI")
async def chat_with_bot(request: EmotionRequest, with_emotion_analysis: bool = Query(False), db: AsyncSession = Depends(get_db)):
    """AI chatbot with optional emotion analysis."""
    user_name = request.user_name
    user_text = request.text

    # Emotion analysis
    emotion_result = None
    if with_emotion_analysis:
        emotion_result = analyze_emotion(user_text)

    # Fetch past emotions
    past_emotions = await db.execute(text(
        "SELECT timestamp, emotion FROM user_emotions WHERE name = :name ORDER BY timestamp DESC LIMIT 3"),
        {"name": user_name}
    )
    past_emotion_list = past_emotions.fetchall()
    emotion_history = "\n".join([f"{row[0]} - {row[1]}" for row in past_emotion_list])

    # ChatGPT prompt
    prompt = f"""
    You are a supportive AI friend. Consider the user's emotions when responding.

    - Past emotions:
    {emotion_history}

    User input: "{user_text}"
    """

    # OpenAI API Call
    response = openai.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": "You are an AI that understands emotions."}, {"role": "user", "content": prompt}]
    )

    bot_response = response.choices[0].message.content.strip()

    # Save emotion result
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    new_emotion = UserEmotion(name=user_name, emotion=emotion_result, timestamp=timestamp)
    db.add(new_emotion)
    async with db as session:
        session.add(new_emotion)
        await session.commit()
    await db.commit()

    return {"status": "success", "data": {"user": user_name, "input_text": user_text, "analyzed_emotion": emotion_result, "bot_response": bot_response, "timestamp": timestamp}}
