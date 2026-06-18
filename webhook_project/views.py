
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

VERIFY_TOKEN = "nile_techno_verify"

@csrf_exempt
def whatsapp_webhook(request):
    if request.method == "GET":
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return HttpResponse(challenge)
        return HttpResponse(status=403)

    if request.method == "POST":
        print("=" * 100)
        print("WEBHOOK CALLED")
        print(request.body.decode("utf-8"))
        print("=" * 100)

        return JsonResponse({"status": "ok"})