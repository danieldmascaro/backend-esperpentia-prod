from django.urls import path

from .api import (
    PaymentCreateIntentAPIView,
    PaymentWebhookAPIView,
    WebpayCommitAPIView,
    WebpayRefundAPIView,
    WebpayStatusAPIView,
)

urlpatterns = [
    path("create-intent/", PaymentCreateIntentAPIView.as_view(), name="payments-create-intent"),
    path("webhook/", PaymentWebhookAPIView.as_view(), name="payments-webhook"),
    path("webpay/commit/", WebpayCommitAPIView.as_view(), name="payments-webpay-commit"),
    path("webpay/status/", WebpayStatusAPIView.as_view(), name="payments-webpay-status"),
    path("webpay/refund/", WebpayRefundAPIView.as_view(), name="payments-webpay-refund"),
]
