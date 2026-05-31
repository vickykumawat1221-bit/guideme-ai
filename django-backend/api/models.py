from django.db import models

class Expert(models.Model):
    name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    experience = models.IntegerField()
    phone = models.CharField(max_length=20)
    email = models.EmailField()
    languages = models.CharField(max_length=200)

class Booking(models.Model):
    expertName = models.CharField(max_length=100)
    userName = models.CharField(max_length=100)
    contact = models.CharField(max_length=100)
    problem = models.TextField()
    method = models.CharField(max_length=50)
    urgency = models.CharField(max_length=50)