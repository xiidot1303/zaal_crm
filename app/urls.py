from django.urls import path, re_path
from django.contrib.auth.views import (
    LoginView, 
    LogoutView, 
    PasswordChangeDoneView, 
    PasswordChangeView
)

from app.views import (
    main,
    expense,
    income,
    room
)


urlpatterns = [
    path('', main.main),
    # login
    path('accounts/login/', LoginView.as_view()),
    path('changepassword/', PasswordChangeView.as_view(
        template_name = 'registration/change_password.html'), name='editpassword'),
    path('changepassword/done/', PasswordChangeDoneView.as_view(
        template_name = 'registration/afterchanging.html'), name='password_change_done'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # files
    re_path(r'^files/(?P<path>.*)$', main.get_file),

    # expense
    path('expense/create/', expense.ExpenseCreateView.as_view(), name='expense_create'),
    
    # income
    path('income/create/', income.IncomeCreateView.as_view(), name='income_create'),
    path('api/rooms/', income.get_rooms, name='get_rooms'),

    # room management
    path('room/management/', room.RoomManagementView.as_view(), name='room_management'),
    path('api/room/toggle-status/', room.RoomToggleStatusView.as_view(), name='room_toggle_status'),
]
