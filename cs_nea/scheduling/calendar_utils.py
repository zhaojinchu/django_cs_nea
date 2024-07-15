from calendar import HTMLCalendar
from datetime import date
from .models import Lesson, OtherEvent
from django.utils import timezone

class LessonCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(LessonCalendar, self).__init__()

    def formatday(self, day, weekday, lessons, other_events):
        today = timezone.now().date()
        if day == 0:
            return '<td class="p-2 border border-gray-200 bg-gray-100"></td>'
        else:
            date_obj = date(self.year, self.month, day)
            classes = ['p-2', 'border', 'border-gray-200']
            if date_obj == today:
                classes.append('bg-yellow-100')
            elif date_obj < today:
                classes.append('bg-gray-50')
            
            lessons_for_day = lessons.filter(start_datetime__date=date_obj)
            events_for_day = other_events.filter(start_datetime__date=date_obj)
            
            d = f"<td class='{' '.join(classes)}'>"
            d += f"<span class='date'>{day}</span>"
            for lesson in lessons_for_day:
                d += f'<div class="text-xs p-1 bg-purple-200 rounded mb-1">{lesson.start_datetime.strftime("%H:%M")} - Lesson</div>'
            for event in events_for_day:
                d += f'<div class="text-xs p-1 bg-blue-200 rounded mb-1">{event.start_datetime.strftime("%H:%M")} - {event.event_description}</div>'
            d += "</td>"
            return d

    def formatweek(self, theweek, lessons, other_events):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, weekday, lessons, other_events)
        return f'<tr>{week}</tr>'

    def formatmonth(self, withyear=True):
        lessons = Lesson.objects.filter(start_datetime__year=self.year, start_datetime__month=self.month)
        other_events = OtherEvent.objects.filter(start_datetime__year=self.year, start_datetime__month=self.month)

        cal = f'<table class="calendar table-auto w-full border-collapse">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week, lessons, other_events)}\n'
        return cal  