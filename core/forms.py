from django import forms
from .models import CompanyCertificate, DailyReport

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

class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        # 'name' is excluded here because it is handled globally
        fields = ['location', 'year', 'volume_num', 'num_of_deed', 'num_of_page', 'pdf_deed', 'indexing', 'uploading', 'metadata']
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'year': forms.TextInput(attrs={'class': 'form-control form-select-sm', 'placeholder': 'Year'}),
            'volume_num': forms.TextInput(attrs={'class': 'form-control form-select-sm', 'placeholder': 'Vol'}),
            'num_of_deed': forms.NumberInput(attrs={'class': 'form-control form-select-sm', 'min': '0'}),
            'num_of_page': forms.NumberInput(attrs={'class': 'form-control form-select-sm', 'min': '0'}),
            'pdf_deed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'indexing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uploading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'metadata': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

# class DailyReportForm(forms.ModelForm):
#     class Meta:
#         model = DailyReport
#         # Fields to expose on the front-end form
#         fields = [
#             'location', 'name', 'year', 'volume_num', 
#             'num_of_deed', 'num_of_page', 'pdf_deed', 
#             'indexing', 'uploading', 'metadata'
#         ]
        
#         # Applying CSS styling classes dynamically
#         widgets = {
#             'location': forms.Select(attrs={'class': 'form-select'}),
#             'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter Employee Name'}),
#             'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2026'}),
#             'volume_num': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Vol-12'}),
#             'num_of_deed': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
#             'num_of_page': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            
#             # Using Bootstrap's form-check-input class for checkboxes
#             'pdf_deed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'indexing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'uploading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#             'metadata': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
#         }