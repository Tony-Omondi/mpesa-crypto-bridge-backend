# /forms.py
from django import forms
from django.utils import timezone
from datetime import date
from .models import DeliveryZone

TIME_SLOT_CHOICES = [
    ('09:00-12:00', '9:00 AM – 12:00 PM (Morning)'),
    ('12:00-15:00', '12:00 PM – 3:00 PM (Afternoon)'),
    ('15:00-18:00', '3:00 PM – 6:00 PM (Late Afternoon)'),
    ('18:00-21:00', '6:00 PM – 9:00 PM (Evening)'),
]

class CheckoutForm(forms.Form):
    email = forms.EmailField(
        label="Email Address",
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-input',
            'placeholder': 'you@example.com'
        })
    )
    phone_number = forms.CharField(
        label="Phone Number",
        max_length=15,
        help_text="Format: 0712345678 or 254712345678 (used for M-Pesa)",
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': '0712345678'
        })
    )
    zone = forms.ModelChoiceField(
        queryset=DeliveryZone.objects.filter(is_active=True).order_by('name'),
        label="Delivery Zone",
        empty_label="Select your delivery zone",
        widget=forms.Select(attrs={'class': 'form-select'}),
    )
    preferred_delivery_date = forms.DateField(
        label="Preferred Delivery Date",
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-input',
        }),
        help_text="We deliver from tomorrow onwards"
    )
    preferred_delivery_time = forms.ChoiceField(
        choices=TIME_SLOT_CHOICES,
        label="Preferred Delivery Time Slot",
        widget=forms.Select(attrs={'class': 'form-select'}),
        help_text="Choose when you'd like us to deliver"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Minimum date: tomorrow
        tomorrow = date.today() + timezone.timedelta(days=1)
        self.fields['preferred_delivery_date'].widget.attrs['min'] = tomorrow.strftime('%Y-%m-%d')
        # Optional: max 14 days ahead
        max_date = tomorrow + timezone.timedelta(days=13)
        self.fields['preferred_delivery_date'].widget.attrs['max'] = max_date.strftime('%Y-%m-%d')

        # Keep zone choices fresh
        self.fields['zone'].queryset = DeliveryZone.objects.filter(is_active=True).order_by('name')

    def clean_preferred_delivery_date(self):
        delivery_date = self.cleaned_data.get('preferred_delivery_date')
        if delivery_date <= date.today():
            raise forms.ValidationError("Delivery date must be tomorrow or later.")
        return delivery_date

    def clean_phone_number(self):
        phone = self.cleaned_data['phone_number'].strip().lstrip('0')
        if not phone.replace('254', '').isdigit() or len(phone.replace('254', '')) != 9:
            raise forms.ValidationError("Invalid Kenyan mobile number format.")
        if not (phone.startswith('7') or phone.startswith('1') or phone.startswith('2547') or phone.startswith('2541')):
            raise forms.ValidationError("Please enter a valid Kenyan mobile number (07xx or 2547xx).")
        # Normalize to international format
        return '254' + phone.replace('254', '')[-9:]