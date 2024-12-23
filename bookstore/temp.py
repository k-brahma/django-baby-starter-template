import time
import uuid
import hmac
import hashlib
import base64
import requests
from django.conf import settings


def test_paypay_auth():
    PAYPAY_API_KEY = settings.PAYPAY_API_KEY
    PAYPAY_API_SECRET = settings.PAYPAY_API_SECRET
    url = 'https://stg-api.paypay.ne.jp/v2/payments'

    # nonce は8文字を推奨
    nonce = str(uuid.uuid4())[:8]
    # epoch は秒単位
    epoch = str(int(time.time()))

    method = 'POST'
    path = '/v2/payments'
    content_type = 'application/json'

    # リクエストボディの作成（支払い用）
    payload = {
        "merchantPaymentId": str(uuid.uuid4()),
        "amount": {
            "amount": 1000,
            "currency": "JPY"
        },
        "codeType": "ORDER_QR",
        "orderDescription": "Test Payment",
        "isAuthorization": False,
        "redirectUrl": "https://localhost:8000/bookstore/paypay/success",
        "redirectType": "WEB_LINK",
    }
    request_body = json.dumps(payload)

    # HMAC-SHA256用の文字列生成
    message = (f"{path}\n"
               f"{method}\n"
               f"{nonce}\n"
               f"{epoch}\n"
               f"{content_type}\n"
               f"{request_body}")

    print("\n=== Auth Details ===")
    print(f"Message for HMAC:\n{message}")

    # HMAC-SHA256署名の生成
    signature = hmac.new(
        bytes(PAYPAY_API_SECRET, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).digest()
    mac_data = base64.b64encode(signature).decode()

    # 認証ヘッダーの生成
    auth_header = f"hmac OPA-Auth:{PAYPAY_API_KEY}:{mac_data}:{nonce}:{epoch}:{request_body}"

    headers = {
        'Authorization': auth_header,
        'Content-Type': content_type
    }

    print("\n=== Headers ===")
    print(f"Authorization: {auth_header}")

    response = requests.post(url, headers=headers, data=request_body)
    print("\n=== Response ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response Body:")
    print(response.text)

    return response.json()

