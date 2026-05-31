from rest_framework.decorators import api_view
from rest_framework.response import Response
from .models import Expert, Booking

@api_view(['GET', 'POST'])
def experts(request):

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
                "languages": expert.languages
            })

        return Response(data)

    elif request.method == 'POST':

        expert = Expert.objects.create(
            name=request.data.get('name'),
            profession=request.data.get('profession'),
            experience=request.data.get('experience'),
            phone=request.data.get('phone'),
            email=request.data.get('email'),
            languages=request.data.get('languages')
        )

        return Response({
            "message": "Expert Created"
        })


@api_view(['GET', 'POST'])
def bookings(request):

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

        return Response(data)

    elif request.method == 'POST':

        Booking.objects.create(
            expertName=request.data.get('expertName'),
            userName=request.data.get('userName'),
            contact=request.data.get('contact'),
            problem=request.data.get('problem'),
            method=request.data.get('method'),
            urgency=request.data.get('urgency')
        )

        return Response({
            "message": "Booking Saved"
        })