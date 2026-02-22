import qrcode
import os

from config import BASE_URL


def generate_qr(user_id, base_url=None):
    """
    Generate QR code with only a dynamic emergency URL and save under static/qrcodes.
    Returns static relative image path.
    """
    effective_base = (base_url or BASE_URL).rstrip("/")
    qr_data = f"{effective_base}/emergency/{user_id}"

    os.makedirs("static/qrcodes", exist_ok=True)
    filename = f"static/qrcodes/user_{user_id}.png"

    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(qr_data)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)

    return filename
