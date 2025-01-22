from django.utils.timezone import activate, deactivate
from pytz import timezone as pytz_timezone
from pytz.exceptions import UnknownTimeZoneError

class UserTimezoneMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Check if the user is authenticated and has a timezone
        if request.user.is_authenticated:
            user_timezone = getattr(request.user, "timezone")  # Default to UTC
            try:
                activate(pytz_timezone(user_timezone))
            except UnknownTimeZoneError:
                activate('UTC')  # Fallback to UTC for invalid timezones
        else:
            deactivate()  # Use the default timezone if the user is not authenticated

        response = self.get_response(request)
        return response
