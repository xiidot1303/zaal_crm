from django.core.exceptions import ValidationError
from django.forms import ModelForm, CharField, IntegerField, DecimalField, DateTimeField
from django import forms

from app.models import *
from app.services.transfer_service import validate_transfer_balance
from django.utils import timezone


class AccommodationForm(ModelForm):
    class Meta:
        model = Accommodation
        fields = ['room', 'days', 'check_in', 'check_out', 'price']
        widgets = {
            'room': forms.Select(attrs={'class': 'form-select'}),
            'days': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'check_in': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'check_out': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'min': 0}),
        }


class IncomeForm(ModelForm):
    # Optional accommodation fields
    accommodation_room = IntegerField(required=False, widget=forms.Select(attrs={'class': 'form-select'}))
    accommodation_days = IntegerField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 1}))
    accommodation_check_in = DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    accommodation_check_out = DateTimeField(required=False, widget=forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}))
    accommodation_price = DecimalField(required=False, widget=forms.NumberInput(attrs={'class': 'form-control', 'min': 0}))

    class Meta:
        model = Income
        fields = ['account', 'type', 'amount', 'description']
        widgets = {
            'account': forms.Select(attrs={'class': 'form-select'}),
            'type': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        amount = cleaned_data.get('amount')
        income_type = cleaned_data.get('type')

        if amount is None or account is None:
            return cleaned_data

        if amount <= 0:
            raise ValidationError({'amount': "Сумма должна быть больше нуля."})

        if account.balance is None:
            raise ValidationError("У выбранного счёта не задан баланс.")

        # If type is accommodation, we need accommodation fields
        if income_type == 'accommodation':
            room_id = cleaned_data.get('accommodation_room')
            days = cleaned_data.get('accommodation_days')
            check_in = cleaned_data.get('accommodation_check_in')
            check_out = cleaned_data.get('accommodation_check_out')
            price = cleaned_data.get('accommodation_price')

            if not all([room_id, days, check_in, check_out, price]):
                raise ValidationError("Все поля проживания обязательны для типа 'Проживание'.")

            if days <= 0:
                raise ValidationError({'accommodation_days': "Количество дней должно быть больше нуля."})

            if price <= 0:
                raise ValidationError({'accommodation_price': "Цена должна быть больше нуля."})

            if check_out <= check_in:
                raise ValidationError("Дата выезда должна быть позже даты заезда.")

        return cleaned_data


class ExpenseForm(ModelForm):
    class Meta:
        model = Expense
        fields = ['title', 'account', 'amount', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control'}),
            'account': forms.Select(attrs={'class': 'form-select'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': 1}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        account = cleaned_data.get('account')
        amount = cleaned_data.get('amount')

        if amount is None or account is None:
            return cleaned_data

        if amount <= 0:
            raise ValidationError({'amount': "Сумма должна быть больше нуля."})

        if account.balance is None:
            raise ValidationError("У выбранного счёта не задан баланс.")

        if amount > account.balance:
            raise ValidationError({
                '__all__': "Недостаточно средств на счёте. Выберите другой счёт или введите меньшую сумму."
            })

        return cleaned_data


class TransferForm(forms.ModelForm):
    class Meta:
        model = Transfer
        fields = [
            'from_account',
            'to_account',
            'amount',
            'fees',
            'description',
        ]

    def clean(self):
        cleaned_data = super().clean()
        from_account = cleaned_data.get('from_account')
        amount = cleaned_data.get('amount')
        fees = cleaned_data.get('fees')

        if from_account is not None and amount is not None and fees is not None:
            validate_transfer_balance(from_account, amount, fees)

        return cleaned_data
