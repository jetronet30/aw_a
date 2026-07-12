from django.shortcuts import render

# Create your views here.


def process(request):
    return render(request, "proc/process.html")
