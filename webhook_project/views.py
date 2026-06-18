from django.http import HttpResponse, JsonResponse, request
from django.views.decorators.csrf import csrf_exempt


VERIFY_TOKEN = "nile_techno_verify"


@csrf_exempt
def whatsapp_webhook(request):
    print("🔥🔥🔥 REQUEST HIT SERVER 🔥🔥🔥")
    print("METHOD:", request.method)
    print("PATH:", request.path)
    print("BODY:", request.body.decode("utf-8"))

    return JsonResponse({"status": "ok"})


def privacy_policy(request):
    return HttpResponse("""
    <h1>Privacy Policy</h1>
    <p>This application is used for WhatsApp message testing and storage.</p>
    """)