from django.shortcuts import render
from django.http import JsonResponse
import requests
from django.views.decorators.csrf import csrf_exempt

def home(request):
    return render(request, "App/index.html")  # Ton index.html actuel

def chat_page(request):
    return render(request, "App/chat.html")   # La nouvelle page pour le chat


@csrf_exempt
def chat_with_rasa(request):
    print("Méthode:", request.method)
    print("POST:", request.POST)

    if request.method != "POST":
        return JsonResponse({"error": "Méthode non autorisée"}, status=405)

    user_message = request.POST.get("message")
    if not user_message:
        return JsonResponse({"error": "Aucun message fourni"}, status=400)

    rasa_url = "http://localhost:5005/webhooks/rest/webhook"
    payload = {"sender": "user", "message": user_message}

    try:
        response = requests.post(rasa_url, json=payload)
        response_data = response.json()
        messages = [msg.get("text") for msg in response_data if "text" in msg]
        print("Messages Rasa:", messages)
    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"responses": messages})
