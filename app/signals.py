import logging

from django.db.models import F
from django.db.models.signals import post_delete, post_save, pre_save, pre_delete
from django.dispatch import receiver
from django.core.exceptions import ValidationError

from app.services.transfer_service import reverse_transfer_balances
from app.utils import generate_random_string
from app.services.bot_service import get_bot_username, send_newsletter_api
from asgiref.sync import async_to_sync

from app.models import *

logger = logging.getLogger(__name__)


def build_staff_invite_link(token_length=6):
    BOT_USERNAME = async_to_sync(get_bot_username)()
    if not BOT_USERNAME:
        return None

    random_string = generate_random_string(token_length)
    return f"https://t.me/{BOT_USERNAME}?start={random_string}"


@receiver(pre_save, sender=Staff)
def staff_pre_save(sender, instance, **kwargs):
    if not instance.pk:
        return

    try:
        existing = Staff.objects.get(pk=instance.pk)
    except Staff.DoesNotExist:
        return

    instance._previous_is_active = existing.is_active


@receiver(post_save, sender=Staff)
def staff_saved(sender, instance, created, **kwargs):
    if created:
        logger.info(f"Staff created: {instance}")

        invite_link = build_staff_invite_link()
        if not invite_link:
            logger.warning(
                "Skipping invite link generation for staff %s because BOT_USERNAME is not configured.",
                instance.pk,
            )
            return

        Staff.objects.filter(pk=instance.pk).update(invite_link=invite_link)
        return

    logger.info(f"Staff updated: {instance}")

    if getattr(instance, '_previous_is_active', None) is True and instance.is_active is False:
        if instance.bot_user_id:
            try:
                send_newsletter_api.delay(
                    instance.bot_user.user_id,
                    text="Ваш доступ деактивирован."
                )
                logger.info(
                    "Sent deactivation newsletter for staff %s to bot user %s.",
                    instance.pk,
                    instance.bot_user.user_id,
                )
            except Exception as exc:
                logger.exception(
                    "Failed to send deactivation newsletter for staff %s: %s",
                    instance.pk,
                    exc,
                )
        else:
            logger.warning(
                "Staff %s deactivated but has no bot_user, skipping newsletter.",
                instance.pk,
            )


