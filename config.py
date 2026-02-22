import os

from public_url import get_ngrok_url

ngrok_url = get_ngrok_url()
BASE_URL = ngrok_url if ngrok_url else os.environ.get("BASE_URL", "http://127.0.0.1:5000")
