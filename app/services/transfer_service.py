from collections import defaultdict
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F

from app.models import Account, Transfer


def validate_transfer_balance(from_account: Account, amount, fees):
    total_deduct = amount + fees
    if from_account.balance is None or from_account.balance < total_deduct:
        raise ValidationError(
            f"Недостаточно средств на счёте {from_account.title}. "
            f"Требуется {total_deduct}, доступно {from_account.balance}."
        )
    return total_deduct


def apply_transfer_balances(transfer: Transfer):
    total_deduct = transfer.amount + transfer.fees

    with transaction.atomic():
        Account.objects.filter(pk=transfer.from_account.pk).update(
            balance=F('balance') - total_deduct
        )
        Account.objects.filter(pk=transfer.to_account.pk).update(
            balance=F('balance') + transfer.amount
        )


def reverse_transfer_balances(transfer: Transfer):
    total_deduct = transfer.amount + transfer.fees

    with transaction.atomic():
        Account.objects.filter(pk=transfer.from_account.pk).update(
            balance=F('balance') + total_deduct
        )
        Account.objects.filter(pk=transfer.to_account.pk).update(
            balance=F('balance') - transfer.amount
        )


def update_transfer_balances(old_transfer: Transfer, new_transfer: Transfer):
    account_ids = {
        old_transfer.from_account.pk,
        old_transfer.to_account.pk,
        new_transfer.from_account.pk,
        new_transfer.to_account.pk,
    }

    accounts = {account.pk: account for account in Account.objects.filter(pk__in=account_ids)}

    total_old = old_transfer.amount + old_transfer.fees
    total_new = new_transfer.amount + new_transfer.fees

    baseline = {account_id: accounts[account_id].balance for account_id in account_ids}
    baseline[old_transfer.from_account.pk] += total_old
    baseline[old_transfer.to_account.pk] -= old_transfer.amount

    if baseline[new_transfer.from_account.pk] < total_new:
        raise ValidationError(
            f"Недостаточно средств на счёте {new_transfer.from_account.title}. "
            f"Требуется {total_new}, доступно {baseline[new_transfer.from_account.pk]}."
        )

    delta = defaultdict(Decimal)
    delta[old_transfer.from_account.pk] += total_old
    delta[old_transfer.to_account.pk] -= old_transfer.amount
    delta[new_transfer.from_account.pk] -= total_new
    delta[new_transfer.to_account.pk] += new_transfer.amount

    with transaction.atomic():
        for account_id, change in delta.items():
            if change == 0:
                continue
            Account.objects.filter(pk=account_id).update(balance=F('balance') + change)
