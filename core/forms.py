from django import forms
from .models import CompanyCertificate, DailyReport

class CertificateForm(forms.ModelForm):
    class Meta:
        model = CompanyCertificate
        fields = ['recipient_name', 'certificate_name', 'certificate_number', 'issue_date']
        widgets = {
            'issue_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'recipient_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Jane Doe'}),
            'certificate_name': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'CERT-12345'}),
        }


# Single Upload Form - name is read-only (auto-filled from logged-in user)
class DailyReportForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = [
            'name', 'location', 'year', 'volume_num',
            'num_of_page', 'num_of_deed', 'pdf_deed',
            'indexing', 'uploading', 'QC', 'metadata'
        ]
        widgets = {
            # Read-only — auto filled from logged-in user in the view
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'readonly': True,
                'style': 'background:#f0f2f5;cursor:not-allowed;color:#5E6B77;',
                'placeholder': 'Auto-filled from your account',
            }),
            'location': forms.Select(attrs={'class': 'form-select'}),
            'year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. 2026'}),
            'volume_num': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Vol-12'}),
            'num_of_page': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'num_of_deed': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'pdf_deed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'indexing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uploading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'QC': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'metadata': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# Bulk Form - no name field (auto-filled from logged-in user in view)
class DailyReportBulkForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = [
            'location', 'year', 'volume_num',
            'num_of_page', 'num_of_deed', 'pdf_deed',
            'indexing', 'uploading', 'QC', 'metadata'
        ]
        widgets = {
            'location': forms.Select(attrs={'class': 'form-select form-select-sm'}),
            'year': forms.TextInput(attrs={'class': 'form-control form-select-sm', 'placeholder': 'Year'}),
            'volume_num': forms.TextInput(attrs={'class': 'form-control form-select-sm', 'placeholder': 'Vol'}),
            'num_of_page': forms.NumberInput(attrs={'class': 'form-control form-select-sm', 'min': '0'}),

            'num_of_deed': forms.NumberInput(attrs={'class': 'form-control form-select-sm', 'min': '0'}),
            'pdf_deed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'indexing': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'uploading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'QC': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'metadata': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


# added seprate form for updating the report
class DailyReportUpdateForm(forms.ModelForm):
    class Meta:
        model = DailyReport
        fields = [
            'name', 'location', 'year', 'volume_num',
            'num_of_page', 'num_of_deed', 'pdf_deed',
            'indexing', 'uploading', 'QC', 'metadata'
        ]
        # Re-use your existing styled widgets
        widgets = DailyReportForm.Meta.widgets 

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        


        # no need for this, already managed inside views.py
        
        # # 🌟 Lock down structural fields during an update to keep data clean
        # self.fields['location'].disabled = True
        # self.fields['year'].disabled = True
        # self.fields['volume_num'].disabled = True
        
        # # Optionally make them visually look locked out:
        # lock_style = 'background:#f0f2f5; cursor:not-allowed; color:#5E6B77;'
        # self.fields['location'].widget.attrs['style'] = lock_style
        # self.fields['year'].widget.attrs['style'] = lock_style
        # self.fields['volume_num'].widget.attrs['style'] = lock_style