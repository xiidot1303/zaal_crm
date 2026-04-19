from django.db import models


class Staff(models.Model):
    name = models.CharField("Имя", max_length=100)
    bot_user = models.ForeignKey(
        'bot.Bot_user',
        verbose_name="Пользователь бота",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    invite_link = models.CharField("Ссылка-приглашение", null=True, blank=True, max_length=255)
    is_active = models.BooleanField("Активен?", default=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Сотрудник"
        verbose_name_plural = "Сотрудники"


class Account(models.Model):
    title = models.CharField("Название", max_length=100)
    TYPE_CHOICES = [
        ('cash', 'Наличные'),
        ('bank', 'Банковский счёт'),
        ('personal', 'Персональный счёт'),
        ('other', 'Другое'),
    ]
    type = models.CharField("Тип", max_length=50, choices=TYPE_CHOICES, default='other')
    balance = models.DecimalField("Баланс", max_digits=12, decimal_places=0, default=0)

    def __str__(self) -> str:
        return f"{self.title} ({self.get_type_display()}) - {self.balance} so'm."

    class Meta:
        verbose_name = "Счёт"
        verbose_name_plural = "Счета"


class Room(models.Model):
    number = models.CharField("Номер комнаты", max_length=20)
    is_free = models.BooleanField("Свободна?", default=True)
    taken_to = models.DateTimeField("Занята до", null=True, blank=True)

    def __str__(self):
        return f"{self.number} - {'Свободна' if self.is_free else 'Занята'}"

    class Meta:
        verbose_name = "Комната"
        verbose_name_plural = "Комнаты"


class Accommodation(models.Model):
    room = models.ForeignKey(Room, null=True, verbose_name="Комната", on_delete=models.CASCADE)
    days = models.IntegerField("Количество дней")
    check_in = models.DateTimeField("Дата заезда")
    check_out = models.DateTimeField("Дата выезда")
    price = models.DecimalField("Цена", max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = "Проживание"
        verbose_name_plural = "Проживания"


class Income(models.Model):
    account = models.ForeignKey(Account, verbose_name="Счёт", on_delete=models.CASCADE)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=0)
    TYPE_CHOICES = [
        ('sale', 'Продажа'),
        ('accommodation', 'Проживание'),
        ('cleaning', 'Уборка'),
    ]
    type = models.CharField("Тип", max_length=50, choices=TYPE_CHOICES, default='other')
    accommondation = models.ForeignKey(
        Accommodation,
        verbose_name="Проживание",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )

    description = models.TextField("Описание", blank=True, null=True)
    date = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Доход"
        verbose_name_plural = "Доходы"


class Expense(models.Model):
    title = models.CharField("Название", max_length=100)
    account = models.ForeignKey(Account, verbose_name="Счёт", on_delete=models.CASCADE)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=0)
    description = models.TextField("Описание", blank=True, null=True)
    date = models.DateTimeField("Дата", auto_now_add=True)

    class Meta:
        verbose_name = "Расход"
        verbose_name_plural = "Расходы"


class Transfer(models.Model):
    from_account = models.ForeignKey(
        Account,
        verbose_name="Счёт отправителя",
        related_name='transfers_out',
        on_delete=models.CASCADE
    )
    to_account = models.ForeignKey(
        Account,
        verbose_name="Счёт получателя",
        related_name='transfers_in',
        on_delete=models.CASCADE
    )
    fees = models.DecimalField("Комиссия", max_digits=12, decimal_places=0, default=0)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=0)
    description = models.TextField("Описание", blank=True, null=True)
    date = models.DateTimeField("Дата", auto_now_add=True)

    def clean(self):
        from django.core.exceptions import ValidationError
        from_account = Account.objects.get(pk=self.from_account_id)
        total_deduct = self.amount + self.fees
        if from_account.balance < total_deduct:
            raise ValidationError(
                f"Недостаточно средств на счёте {from_account.title}. "
                f"Требуется {total_deduct}, доступно {from_account.balance}."
            )

    class Meta:
        verbose_name = "Перевод"
        verbose_name_plural = "Переводы"


class Salary(models.Model):
    staff = models.ForeignKey(Staff, verbose_name="Сотрудник", on_delete=models.CASCADE)
    account = models.ForeignKey(Account, verbose_name="Счёт", on_delete=models.CASCADE)
    amount = models.DecimalField("Сумма", max_digits=12, decimal_places=0)
    description = models.TextField("Описание", blank=True, null=True)
    date = models.DateTimeField("Дата", auto_now_add=True)

    def __str__(self):
        return f"{self.staff.name} - {self.amount} so'm."

    def clean(self):
        from django.core.exceptions import ValidationError
        account = Account.objects.get(pk=self.account_id)
        if account.balance < self.amount:
            raise ValidationError(
                f"Недостаточно средств на счёте {account.title}. "
                f"Требуется {self.amount}, доступно {account.balance}."
            )

    class Meta:
        verbose_name = "Зарплата"
        verbose_name_plural = "Зарплаты"
