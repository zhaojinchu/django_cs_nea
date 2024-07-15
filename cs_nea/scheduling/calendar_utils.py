# scheduling/calendar_utils.py

from calendar import HTMLCalendar
from datetime import date
from .models import Lesson, OtherEvent

class LessonCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None):
        self.year = year
        self.month = month
        super(LessonCalendar, self).__init__()

    def formatday(self, day, lessons, other_events):
        lessons_for_day = lessons.filter(start_datetime__day=day)
        events_for_day = other_events.filter(start_datetime__day=day)
        d = ''
        for lesson in lessons_for_day:
            d += f'<div class="text-xs p-1 bg-purple-200 rounded mb-1">{lesson.start_datetime.strftime("%H:%M")} - Lesson</div>'
        for event in events_for_day:
            d += f'<div class="text-xs p-1 bg-blue-200 rounded mb-1">{event.start_datetime.strftime("%H:%M")} - {event.event_description}</div>'
        if day != 0:
            return f"<td class='p-2 border border-gray-200'><span class='date'>{day}</span><div class='events'>{d}</div></td>"
        return '<td class="p-2 border border-gray-200"></td>'

    def formatweek(self, theweek, lessons, other_events):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, lessons, other_events)
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
    
    
    
    
