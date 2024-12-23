import base64
import hashlib
import hmac
import uuid
from datetime import datetime
import pytz
import requests
import json
from django.conf import settings


def test_paypay_auth():
    PAYPAY_API_KEY = settings.PAYPAY_API_KEY
    PAYPAY_API_SECRET = settings.PAYPAY_API_SECRET
    MERCHANT_ID = settings.PAYPAY_MERCHANT_ID

    base_url = 'https://stg-api.paypay.ne.jp/v2/codes/payments'
    url = f"{base_url}?assumeMerchant={MERCHANT_ID}"

    epoch = str(int(datetime.now(pytz.UTC).timestamp()))
    nonce = str(uuid.uuid4())[:8]

    # POSTリクエスト用のペイロード
    payload = {
        "merchantPaymentId": str(uuid.uuid4()),
        "amount": {
            "amount": 1,
            "currency": "JPY"
        },
        "codeType": "ORDER_QR",
        "orderDescription": "Test Payment",
        "isAuthorization": False
    }

    method = 'POST'
    path = '/v2/codes/payments'
    content_type = 'application/json;charset=UTF-8'

    # ペイロードのハッシュ化
    body_str = json.dumps(payload)
    md5 = hashlib.md5()
    md5.update(content_type.encode('utf-8'))
    md5.update(body_str.encode('utf-8'))
    hash_value = base64.b64encode(md5.digest()).decode()

    message = (f"{path}\n"
               f"{method}\n"
               f"{nonce}\n"
               f"{epoch}\n"
               f"{content_type}\n"
               f"{hash_value}")

    print("\n=== Auth Details ===")
    print(f"Message for HMAC:\n{message}")

    signature = hmac.new(
        bytes(PAYPAY_API_SECRET, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).digest()
    mac_data = base64.b64encode(signature).decode()

    auth_header = f"hmac OPA-Auth:{PAYPAY_API_KEY}:{mac_data}:{nonce}:{epoch}:{hash_value}"

    headers = {
        'Authorization': auth_header,
        'X-ASSUME-MERCHANT': MERCHANT_ID,
        'Accept': 'application/json;charset=UTF-8',
        'Content-Type': content_type
    }

    print("\n=== Headers ===")
    for key, value in headers.items():
        print(f"{key}: {value}")

    response = requests.post(url, headers=headers, json=payload)
    print("\n=== Response ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"{key}: {value}")
    print(f"\nResponse Body:")
    print(response.text)

    return response.json()