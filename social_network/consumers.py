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
            
            self.user = self.scope.get("user")
            if not self.user or self.user.is_anonymous:
                await self.close(code=4001)
                return

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"WebSocket connected: {self.user.username} to room {self.room_name}")

        except KeyError:
            await self.close(code=4000)
        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close(code=4002)

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_group_name'):
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
        except Exception:
            pass

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type', 'chat_message')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'typing':
                await self.handle_typing(data)
            
        except json.JSONDecodeError:
            pass
        except Exception:
            pass

    async def handle_chat_message(self, data):
        try:
            text = data.get('message', '').strip()
            sender_username = data.get('sender', '')
            receiver_username = data.get('receiver', '')
            
            if not text or not sender_username or not receiver_username:
                return

            if not hasattr(self, 'user') or sender_username != self.user.username:
                return

            message = await self.save_message(sender_username, receiver_username, text)
            
            if message:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': text,
                        'sender': sender_username,
                        'receiver': receiver_username,
                        'timestamp': message.timestamp.isoformat() if message.timestamp else None,
                        'message_id': message.id,
                    }
                )
                
        except Exception:
            pass

    async def handle_typing(self, data):
        try:
            is_typing = data.get('is_typing', False)
            sender_username = data.get('sender', '')
            receiver_username = data.get('receiver', '')
            
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'typing_indicator',
                    'is_typing': is_typing,
                    'sender': sender_username,
                    'receiver': receiver_username,
                }
            )
        except Exception:
            pass

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'chat_message',
            'message': event['message'],
            'sender': event['sender'],
            'receiver': event['receiver'],
            'timestamp': event.get('timestamp'),
            'message_id': event.get('message_id'),
        }))

    async def typing_indicator(self, event):
        await self.send(text_data=json.dumps({
            'type': 'typing_indicator',
            'is_typing': event['is_typing'],
            'sender': event['sender'],
            'receiver': event['receiver'],
        }))

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