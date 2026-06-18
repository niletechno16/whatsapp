
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
        try:
            data = json.loads(request.body or "{}")
            print("WHATSAPP EVENT:", data)
        except Exception as e:
            print(e)
        return JsonResponse({"status": "ok"})
