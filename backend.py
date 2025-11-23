from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
import os
from datetime import datetime
from random import randint
import smtplib
from email.mime.text import MIMEText

app = FastAPI()

RAZORPAY_WEBHOOK_SECRET = os.getenv("RAZORPAY_WEBHOOK_SECRET", "change_this_secret")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

CODES_DB_PATH = "premium_codes.json"


def load_codes():
    if not os.path.exists(CODES_DB_PATH):
        return {}
    with open(CODES_DB_PATH, "r") as f:
        return json.load(f)


def save_codes(data):
    with open(CODES_DB_PATH, "w") as f:
        json.dump(data, f, indent=2)


def generate_code():
    return str(randint(1000000000, 9999999999))


def send_email(recipient, code):
    msg = MIMEText(f"Your SuperBrain AI Premium Code is: {code}")
    msg["Subject"] = "Your SuperBrain AI Premium Access Code"
    msg["From"] = GMAIL_EMAIL
    msg["To"] = recipient

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
        server.sendmail(GMAIL_EMAIL, recipient, msg.as_string())


def verify_signature(body, received_sig):
    expected = hmac.new(
        RAZORPAY_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, received_sig)


@app.post("/razorpay/webhook")
async def razorpay_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Razorpay-Signature")

    if not signature or not verify_signature(body, signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    payload = await request.json()
    payment = payload["payload"]["payment"]["entity"]

    email = payment.get("email")
    amount = payment.get("amount") / 100
    payment_id = payment.get("id")

    code = generate_code()
    data = load_codes()

    data[code] = {
        "email": email,
        "amount": amount,
        "payment_id": payment_id,
        "created_at": datetime.utcnow().isoformat()
    }
    save_codes(data)

    if email:
        send_email(email, code)

    return {"status": "success"}
