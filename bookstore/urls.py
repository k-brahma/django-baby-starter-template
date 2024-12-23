from django.urls import path

from . import views

app_name = 'bookstore'

urlpatterns = [
    path('checkout', views.checkout, name='checkout'),
    path('checkout-paypay', views.checkout_paypay, name='checkout-paypay'),
    path('success', views.success, name='success'),
    path('error', views.error, name='error'),
    path('cancel', views.cancel, name='cancel'),
    path('create-checkout-session', views.create_checkout_session, name='create_checkout_session'),
    # path('create-checkout-session-paypay', views.create_checkout_session_paypay, name='create_checkout_session-paypay'),
    path('redirect-to-paypay', views.redirect_to_paypay, name='redirect_to_paypay'),
    path('paypay/success', views.paypay_success, name='paypay_success'),
    path('webhook', views.handle_webhook, name='webhook'),
    # path('paypay/webhook', views.paypay_webhook, name='paypay_webhook'),
]
