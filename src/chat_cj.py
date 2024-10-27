from time import sleep
from openai import OpenAI
import requests
import os
import re
from instruction import instruction_system, instruction_assistant

client = OpenAI()

# Kits.ai TTS
KITS_API_KEY = os.getenv("KITS_API_KEY")

def play_tts(text: str):
    url = "https://arpeggi.io/api/kits/v1/tts"
    voice_model_id = '1508262'  # Cheju ID
    files = {
        'voiceModelId': (None, voice_model_id),
        'inputTtsText': (None, text)
    }
    headers = {'Authorization': f'Bearer {KITS_API_KEY}'}

    # 멀티파트 요청으로 TTS 작업 생성
    response = requests.post(url, files=files, headers=headers)
    tts_job = response.json()

    # 작업 생성 상태 확인
    if response.status_code == 201 and tts_job.get("status") == "running":
        job_id = tts_job["id"]
        print(f"TTS job created with ID: {job_id}. Waiting for completion...")

        # 작업이 완료될 때까지 주기적으로 상태 확인
        status_url = f"https://arpeggi.io/api/kits/v1/tts/{job_id}"
        while True:
            status_response = requests.get(status_url, headers=headers)
            status_data = status_response.json()

            if status_data.get("status") == "running":
                break

# Get input from the user
user_input = input("Enter your message for 'role': 'user': ")

response = client.chat.completions.create(
  model="gpt-4o",
  messages=[
    {
      "role": "system",
      "content": [
        {
          "text": instruction_system,
          "type": "text"
        }
      ]
    },
    {
      "role": "user",
      "content": [
        {
          "text": user_input,
          "type": "text"
        }
      ]
    },
    {
      "role": "assistant",
      "content": [
        {
          "text": instruction_assistant,
          "type": "text"
        }
      ]
    }
  ],
  temperature=0.4,
  max_tokens=2048,
  top_p=0.5,
  frequency_penalty=0,
  presence_penalty=0,
  response_format={
    "type": "text"
  }
)

# Print ChatGPT's response
assistant_response = response.choices[0].message.content
print("Assistant:", assistant_response)

# Use regex to split by '.', '?', or '!' to break into sentences
response_sentences = re.split(r'(?<=[.!?])\s+', assistant_response)

# Pass each sentence to play_tts
for sentence in response_sentences:
    play_tts(sentence)
