import re
from openai import OpenAI
import os

from enum import Enum

class Emotion(Enum):
    NEUTRAL = "Neutral"
    HAPPY = "Happy"
    SURPRISED = "Surprised"
    SAD = "Sad"
    ANGRY = "Angry"
    
# Set up OpenAI API key
#client = OpenAI()
API_KEY = os.getenv("OPENAI_API_KEY")

def classify_emotion(sentence):
    """Classifies the emotion of a given sentence using OpenAI's API."""
    response = OpenAI().chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are an assistant that classifies emotions of given sentences. Neutral / Happy / Surprised / Sad / Angry" },
            {"role": "user", "content": f"Classify the emotion of the following sentence: '{sentence}'."}
        ]
    )

    # Extract emotion classification from the response
    emotion_text = response.choices[0].message.content
    
    try:
        emotion = Emotion(emotion_text.upper())
    except ValueError:
        # Default to NEUTRAL if the response is unexpected
        emotion = Emotion.NEUTRAL
    
    return emotion