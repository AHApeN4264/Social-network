import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from .models import Message

logger = logging.getLogger(__name__)
User = get_user_model()

class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            self.room_name = self.scope['url_route']['kwargs']['room_name']
            self.room_group_name = f'chat_{self.room_name}'

            if not self.scope["user"].is_authenticated:
                await self.close(code=4001)
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()

        except Exception as e:
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
        except Exception:
            pass

    async def receive(self, text_data=None, bytes_data=None):
        if text_data is None:
            return

        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            sender_username = data.get('sender')
            receiver_username = data.get('receiver')

            if not message or not sender_username or not receiver_username:
                return

            saved_message = await self.save_message(sender_username, receiver_username, message)

            if saved_message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat.message',
                        'message': message,
                        'sender': sender_username,
                        'receiver': receiver_username,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'message_id': saved_message.id,
                    }
                )

        except json.JSONDecodeError:
            pass
        except Exception:
            pass

    async def chat_message(self, event):
        payload = {
            'type': 'chat.message',
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'timestamp': event['timestamp'],
            'message_id': event.get('message_id'),
        }

        await self.send(text_data=json.dumps(payload))

    async def message_edited(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_edited',
            'message_id': event.get('message_id'),
            'text': event.get('text'),
            'timestamp': event.get('timestamp'),
            'sender': event.get('sender'),
        }))

    async def message_deleted(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_deleted',
            'message_id': event.get('message_id'),
            'sender': event.get('sender'),
        }))

    @database_sync_to_async
    def save_message(self, sender_username, receiver_username, text):
        try:
            sender = User.objects.get(username=sender_username)
            receiver = User.objects.get(username=receiver_username)

            msg = Message.objects.create(
                sender=sender,
                receiver=receiver,
                text=text,
            )
            return msg
        except User.DoesNotExist:
            return None
        except Exception:
            return None