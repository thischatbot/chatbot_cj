import re
from openai import OpenAI
import os

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
    emotion = response.choices[0].message.content
    #emotion = response['choices'][0]['message']['content'].strip()
    return emotion