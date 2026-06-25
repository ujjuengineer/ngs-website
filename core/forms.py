from django import forms
from .models import CompanyCertificate

class CertificateForm(forms.ModelForm):
    class Meta:
        model = CompanyCertificate
        fields = ['recipient_name', 'certificate_name', 'certificate_number', 'issue_date']
        
        # Adding HTML widgets to make the date inputs look like actual date pickers
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jane Doe'}),
            'certificate_name': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CERT-12345'}),
        }