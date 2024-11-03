import json
from pathlib import Path
from openai import OpenAI
import os
import re
from instruction import instruction_system, instruction_assistant

import pyaudio
from pydub import AudioSegment
import wave

client = OpenAI()

# Kits.ai TTS
KITS_API_KEY = os.getenv("KITS_API_KEY")

def play_mp3(file_path):
    # Load the MP3 file and convert to WAV in memory
    audio = AudioSegment.from_mp3(file_path)
    wav_data = audio.export(format="wav")

    # Open the WAV data with wave module to get params
    wav_data.seek(0)
    with wave.open(wav_data, 'rb') as wf:
        # Set up PyAudio stream
        p = pyaudio.PyAudio()
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # Read data in chunks and play
        chunk_size = 1024
        data = wf.readframes(chunk_size)
        while data:
            stream.write(data)
            data = wf.readframes(chunk_size)

        # Close and terminate the stream
        stream.stop_stream()
        stream.close()
        p.terminate()

def run_tts(text: str):
#    url = "https://arpeggi.io/api/kits/v1/tts"
#    voice_model_id = '1508262'  # Cheju ID
#    files = {
#        'voiceModelId': (None, voice_model_id),
#        'inputTtsText': (None, text)
#    }
#    headers = {'Authorization': f'Bearer {KITS_API_KEY}'}
#
#    # 멀티파트 요청으로 TTS 작업 생성
#    response = requests.post(url, files=files, headers=headers)
#    tts_job = response.json()
#
#    # 작업 생성 상태 확인
#    if response.status_code == 201 and tts_job.get("status") == "running":
#        job_id = tts_job["id"]
#        print(f"TTS job created with ID: {job_id}. Waiting for completion...")
#
#        # 작업이 완료될 때까지 주기적으로 상태 확인
#        status_url = f"https://arpeggi.io/api/kits/v1/tts/{job_id}"
#        while True:
#            status_response = requests.get(status_url, headers=headers)
#            status_data = status_response.json()
#
#            if status_data.get("status") == "running":
#                break

######
  speech_file_path = Path(__file__).parent / "cj_speech.mp3"
  response = client.audio.speech.create(model="tts-1",
                              voice="onyx", 
                              response_format="mp3",
                              input=text)
  response.stream_to_file(speech_file_path)
  play_mp3(speech_file_path)
# Get input from the user
user_input = input("Enter your message for 'role': 'user': ")

with client.chat.completions.with_streaming_response.create(
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
) as response :
  # Collect all lines into a single list
  lines = []

  # Gather all lines of the response
  for line in response.iter_lines():
      if line:  # Ignore empty lines
          lines.append(line.strip())

  # Join all lines into a single JSON string
  json_string = "\n".join(lines)

  # Now parse the entire JSON object once it's complete
  try:
      response_data = json.loads(json_string)
      
      # Access the assistant's message content
      assistant_response_text = response_data['choices'][0]['message']['content']
      
      # Print or further process the response
      print(assistant_response_text)
  except json.JSONDecodeError as e:
      print("Error decoding JSON:", e)
    
response_sentences = re.split(r'(?<=[.!?])\s+', assistant_response_text)

# Pass each sentence to run_tts
for sentence in response_sentences:
  print(sentence)
  run_tts(sentence)
