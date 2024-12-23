import base64
import hashlib
import hmac
import json
import time
import uuid

import requests
import stripe
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import redirect, render, resolve_url
from django.views.decorators.csrf import csrf_exempt

from config import settings

stripe.api_key = settings.STRIPE_KEY_SECRET


def test_paypay_auth():
    PAYPAY_API_KEY = settings.PAYPAY_API_KEY
    PAYPAY_API_SECRET = settings.PAYPAY_API_SECRET
    url = 'https://stg-api.paypay.ne.jp/v2/payments'

    # 認証情報の生成と出力
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())
    method = 'GET'
    path = '/v2/payments'
    content_type = 'application/json'

    # 署名用メッセージの構築と表示
    message = f"{method}\n{path}\n{content_type}\n\n{nonce}\n{timestamp}"
    print("\n=== Request Details ===")
    print(f"Message for signature:\n{message}")
    print(f"Message bytes: {bytes(message, 'utf-8')}")

    # 署名の作成と表示
    signature = hmac.new(
        bytes(PAYPAY_API_SECRET, 'utf-8'),
        bytes(message, 'utf-8'),
        hashlib.sha256
    ).digest()
    signature_base64 = base64.b64encode(signature).decode()
    print(f"\nSignature (base64): {signature_base64}")

    # ヘッダーの構築と表示
    headers = {
        'Content-Type': content_type,
        'X-API-KEY': PAYPAY_API_KEY,
        'X-NONCE': nonce,
        'X-TIMESTAMP': timestamp,
        'X-SIGNATURE': signature_base64,
    }
    print("\n=== Headers ===")
    for key, value in headers.items():
        print(f"{key}: {value}")

    # リクエストの送信とレスポンスの詳細表示
    response = requests.get(url, headers=headers)
    print("\n=== Response ===")
    print(f"Status Code: {response.status_code}")
    print(f"Response Headers:")
    for key, value in response.headers.items():
        print(f"{key}: {value}")
    print(f"\nResponse Body:")
    print(json.dumps(response.json(), indent=2))

    return response.json()

def checkout(request):
    return render(request, "checkout.html")


def checkout_paypay(request):
    intent = stripe.PaymentIntent.create(
        amount=2000,  # 商品の価格（最小単位）
        currency=settings.STRIPE_CURRENCY,
        automatic_payment_methods={
            'enabled': True,
        },
    )

    return render(request, "checkout_paypay.html", {
        'client_secret': intent.client_secret,
        'STRIPE_PUBLISHABLE_KEY': settings.STRIPE_KEY_PUBLIC,
    })


def success(request):
    return render(request, "success.html")


def cancel(request):
    return render(request, "cancel.html")


@csrf_exempt
def create_checkout_session(request):
    MY_DOMAIN = f'{request.scheme}://{request.get_host()}'
    PRICE_ID = "price_1QLgOXJt0UbzYBEEdbsoB3zx"  # "あなたの値段ID"
    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    'price': PRICE_ID,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            payment_method_types=['card', 'external_paypay'],  # PayPayを追加
            currency=settings.STRIPE_CURRENCY,  # PayPayには必須
            success_url=MY_DOMAIN + '/bookstore/success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url=MY_DOMAIN + '/bookstore/cancel',
        )
        print("決済ページのURLはこれ →" + checkout_session.url)
        return redirect(checkout_session.url)
    except Exception as e:
        print("エラー内容：" + str(e))
        return HttpResponse("Error: " + str(e))


def create_paypay_payment():
    PAYPAY_API_KEY = settings.PAYPAY_API_KEY
    PAYPAY_API_SECRET = settings.PAYPAY_API_SECRET

    url = 'https://stg-api.paypay.ne.jp/v2/payments'

    # タイムスタンプをミリ秒単位で取得
    timestamp = str(int(time.time() * 1000))
    nonce = str(uuid.uuid4())

    # リクエストペイロード
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

    # 署名の作成
    body = json.dumps(payload)
    method = 'POST'
    path = '/v2/payments'

    content_type = "application/json"
    message = f"{method}\n{path}\n{content_type}\n{body}\n{nonce}\n{timestamp}"
    signature = hmac.new(bytes(PAYPAY_API_SECRET, 'utf-8'), bytes(message, 'utf-8'), hashlib.sha256).digest()
    signature_base64 = base64.b64encode(signature).decode()

    headers = {
        'Content-Type': 'application/json',
        'X-API-KEY': PAYPAY_API_KEY,
        'X-NONCE': nonce,
        'X-TIMESTAMP': timestamp,
        'X-SIGNATURE': signature_base64,
    }

    # リクエストの送信
    response = requests.post(url, data=body, headers=headers)

    if response.status_code == 200:
        data = response.json()
        return data['data']['url']
    else:
        # エラー処理
        print(response.text)
        return resolve_url('bookstore:error')


def error(request):
    return render(request, "error.html")


def redirect_to_paypay(request):
    # PayPay の決済ページ URL を生成
    paypay_redirect_url = create_paypay_payment()
    return redirect(paypay_redirect_url)


def paypay_success(request):
    # PayPay からのパラメータを取得
    payment_id = request.GET.get('paymentId')

    # 決済の検証（必要に応じて）および Stripe に決済成功を通知
    if payment_id:
        # Stripe の PaymentIntent ID を使って通知する
        # （ここでは PaymentIntent ID を適切に追跡・保存しておく必要があります）
        payment_intent_id = request.GET.get('payment_intent_id')
        if payment_intent_id:
            notify_stripe_payment_success(payment_intent_id)

    return render(request, 'success.html')


def notify_stripe_payment_success(payment_intent_id):
    # Stripe シークレットキーを設定
    stripe.api_key = settings.STRIPE_KEY_SECRET

    try:
        # PaymentIntent を更新して支払いが成功したことを通知
        stripe.PaymentIntent.modify(
            payment_intent_id,
            metadata={
                'external_payment_status': 'succeeded',
                'payment_method': 'paypay'
            },
        )
        print("Stripe PaymentIntent が更新されました。")
    except stripe.error.StripeError as e:
        # エラーハンドリング
        print(f"Stripe エラー: {str(e)}")


@csrf_exempt
def handle_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE', '')
    event = None

    try:
        # Stripeが送ってきたものか判定
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    except ValueError:
        # Payloadが変な時
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError:
        # Stripeでない第三者が不正に送ってきた時
        return HttpResponse(status=400)

    # eventのtypeによって、好きなように分岐
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        metadata = payment_intent["metadata"]
        print('決済が完了しました。ここで処理を行います。')
        print("決済の詳細情報→" + str(payment_intent))
        print("指定したメタデータの取り出し→" + str(metadata))
    else:
        event_type = event['type']
        print(f'Event type {event_type}')

    return HttpResponse(status=200)
