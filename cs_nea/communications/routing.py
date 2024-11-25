from django.urls import re_path
from . import consumers

# Websocket routing for real-time messaging and notifications
websocket_urlpatterns = [
    # Real time messaging routing
    re_path(r"ws/dm/(?P<user_id>\w+)/$", consumers.DirectMessageConsumer.as_asgi()),

    # Notification routing
    re_path(r'ws/notifications/$', consumers.NotificationConsumer.as_asgi()),
]

