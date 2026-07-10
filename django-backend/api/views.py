from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Expert, Booking

def add_cors_headers(response):
    response['Access-Control-Allow-Origin'] = '*'
    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type'
    return response

@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def experts(request):

    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}))

    if request.method == 'GET':

        experts = Expert.objects.all()

        data = []

        for expert in experts:

            data.append({
                "id": expert.id,
                "name": expert.name,
                "profession": expert.profession,
                "experience": expert.experience,
                "phone": expert.phone,
                "email": expert.email,
                "languages": expert.languages,
                "_id": str(expert.id)
            })

        response = JsonResponse(data, safe=False)
        return add_cors_headers(response)

    elif request.method == 'POST':

        try:
            data = json.loads(request.body)
            expert = Expert.objects.create(
                name=data.get('name'),
                profession=data.get('profession'),
                experience=data.get('experience'),
                phone=data.get('phone'),
                email=data.get('email'),
                languages=data.get('languages')
            )

            response = JsonResponse({
                "message": "Expert Created"
            })
            return add_cors_headers(response)
        except Exception as e:
            response = JsonResponse({
                "error": str(e)
            }, status=400)
            return add_cors_headers(response)


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def bookings(request):

    if request.method == 'OPTIONS':
        return add_cors_headers(JsonResponse({}))

    if request.method == 'GET':

        bookings = Booking.objects.all()

        data = []

        for booking in bookings:

            data.append({
                "expertName": booking.expertName,
                "userName": booking.userName,
                "contact": booking.contact,
                "problem": booking.problem,
                "method": booking.method,
                "urgency": booking.urgency
            })

        response = JsonResponse(data, safe=False)
        return add_cors_headers(response)

    elif request.method == 'POST':

        try:
            data = json.loads(request.body)
            Booking.objects.create(
                expertName=data.get('expertName'),
                userName=data.get('userName'),
                contact=data.get('contact'),
                problem=data.get('problem'),
                method=data.get('method'),
                urgency=data.get('urgency')
            )

            response = JsonResponse({
                "message": "Booking Saved"
            })
            return add_cors_headers(response)
        except Exception as e:
            response = JsonResponse({
                "error": str(e)
            }, status=400)
            return add_cors_headers(response)