from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from asgiref.sync import sync_to_async
from app.models import Income, Accommodation, Room
from app.forms import IncomeForm


@method_decorator(csrf_exempt, name='dispatch')
class IncomeCreateView(CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'app/income/income_form.html'
    success_url = reverse_lazy('admin:index')

    def form_valid(self, form):
        cleaned_data = form.cleaned_data
        income_type = cleaned_data.get('type')
        
        # Handle accommodation creation if type is 'accommodation'
        if income_type == 'accommodation':
            try:
                room_id = cleaned_data.get('accommodation_room')
                days = cleaned_data.get('accommodation_days')
                check_in = cleaned_data.get('accommodation_check_in')
                check_out = cleaned_data.get('accommodation_check_out')
                price = cleaned_data.get('accommodation_price')
                
                room = Room.objects.get(pk=room_id)
                accommodation = Accommodation.objects.create(
                    room=room,
                    days=days,
                    check_in=check_in,
                    check_out=check_out,
                    price=price
                )
                
                # Attach accommodation to income
                self.object = form.save()
                self.object.accommondation = accommodation
                self.object.save()
            except Room.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'errors': {'accommodation_room': 'Invalid room selected'}
                }, status=400)
        else:
            self.object = form.save()
        
        if self.request.headers.get('Content-Type') == 'application/json' or self.request.POST.get('is_ajax'):
            return JsonResponse({
                'success': True,
                'income_id': self.object.id,
                'message': 'Доход успешно создан'
            })
        return super().form_valid(form)

    def form_invalid(self, form):
        if self.request.headers.get('Content-Type') == 'application/json' or self.request.POST.get('is_ajax'):
            return JsonResponse({
                'success': False,
                'errors': form.errors
            }, status=400)
        return super().form_invalid(form)


@csrf_exempt
def get_rooms(request):
    """API endpoint to fetch all rooms as JSON"""
    rooms = Room.objects.all().order_by('-is_free').values('id', 'number', 'is_free')
    return JsonResponse({'rooms': list(rooms)})