@receiver(post_save, sender=Accommodation)
def accommodation_created(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.room_id:
        logger.warning(
            "Accommodation %s has no room_id, skipping room status update.",
            instance.pk,
        )
        return

    logger.info(
        "Updating room %s status after accommodation %s created.",
        instance.room_id,
        instance.pk,
    )

    # Update room to be occupied
    from .models import Room
    Room.objects.filter(pk=instance.room_id).update(
        is_free=False,
        taken_to=instance.check_out
    )


@receiver(post_delete, sender=Accommodation)
def accommodation_deleted(sender, instance, **kwargs):
    """Free up the room when accommodation is deleted"""
    if not instance.room_id:
        logger.warning(
            "Accommodation %s has no room_id, skipping room status update on delete.",
            instance.pk,
        )
        return

    logger.info(
        "Freeing room %s after accommodation %s deleted.",
        instance.room_id,
        instance.pk,
    )

    # Update room to be free
    from .models import Room
    Room.objects.filter(pk=instance.room_id).update(
        is_free=True,
        taken_to=None
    )


@receiver(post_save, sender=Expense)
def expense_created(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.account_id:
        logger.warning(
            "Expense %s has no account_id, skipping balance update.",
            instance.pk,
        )
        return

    logger.info(
        "Updating balance for account %s after expense %s created.",
        instance.account_id,
        instance.pk,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') - instance.amount
    )


@receiver(post_delete, sender=Expense)
def expense_deleted(sender, instance, **kwargs):
    """Add expense amount back to account balance when expense is deleted"""
    if not instance.account_id:
        logger.warning(
            "Expense %s has no account_id, skipping balance reversal on delete.",
            instance.pk,
        )
        return

    logger.info(
        "Reversing expense %s: adding %s back to account %s balance.",
        instance.pk,
        instance.amount,
        instance.account_id,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') + instance.amount
    )


@receiver(post_save, sender=Income)
def income_created(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.account_id:
        logger.warning(
            "Income %s has no account_id, skipping balance update.",
            instance.pk,
        )
        return

    logger.info(
        "Updating balance for account %s after income %s created.",
        instance.account_id,
        instance.pk,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') + instance.amount
    )

    # If account is bank type, create an expense for 0.2% fee
    account = Account.objects.get(pk=instance.account_id)
    if account.type == 'bank':
        fee_amount = float(instance.amount) * 0.002  # 0.2%
        expense = Expense.objects.create(
            title=f"Комиссия банка за доход #{instance.pk}",
            account=account,
            amount=fee_amount,
            description=f"Автоматическая комиссия банка (0.2%) за доход #{instance.pk}"
        )
        logger.info(
            "Created bank fee expense %s for income %s with amount %s",
            expense.pk,
            instance.pk,
            fee_amount,
        )
    
    # delete accommodation if income is of type accommodation
    if instance.type == 'accommodation' and instance.accommondation_id:
        Accommodation.objects.filter(pk=instance.accommondation_id).delete()


@receiver(pre_delete, sender=Income)
def income_pre_delete(sender, instance, **kwargs):
    """Validate that account has enough balance before allowing income deletion"""
    if not instance.account_id:
        logger.warning(
            "Income %s has no account_id, skipping balance validation.",
            instance.pk,
        )
        return

    account = Account.objects.get(pk=instance.account_id)
    if account.balance < instance.amount:
        error_msg = (
            f"Невозможно удалить доход #{instance.pk}. "
            f"На счёте {account.title} недостаточно средств. "
            f"Требуется {instance.amount}, доступно {account.balance}."
        )
        logger.error(error_msg)
        raise ValidationError(error_msg)

    logger.info(
        "Income %s validation passed for deletion. Account %s has sufficient balance.",
        instance.pk,
        instance.account_id,
    )


@receiver(post_delete, sender=Income)
def income_deleted(sender, instance, **kwargs):
    """Subtract income amount from account balance after income deletion"""
    if not instance.account_id:
        logger.warning(
            "Income %s has no account_id, skipping balance update on delete.",
            instance.pk,
        )
        return

    logger.info(
        "Reversing income %s: subtracting %s from account %s balance.",
        instance.pk,
        instance.amount,
        instance.account_id,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') - instance.amount
    )

    account = Account.objects.get(pk=instance.account_id)
    if account.type == 'bank':
        fee_amount = float(instance.amount) * 0.002  # 0.2%
        Expense.objects.filter(
            title__icontains=f"#{instance.pk}",
            account_id=instance.account_id,
            amount=fee_amount
        ).delete()
        logger.info(
            "Deleted bank fee expense for income %s with amount %s",
            instance.pk,
            fee_amount,
        )


@receiver(post_save, sender=Transfer)
def transfer_created(sender, instance, created, **kwargs):
    if getattr(instance, '_skip_transfer_signal', False):
        return

    if not created:
        return

    logger.info(
        "Processing transfer %s: from %s to %s, amount %s, fees %s",
        instance.pk,
        instance.from_account_id,
        instance.to_account_id,
        instance.amount,
        instance.fees,
    )

    # Deduct from from_account
    Account.objects.filter(pk=instance.from_account_id).update(
        balance=F('balance') - instance.amount - instance.fees
    )

    # Add to to_account
    Account.objects.filter(pk=instance.to_account_id).update(
        balance=F('balance') + instance.amount
    )


@receiver(post_delete, sender=Transfer)
def transfer_deleted(sender, instance, **kwargs):
    logger.info(
        "Reversing transfer %s: from %s to %s, amount %s, fees %s",
        instance.pk,
        instance.from_account_id,
        instance.to_account_id,
        instance.amount,
        instance.fees,
    )

    reverse_transfer_balances(instance)


@receiver(post_save, sender=Salary)
def salary_created(sender, instance, created, **kwargs):
    if not created:
        return

    if not instance.account_id:
        logger.warning(
            "Salary %s has no account_id, skipping balance update.",
            instance.pk,
        )
        return

    logger.info(
        "Updating balance for account %s after salary %s created.",
        instance.account_id,
        instance.pk,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') - instance.amount
    )


@receiver(post_delete, sender=Salary)
def salary_deleted(sender, instance, **kwargs):
    """Add salary amount back to account balance when salary is deleted"""
    if not instance.account_id:
        logger.warning(
            "Salary %s has no account_id, skipping balance reversal on delete.",
            instance.pk,
        )
        return

    logger.info(
        "Reversing salary %s: adding %s back to account %s balance.",
        instance.pk,
        instance.amount,
        instance.account_id,
    )

    Account.objects.filter(pk=instance.account_id).update(
        balance=F('balance') + instance.amount
    )
