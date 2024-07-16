from calendar import HTMLCalendar, weekheader
from datetime import date, timedelta
from .models import Lesson, OtherEvent
from django.utils import timezone

class LessonCalendar(HTMLCalendar):
    def __init__(self, year=None, month=None, week=None, lessons=None, other_events=None):
        self.year = year
        self.month = month
        self.week = week
        self.lessons = lessons or []
        self.other_events = other_events or []
        super(LessonCalendar, self).__init__()

    def formatday(self, day, weekday):
        if day == 0:
            return '<td class="p-2 border border-gray-200 bg-gray-100"></td>'
        
        today = timezone.now().date()   
        try:
            date_obj = date(self.year, self.month, day)
        except ValueError:
            return '<td class="p-2 border border-gray-200 bg-gray-100"></td>'
        
        classes = ['p-2', 'border', 'border-gray-200', 'align-top']
        if date_obj == today:
            classes.append('bg-yellow-100')
        elif date_obj < today:
            classes.append('bg-gray-50')
        
        lessons_for_day = [lesson for lesson in self.lessons if lesson.start_datetime.date() == date_obj]
        events_for_day = [event for event in self.other_events if event.start_datetime.date() == date_obj]
        
        d = f"<td class='{' '.join(classes)}'>"
        d += f"<div class='flex flex-col h-full'>"
        d += f"<span class='text-sm font-semibold mb-1'>{day}</span>"
        d += "<div class='flex-grow'>"
        for lesson in lessons_for_day:
            d += f'<div class="text-xs p-1 bg-purple-200 rounded mb-1">{lesson.start_datetime.strftime("%H:%M")} - Lesson</div>'
        for event in events_for_day:
            d += f'<div class="text-xs p-1 bg-blue-200 rounded mb-1">{event.start_datetime.strftime("%H:%M")} - {event.event_description}</div>'
        d += "</div></div></td>"
        return d
    
    def formatweek(self, theweek):
        week = ''
        for d, weekday in theweek:
            week += self.formatday(d, weekday)
        return f'<tr>{week}</tr>'

    def formatmonth(self, withyear=True):
        cal = f'<table class="calendar table-auto w-full border-collapse h-full">\n'
        cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
        cal += f'{self.formatweekheader()}\n'
        for week in self.monthdays2calendar(self.year, self.month):
            cal += f'{self.formatweek(week)}\n'
        return cal
    
    def formatweek_view(self):
        month_calendar = self.monthdays2calendar(self.year, self.month)
        week_dates = month_calendar[self.week - 1]

        cal = f'<table class="calendar table-auto w-full border-collapse h-full">\n'
        cal += f'<tr><th colspan="7">{date(self.year, self.month, 1).strftime("%B %Y")} - Week {self.week}</th></tr>\n'
        
        # Add day names
        cal += '<tr>'
        for day_name in weekheader(7).split():  # Use weekheader() function directly
            cal += f'<th class="p-2 border border-gray-200">{day_name}</th>'    
        cal += '</tr>\n'
    
        # Add day numbers
        cal += '<tr>'
        for day, weekday in week_dates:
            if day != 0:
                cal += f'<th class="p-2 border border-gray-200">{day}</th>'
            else:
                cal += '<th class="p-2 border border-gray-200"></th>'
        cal += '</tr>\n'
        
        # Add events (without day numbers in the cells)
        cal += '<tr class="h-full">'
        for day, weekday in week_dates:
            if day != 0:
                date_obj = date(self.year, self.month, day)
                lessons_for_day = [lesson for lesson in self.lessons if lesson.start_datetime.date() == date_obj]
                events_for_day = [event for event in self.other_events if event.start_datetime.date() == date_obj]
                
                classes = ['p-2', 'border', 'border-gray-200', 'align-top']
                if date_obj == timezone.now().date():
                    classes.append('bg-yellow-100')
                elif date_obj < timezone.now().date():
                    classes.append('bg-gray-50')
                
                d = f"<td class='{' '.join(classes)}'>"
                d += "<div class='flex flex-col h-full'>"
                for lesson in lessons_for_day:
                    d += f'<div class="text-xs p-1 bg-purple-200 rounded mb-1">{lesson.start_datetime.strftime("%H:%M")} - Lesson</div>'
                for event in events_for_day:
                    d += f'<div class="text-xs p-1 bg-blue-200 rounded mb-1">{event.start_datetime.strftime("%H:%M")} - {event.event_description}</div>'
                d += "</div></td>"
                cal += d
            else:
                cal += '<td class="p-2 border border-gray-200 bg-gray-100"></td>'
        cal += '</tr>\n'
        
        cal += '</table>'
        return cal