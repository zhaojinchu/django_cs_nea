from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST
from django.contrib.auth.decorators import login_required
from .models import Lesson, CalendarEvent
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from datetime import datetime

@login_required
def calendar_view(request):
    return render(request, "scheduling/calendar.html")


@login_required
@require_GET
def get_calendar_data(request):
    start = timezone.datetime.fromisoformat(request.GET.get("start").replace("Z", "+00:00"))
    end = timezone.datetime.fromisoformat(request.GET.get("end").replace("Z", "+00:00"))

    user_timezone = timezone.get_current_timezone()

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
        events.append({
            "id": f"lesson_{lesson.lesson_id}",
            "title": event_title,
            "start": lesson.start_datetime.astimezone(user_timezone).isoformat(),
            "end": lesson.end_datetime.astimezone(user_timezone).isoformat(),
            "color": "blue",
            "editable": False,
        })

    for event in calendar_events:
        events.append({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.astimezone(user_timezone).isoformat(),
            "end": event.end_datetime.astimezone(user_timezone).isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })

    return JsonResponse(events, safe=False)


# Calendar views for AJAX requests to create, update, and delete events
@login_required
@require_POST
def create_event(request):
    if request.user.user_type != 2:
        return JsonResponse({"error": "Only teachers can create events"}, status=403)

    title = request.POST.get("title")
    start_str = request.POST.get("start")
    end_str = request.POST.get("end")
    all_day = request.POST.get("allDay") == "true"
    event_type = request.POST.get("event_type", "other")

    try:
        if all_day:
            start = timezone.datetime.strptime(start_str, "%Y-%m-%d").date()
            end = timezone.datetime.strptime(end_str, "%Y-%m-%d").date()
            start_datetime = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
            end_datetime = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))
        else:
            start_datetime = timezone.datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
            end_datetime = timezone.datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
            start_datetime = timezone.make_aware(start_datetime)
            end_datetime = timezone.make_aware(end_datetime)

        event = CalendarEvent.objects.create(
            teacher=request.user.teacher,
            title=title,
            start_datetime=start_datetime,
            end_datetime=end_datetime,
            all_day=all_day,
            event_type=event_type,
        )

        return JsonResponse({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)


@login_required
@require_POST
def update_event(request):
    event_id = request.POST.get("id")
    if not event_id.startswith("event_"):
        return JsonResponse({"error": "Can only update calendar events"}, status=400)

    event = get_object_or_404(CalendarEvent, event_id=event_id[6:])
    if event.teacher != request.user.teacher:
        return JsonResponse({"error": "Permission denied"}, status=403)

    title = request.POST.get("title")
    start_str = request.POST.get("start")
    end_str = request.POST.get("end")
    all_day = request.POST.get("allDay") == "true"

    try:
        if all_day:
            start = timezone.datetime.strptime(start_str, "%Y-%m-%d").date()
            end = timezone.datetime.strptime(end_str, "%Y-%m-%d").date()
            event.start_datetime = timezone.make_aware(timezone.datetime.combine(start, timezone.datetime.min.time()))
            event.end_datetime = timezone.make_aware(timezone.datetime.combine(end, timezone.datetime.max.time()))
        else:
            start_datetime = timezone.datetime.strptime(start_str, "%Y-%m-%dT%H:%M:%S")
            end_datetime = timezone.datetime.strptime(end_str, "%Y-%m-%dT%H:%M:%S")
            event.start_datetime = timezone.make_aware(start_datetime)
            event.end_datetime = timezone.make_aware(end_datetime)

        event.title = title
        event.all_day = all_day
        event.save()

        return JsonResponse({
            "id": f"event_{event.event_id}",
            "title": event.title,
            "start": event.start_datetime.isoformat(),
            "end": event.end_datetime.isoformat(),
            "allDay": event.all_day,
            "color": "green",
            "editable": True,
        })
    except ValueError as e:
        return JsonResponse({"error": str(e)}, status=400)


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
