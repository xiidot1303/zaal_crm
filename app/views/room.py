from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from app.models import Room


@method_decorator(csrf_exempt, name='dispatch')
class RoomManagementView(TemplateView):
    template_name = 'app/room/room_management.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rooms'] = Room.objects.all().order_by('number')
        return context


@method_decorator(csrf_exempt, name='dispatch')
class RoomToggleStatusView(View):
    def post(self, request, *args, **kwargs):
        try:
            room_id = request.POST.get('room_id')
            if not room_id:
                return JsonResponse({'success': False, 'error': 'Room ID is required'}, status=400)

            room = Room.objects.get(pk=room_id)
            room.is_free = not room.is_free
            if room.is_free:
                room.taken_to = None
            room.save()

            return JsonResponse({
                'success': True,
                'room_id': room.id,
                'is_free': room.is_free,
                'message': 'Room status updated successfully'
            })
        except Room.DoesNotExist:
            return JsonResponse({'success': False, 'error': 'Room not found'}, status=404)
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)