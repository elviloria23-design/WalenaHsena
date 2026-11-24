from django import forms
from .models import reservas

class ReservaForm(forms.ModelForm):
    checkin = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha de Entrada (Check-in)"
    )
    checkout = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
        label="Fecha de Salida (Check-out)"
    )

    class Meta:
        model = reservas
        fields = ['checkin', 'checkout']