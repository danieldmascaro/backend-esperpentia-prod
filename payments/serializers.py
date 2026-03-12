from rest_framework import serializers

from .models import Payment


class CreatePaymentIntentSerializer(serializers.Serializer):
    order_id = serializers.UUIDField()
    provider = serializers.ChoiceField(choices=["mockpay", "webpay"], default="mockpay")


class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = (
            "id",
            "order",
            "provider",
            "status",
            "amount",
            "currency",
            "provider_reference",
            "created_at",
            "updated_at",
        )


class PaymentWebhookSerializer(serializers.Serializer):
    provider_reference = serializers.CharField()
    status = serializers.ChoiceField(choices=Payment.Status.choices)


class WebpayCommitSerializer(serializers.Serializer):
    token_ws = serializers.CharField()


class WebpayRefundSerializer(serializers.Serializer):
    token_ws = serializers.CharField()
    amount = serializers.DecimalField(max_digits=12, decimal_places=0)
