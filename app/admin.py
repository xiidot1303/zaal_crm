from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from django.contrib.auth.models import User, Group

from typing import cast
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm
from unfold.admin import ModelAdmin

from app.forms import TransferForm
from app.models import *
from app.services.transfer_service import (
    apply_transfer_balances,
    update_transfer_balances,
)
from unfold.contrib.filters.admin import RangeDateFilter, RangeDateTimeFilter
from import_export.admin import ImportExportModelAdmin, ExportActionModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(BaseUserAdmin, ModelAdmin):
    # Forms loaded from `unfold.forms`
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm


@admin.register(Group)
class GroupAdmin(BaseGroupAdmin, ModelAdmin):
    pass


@admin.register(Staff)
class StaffAdmin(ModelAdmin):
    list_display = ("name", "bot_user", "invite_link", "is_active")
    search_fields = ("name", "bot_user__tg_id")
    list_select_related = ("bot_user",)
    readonly_fields = ("invite_link", "bot_user")
    list_filter = ("is_active",)


@admin.register(Account)
class AccountAdmin(ModelAdmin):
    list_display = ("title", "type", "balance")
    list_filter = ("type",)
    search_fields = ("title",)


@admin.register(Room)
class RoomAdmin(ModelAdmin):
    list_display = ("number", "is_free", "taken_to")
    search_fields = ("number",)
    list_filter = ("is_free",)


@admin.register(Accommodation)
class AccommodationAdmin(ModelAdmin, ExportActionModelAdmin):
    list_display = ("room", "days", "check_in", "check_out", "price")
    search_fields = ("room__number",)
    list_filter_submit = True
    list_filter = (("check_in", RangeDateFilter), ("check_out", RangeDateFilter))
    export_form_class = ExportForm


@admin.register(Income)
class IncomeAdmin(ModelAdmin, ExportActionModelAdmin):
    list_display = ("account", "staff", "type", "amount", "accommondation", "date")
    list_filter_submit = True
    list_filter = ("type", ("date", RangeDateFilter))
    search_fields = ("account__title", "description", "accommondation__room_number")
    list_select_related = ("account", "accommondation")
    readonly_fields = ("date",)
    export_form_class = ExportForm


@admin.register(Expense)
class ExpenseAdmin(ModelAdmin, ExportActionModelAdmin):
    list_display = ("title", "account", "staff", "amount", "date")
    search_fields = ("title", "description", "account__title")
    list_filter_submit = True
    list_filter = (("date", RangeDateFilter), "account")
    list_select_related = ("account",)
    readonly_fields = ("date",)
    export_form_class = ExportForm


@admin.register(Transfer)
class TransferAdmin(ModelAdmin, ExportActionModelAdmin):
    form = TransferForm

    list_display = ("from_account", "to_account", "amount", "fees", "date")
    search_fields = (
        "from_account__title",
        "to_account__title",
        "description",
    )
    list_filter_submit = True
    list_filter = (("date", RangeDateFilter), "from_account", "to_account")
    list_select_related = ("from_account", "to_account")
    readonly_fields = ("date",)
    export_form_class = ExportForm

    def save_model(self, request, obj, form, change):
        if not change:
            setattr(obj, '_skip_transfer_signal', True)
            super().save_model(request, obj, form, change)
            apply_transfer_balances(cast(Transfer, obj))
        else:
            transfer_obj = cast(Transfer, obj)
            old_transfer = cast(Transfer, Transfer.objects.get(pk=transfer_obj.pk))
            if (
                old_transfer.from_account.pk == transfer_obj.from_account.pk
                and old_transfer.to_account.pk == transfer_obj.to_account.pk
                and old_transfer.amount == transfer_obj.amount
                and old_transfer.fees == transfer_obj.fees
            ):
                super().save_model(request, transfer_obj, form, change)
                return

            setattr(transfer_obj, '_skip_transfer_signal', True)
            super().save_model(request, transfer_obj, form, change)
            update_transfer_balances(old_transfer, transfer_obj)


@admin.register(Salary)
class SalaryAdmin(ModelAdmin, ExportActionModelAdmin):
    list_display = ("staff", "account", "amount", "date")
    search_fields = ("staff__name", "account__title", "description")
    list_filter_submit = True
    list_filter = (("date", RangeDateFilter), "account")
    list_select_related = ("staff", "account")
    readonly_fields = ("date",)
    export_form_class = ExportForm
