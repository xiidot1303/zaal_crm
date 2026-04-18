from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.models import Expense
from app.forms import ExpenseForm


@method_decorator(csrf_exempt, name='dispatch')
class ExpenseCreateView(CreateView):
    model = Expense
    form_class = ExpenseForm
    template_name = 'app/expense/expense_form.html'
    success_url = reverse_lazy('admin:index')

    def form_valid(self, form):
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
