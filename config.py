import os

from public_url import get_ngrok_url

ngrok_url = get_ngrok_url()
BASE_URL = os.environ.get("BASE_URL") or ngrok_url or "http://127.0.0.1:5000"
