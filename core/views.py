from django.shortcuts import render, redirect
from django.contrib import messages
from .models import ContactMessage, CompanyCertificate
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView
from .forms import CertificateForm
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import DetailView

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
            messages.success(request, 'Thank you! Your message has been received. We will contact you shortly.')
        else:
            messages.error(request, 'Please fill in all required fields.')
        return redirect('home')
    return redirect('home')


class CertificateCreateView(CreateView):
    model = CompanyCertificate
    form_class = CertificateForm
    template_name = 'core/add_certificate.html'
    
    # Where to redirect the user after successfully adding a certificate
    # Change 'certificate_list' to whatever your success URL name is
    success_url = reverse_lazy('add_certificate')

    success_message = "Certificate for %(recipient_name)s was created successfully!"


class CertificateVerifyView(DetailView):
    model = CompanyCertificate
    template_name = 'core/verify_certificate.html'
    context_object_name = 'certificate'
    
    # Tell Django to look up the certificate by its number instead of its primary key ID
    slug_field = 'certificate_number'
    slug_url_kwarg = 'certificate_number'