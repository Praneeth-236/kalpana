import requests


def get_ngrok_url():
    try:
        data = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=2).json()
        tunnels = data.get("tunnels", [])
        if not tunnels:
            return None
        return tunnels[0].get("public_url")
    except Exception:
        return None
