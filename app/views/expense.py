from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.models import Expense, Staff
from app.forms import ExpenseForm


def get_staff_from_request(request):
    staff_id = request.GET.get('staff_id') or request.POST.get('staff_id')
    if not staff_id:
        return None
    try:
        return Staff.objects.get(pk=int(staff_id))
    except (Staff.DoesNotExist, ValueError, TypeError):
        return None


@method_decorator(csrf_exempt, name='dispatch')
class ExpenseCreateView(CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'app/expense/expense_form.html'
    success_url = reverse_lazy('admin:index')

    def form_valid(self, form):
        staff = get_staff_from_request(self.request)
        if staff:
            form.instance.staff = staff

        self.object = form.save()
        if self.request.headers.get('Content-Type') == 'application/json' or self.request.POST.get('is_ajax'):
            return JsonResponse({
                'success': True,
                'expense_id': self.object.id,
                'message': 'Расход успешно создан'
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('Content-Type') == 'application/json' or self.request.POST.get('is_ajax'):
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)
