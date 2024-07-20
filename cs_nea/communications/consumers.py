import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.db import models
from django.utils import timezone
from .models import Message, MessageConfig

User = get_user_model()


class DirectMessageConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope["user"]
        self.other_user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.room_name = f"dm_{min(self.user.id, int(self.other_user_id))}_{max(self.user.id, int(self.other_user_id))}"
        self.room_group_name = f"chat_{self.room_name}"

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)

        await self.accept()

        previous_messages = await self.get_previous_messages()
        for message in previous_messages:
            message_data = await self.get_message_data(message)
            await self.send(text_data=json.dumps(message_data))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        if await self.can_send_message():
            await self.save_message(message)
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    "type": "chat_message",
                    "message": message,
                    "sender": self.user.get_full_name(),
                    "timestamp": timezone.now().isoformat(),
                },
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))

    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(id=self.other_user_id)
        Message.objects.create(sender=self.user, receiver=other_user, content=content)

    @database_sync_to_async
    def get_previous_messages(self):
        other_user = User.objects.get(id=self.other_user_id)
        return list(
            Message.objects.filter(
                (models.Q(sender=self.user) & models.Q(receiver=other_user))
                | (models.Q(sender=other_user) & models.Q(receiver=self.user))
            ).order_by("-timestamp")[:50][::-1]
        )

    @database_sync_to_async
    def get_message_data(self, message):
        return {
            "message": message.content,
            "sender": message.sender.get_full_name(),
            "timestamp": message.timestamp.isoformat(),
        }

    @database_sync_to_async
    def can_send_message(self):
        other_user = User.objects.get(id=self.other_user_id)
        config = MessageConfig.objects.filter(
            (models.Q(student=self.user) & models.Q(teacher=other_user))
            | (models.Q(student=other_user) & models.Q(teacher=self.user))
        ).first()
        return not config or not config.read_only

    @database_sync_to_async
    def save_message(self, content):
        other_user = User.objects.get(id=self.other_user_id)
        return Message.objects.create(
            sender=self.user, receiver=other_user, content=content
        )

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        if await self.can_send_message():
            saved_message = await self.save_message(message)
            message_data = await self.get_message_data(saved_message)
            await self.channel_layer.group_send(
                self.room_group_name, {"type": "chat_message", **message_data}
            )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event))
