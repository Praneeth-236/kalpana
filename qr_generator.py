import qrcode
import os

from config import BASE_URL


def generate_qr(user_id, base_url=None):
    """
    Generate QR code for emergency profile URL and save it under static/qrcodes.
    Returns static relative image path.
    """
    effective_base = (base_url or BASE_URL).rstrip("/")
    url = f"{effective_base}/emergency/{user_id}"

    os.makedirs("static/qrcodes", exist_ok=True)
    filename = f"static/qrcodes/user_{user_id}.png"

    qr = qrcode.make(url)
    qr.save(filename)

    return filename
