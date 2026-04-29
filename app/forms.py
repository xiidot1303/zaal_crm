from django.core.exceptions import ValidationError
from django.forms import ModelForm, formset_factory
from django import forms

from app.models import *
from app.services.transfer_service import validate_transfer_balance


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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['room'].queryset = Room.objects.order_by('-is_free', 'number')

    def clean(self):
        cleaned_data = super().clean()
        days = cleaned_data.get('days')
        check_in = cleaned_data.get('check_in')
        check_out = cleaned_data.get('check_out')
        price = cleaned_data.get('price')

        if days is not None and days <= 0:
            raise ValidationError({'days': "Количество дней должно быть больше нуля."})

        if price is not None and price <= 0:
            raise ValidationError({'price': "Цена должна быть больше нуля."})

        if check_in and check_out and check_out <= check_in:
            raise ValidationError({'check_out': "Дата выезда должна быть позже даты заезда."})

        return cleaned_data


class IncomeForm(ModelForm):
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

        return cleaned_data


class BaseAccommodationFormSet(forms.BaseFormSet):
    def __init__(self, *args, require_at_least_one=False, **kwargs):
        self.require_at_least_one = require_at_least_one
        super().__init__(*args, **kwargs)

    def clean(self):
        super().clean()

        if any(self.errors) or not self.require_at_least_one:
            return

        has_accommodation = any(
            form.cleaned_data and form.cleaned_data.get('room')
            for form in self.forms
        )
        if not has_accommodation:
            raise ValidationError("Добавьте хотя бы одно проживание.")


AccommodationFormSet = formset_factory(
    AccommodationForm,
    formset=BaseAccommodationFormSet,
    extra=1,
)


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
