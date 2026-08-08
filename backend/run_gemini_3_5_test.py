import os, json
from dotenv import load_dotenv
import httpx

load_dotenv()
key = os.getenv('GEMINI_API_KEY')
model = os.getenv('GEMINI_MODEL')
print('MODEL=', model)
print('KEY_PRESENT=', bool(key))

url = f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
headers = {'x-goog-api-key': key, 'Content-Type': 'application/json'}
payload = {
    'contents': [
        {'role': 'user', 'parts': [{'text': 'Hello from test - short sanity check'}]}
    ],
    'generationConfig': {'temperature': 0.0, 'topP': 0.95, 'maxOutputTokens': 64}
}

with httpx.Client(timeout=30) as client:
    r = client.post(url, headers=headers, json=payload)
    print('STATUS', r.status_code)
    try:
        print(json.dumps(r.json(), indent=2)[:4000])
    except Exception:
        print(r.text[:4000])
