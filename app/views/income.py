from django.views.generic import CreateView
from django.urls import reverse_lazy
from django.http import HttpResponseRedirect, JsonResponse
from django.db import transaction
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from app.models import Income, Accommodation, Room, Staff
from app.forms import AccommodationFormSet, IncomeForm


def get_staff_from_request(request):
    staff_id = request.GET.get('staff_id') or request.POST.get('staff_id')
    if not staff_id:
        return None
    try:
        return Staff.objects.get(pk=int(staff_id))
    except (Staff.DoesNotExist, ValueError, TypeError):
        return None


@method_decorator(csrf_exempt, name='dispatch')
class IncomeCreateView(CreateView):
    model = Income
    form_class = IncomeForm
    template_name = 'app/income/income_form.html'
    success_url = reverse_lazy('admin:index')

    def get_accommodation_formset(self):
        return AccommodationFormSet(
            self.request.POST or None,
            prefix='accommodations',
            require_at_least_one=self.request.POST.get('type') == 'accommodation',
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.setdefault('accommodation_formset', self.get_accommodation_formset())
        return context

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        formset = self.get_accommodation_formset()

        form_is_valid = form.is_valid()
        formset_is_valid = True
        if request.POST.get('type') == 'accommodation':
            formset_is_valid = formset.is_valid()

        if form_is_valid and formset_is_valid:
            return self.forms_valid(form, formset)
        return self.forms_invalid(form, formset)

    def forms_valid(self, form, formset):
        staff = get_staff_from_request(self.request)
        if staff:
            form.instance.staff = staff

        with transaction.atomic():
            self.object = form.save()

            if form.cleaned_data.get('type') == 'accommodation':
                for accommodation_data in formset.cleaned_data:
                    if not accommodation_data:
                        continue

                    Accommodation.objects.create(
                        income=self.object,
                        room=accommodation_data['room'],
                        days=accommodation_data['days'],
                        check_in=accommodation_data['check_in'],
                        check_out=accommodation_data['check_out'],
                        price=accommodation_data['price'],
                    )

        if self.is_ajax_request():
            return JsonResponse({
                'success': True,
                'income_id': self.object.id,
                'message': 'Доход успешно создан'
            })
        return HttpResponseRedirect(self.get_success_url())

    def forms_invalid(self, form, formset):
        if self.is_ajax_request():
            return JsonResponse({
                'success': False,
                'errors': {
                    'form': form.errors,
                    'accommodations': formset.errors,
                    'accommodations_non_form': formset.non_form_errors(),
                }
            }, status=400)
        return self.render_to_response(self.get_context_data(form=form, accommodation_formset=formset))

    def is_ajax_request(self):
        return (
            self.request.headers.get('Content-Type') == 'application/json'
            or self.request.POST.get('is_ajax')
        )


@csrf_exempt
def get_rooms(request):
    """API endpoint to fetch all rooms as JSON"""
    rooms = Room.objects.all().order_by('-is_free').values('id', 'number', 'is_free')
    return JsonResponse({'rooms': list(rooms)})
