import logging
from urllib.parse import urlencode
from uuid import uuid4

from django.conf import settings
from django.http import HttpResponseRedirect, JsonResponse

logger = logging.getLogger(__name__)


class PaymentsExceptionRescueMiddleware:
    """
    Avoid opaque Django 500 HTML pages on payment flows.
    Returns a controlled payload/redirect with error_id for debugging.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        try:
            return self.get_response(request)
        except Exception as exception:
            return self._build_rescue_response(request, exception)

    def _build_rescue_response(self, request, exception):
        path = request.path or ""

        is_payment_or_checkout_path = path.startswith("/payments/") or path.startswith("/checkout/")
        if not is_payment_or_checkout_path:
            raise exception

        error_id = uuid4().hex[:12]
        logger.exception(
            "Unhandled exception in payment/checkout endpoint. error_id=%s path=%s",
            error_id,
            path,
        )

        if path.startswith("/payments/webpay/return"):
            base_url = getattr(
                settings,
                "WEBPAY_FRONTEND_RESULT_URL",
                "http://localhost:5173/checkout/resultado",
            )
            separator = "&" if "?" in base_url else "?"
            query = urlencode(
                {
                    "outcome": "failed",
                    "reason": "unhandled_exception",
                    "error_id": error_id,
                }
            )
            return HttpResponseRedirect(f"{base_url}{separator}{query}")

        if path.startswith("/payments/create-intent"):
            return JsonResponse(
                {
                    "detail": f"Error interno en create-intent. ref={error_id}",
                    "reason": "unhandled_exception",
                },
                status=400,
            )

        if path.startswith("/payments/webpay/commit"):
            return JsonResponse(
                {
                    "detail": f"Error interno en webpay commit. ref={error_id}",
                    "reason": "unhandled_exception",
                },
                status=400,
            )

        if path.startswith("/checkout/"):
            return JsonResponse(
                {
                    "detail": f"Error interno en checkout. ref={error_id}",
                    "reason": "unhandled_exception",
                },
                status=400,
            )

        return JsonResponse(
            {
                "detail": f"Error interno en endpoint de pagos. ref={error_id}",
                "reason": "unhandled_exception",
            },
            status=400,
        )
