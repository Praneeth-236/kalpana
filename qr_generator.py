from pathlib import Path

import qrcode


BASE_DIR = Path(__file__).resolve().parent
QRCODE_DIR = BASE_DIR / "static" / "qrcodes"


def generate_qr(user_id):
    """
    Generate QR code for emergency profile URL and save it under static/qrcodes.
    Returns absolute image path.
    """
    QRCODE_DIR.mkdir(parents=True, exist_ok=True)

    emergency_url = f"http://localhost:5000/emergency/{user_id}"
    image = qrcode.make(emergency_url)

    file_path = QRCODE_DIR / f"user_{user_id}.png"
    image.save(file_path)
    return file_path
