import requests
import os

url = "https://arpeggi.io/api/kits/v1/voice-models"

token = os.getenv("KITS_API_KEY")
headers = {"Authorization": f"Bearer {token}"}

response = requests.request("GET", url, headers=headers)

print(response.text)