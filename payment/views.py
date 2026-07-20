import uuid

from django.http import HttpResponse
from django.shortcuts import render
import requests

import config.settings as settings


def initiate_payment(request):
    txn_ref = str(uuid.uuid4())

    context = {
        "merchant_code": settings.INTERSWITCH_MERCHANT_CODE,
        "pay_item_id": settings.INTERSWITCH_PAY_ITEM_ID,
        "txn_ref": txn_ref,
        "amount": 200000,  # (amt in minor)
        "currency": 566,  # (NGN)
        "redirect_url": "http://127.0.0.1:8000/payment/callback/",
    }
    return render(request, "payment.html", context)


def payment_callback(request):
    txn_ref = request.GET.get("txn_ref")
    amount = request.GET.get("amount")

    verification_url = f"https:qa.interswitchng.com/collections/api/v1/gettransaction.json?merchantcode={settings.INTERSWITCH_MERCHANT_CODE}&transactionreference={txn_ref}&amount={amount}"

    response = requests.get(verification_url)
    data = response.json()

    if data.get("ResponseCode") == "00":
        request.user.is_premium = True
        request.user.save()

        return HttpResponse("Payment Successful, you are now a premium user 🎉")
    return HttpResponse("Payment Failed")
