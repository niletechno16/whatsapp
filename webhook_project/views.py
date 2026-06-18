from django.http import HttpResponse, JsonResponse, request
from django.views.decorators.csrf import csrf_exempt


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
        print("\n" + "=" * 100)
        print("🔥 WEBHOOK CALLED")
        print("PATH:", request.path)
        print("METHOD:", request.method)
        print("HEADERS:", dict(request.headers))
        print("BODY:", request.body.decode("utf-8"))
        print("=" * 100 + "\n")

        return JsonResponse({"status": "ok"})


def privacy_policy(request):
    return HttpResponse("""
    <h1>Privacy Policy</h1>
    <p>This application is used for WhatsApp message testing and storage.</p>
    """)