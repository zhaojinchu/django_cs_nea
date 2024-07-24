from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from .models import Lesson, CalendarEvent
from django.shortcuts import get_object_or_404, render
from django.utils.dateparse import parse_datetime
from django.core.serializers.json import DjangoJSONEncoder
from django.utils import timezone


@login_required
def calendar_view(request):
    return render(request, "scheduling/calendar.html")


@login_required
@require_GET
def get_calendar_data(request):
    start = timezone.datetime.fromisoformat(
        request.GET.get("start").replace("Z", "+00:00")
    )
    end = timezone.datetime.fromisoformat(request.GET.get("end").replace("Z", "+00:00"))

    events = []

    if request.user.user_type == 2:  # Teacher
        lessons = Lesson.objects.filter(
            teacher=request.user.teacher,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
        calendar_events = CalendarEvent.objects.filter(
            teacher=request.user.teacher,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
    elif request.user.user_type == 1:  # Student
        lessons = Lesson.objects.filter(
            student=request.user.student,
            start_datetime__gte=start,
            end_datetime__lte=end,
        )
        calendar_events = []  # Students don't see calendar events
    else:
        lessons = []
        calendar_events = []

    for lesson in lessons:
        event_title = (
            f"Lesson with {lesson.student.user.get_full_name()}"
            if request.user.user_type == 2
            else f"Lesson with {lesson.teacher.user.get_full_name()}"
        )
        events.append(
            {
                "id": f"lesson_{lesson.lesson_id}",
                "title": event_title,
                "start": lesson.start_datetime.isoformat(),
                "end": lesson.end_datetime.isoformat(),
                "color": "blue",
                "editable": False,
            }
        )

    for event in calendar_events:
        events.append(
            {
                "id": f"event_{event.event_id}",
                "title": event.title,
                "start": event.start_datetime.isoformat(),
                "end": event.end_datetime.isoformat(),
                "color": "green",
                "editable": True,
            }
        )

    return JsonResponse(events, safe=False)


# Calendar views for AJAX requests to create, update, and delete events
@login_required
@require_POST
def create_event(request):
    if request.user.user_type != 2:
        return JsonResponse({"error": "Only teachers can create events"}, status=403)

    title = request.POST.get("title")
    start = timezone.datetime.fromisoformat(request.POST.get("start"))
    end = timezone.datetime.fromisoformat(request.POST.get("end"))
    event_type = request.POST.get("event_type", "other")

    event = CalendarEvent.objects.create(
        teacher=request.user.teacher,
        title=title,
        start_datetime=start,
        end_datetime=end,
        event_type=event_type,
    )

    return JsonResponse(
        {
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "color": "green",
            "editable": True,
        }
    )


@login_required
@require_POST
def update_event(request):
    event_id = request.POST.get("id")
    if not event_id.startswith("event_"):
        return JsonResponse({"error": "Can only update calendar events"}, status=400)

    event = get_object_or_404(CalendarEvent, event_id=event_id[6:])
    if event.teacher != request.user.teacher:
        return JsonResponse({"error": "Permission denied"}, status=403)

    event.start_datetime = timezone.datetime.fromisoformat(
        request.POST.get("start").replace("Z", "+00:00")
    )
    event.end_datetime = timezone.datetime.fromisoformat(
        request.POST.get("end").replace("Z", "+00:00")
    )
    event.save()

    return JsonResponse({"success": True})


@login_required
@require_POST
def delete_event(request):
    event_id = request.POST.get("id")
    if not event_id.startswith("event_"):
        return JsonResponse({"error": "Can only delete calendar events"}, status=400)

    event = get_object_or_404(CalendarEvent, event_id=event_id[6:])
    if event.teacher != request.user.teacher:
        return JsonResponse({"error": "Permission denied"}, status=403)

    event.delete()
    return JsonResponse({"success": True})
