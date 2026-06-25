from django.shortcuts import render, redirect
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from .models import ContactMessage

def home(request):
    return render(request, 'core/home.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        email = request.POST.get('email', '').strip()
        phone = request.POST.get('phone', '').strip()
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()

        if name and email and subject and message:
            ContactMessage.objects.create(
                name=name,
                email=email,
                phone=phone,
                subject=subject,
                message=message
            )

            messages.success(
                request,
                'Thank you! Your message has been received. We will contact you shortly.'
            )
        else:
            messages.error(
                request,
                'Please fill in all required fields.'
            )

        return redirect('home')

    return redirect('home')