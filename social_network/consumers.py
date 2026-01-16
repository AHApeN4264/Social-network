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
                await self.close()
                return

            logger.info(f"Connecting to room: {self.room_name}")

            await self.channel_layer.group_add(
                self.room_group_name,
                self.channel_name
            )

            await self.accept()
            logger.info(f"WebSocket connected successfully to: {self.room_name}")

        except Exception as e:
            logger.error(f"Connection error: {e}")
            await self.close()

    async def disconnect(self, close_code):
        try:
            if hasattr(self, 'room_group_name') and self.room_group_name:
                await self.channel_layer.group_discard(
                    self.room_group_name,
                    self.channel_name
                )
                logger.info(f"WebSocket disconnected from: {getattr(self, 'room_name', None)}")
        except Exception as e:
            logger.error(f"Disconnection error: {e}")

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message = data.get('message', '').strip()
            sender_username = data.get('sender')
            receiver_username = data.get('receiver')

            if not message or not sender_username or not receiver_username:
                logger.error("Missing required fields in message")
                return

            logger.info(f"Message received: {sender_username} -> {receiver_username}: {message}")

            saved_message = await self.save_message(sender_username, receiver_username, message)

            if saved_message:
                logger.info(f"Message saved to DB with ID: {saved_message.id}")

                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message',
                        'message': message,
                        'sender': sender_username,
                        'receiver': receiver_username,
                        'timestamp': saved_message.timestamp.isoformat(),
                        'message_id': saved_message.id
                    }
                )
            else:
                logger.error("Failed to save message to database")

        except json.JSONDecodeError:
            logger.error("Invalid JSON in WebSocket message")
        except Exception as e:
            logger.error(f"Error in receive: {e}")

    async def chat_message(self, event):
        try:
            payload = {
                'message': event['message'],
                'sender': event['sender'],
                'receiver': event['receiver'],
                'timestamp': event.get('timestamp'),
                'message_id': event.get('message_id')
            }

            for k in ['file_url', 'file_name', 'file_type', 'file_size']:
                if k in event:
                    payload[k] = event[k]

            await self.send(text_data=json.dumps(payload))
            logger.info(f"Broadcasted message: {payload}")

        except Exception as e:
            logger.error(f"Error in chat_message: {e}")

    @database_sync_to_async
    def save_message(self, sender_username, receiver_username, text):
        try:
            sender = User.objects.get(username=sender_username)
            receiver = User.objects.get(username=receiver_username)

            message = Message.objects.create(
                sender=sender,
                receiver=receiver,
                text=text
            )
            return message
        except User.DoesNotExist:
            logger.error(f"User not found: {sender_username} or {receiver_username}")
            return None
        except Exception as e:
            logger.error(f"Error saving message: {e}")
            return None

    async def message_edited(self, event):
        try:
            await self.send(text_data=json.dumps({
                'type': 'message_edited',
                'message_id': event.get('message_id'),
                'text': event.get('text'),
                'timestamp': event.get('timestamp'),
                'sender': event.get('sender'),
                'receiver': event.get('receiver')
            }))
        except Exception as e:
            logger.error(f"Error in message_edited handler: {e}")

    async def message_deleted(self, event):
        try:
            await self.send(text_data=json.dumps({
                'type': 'message_deleted',
                'message_id': event.get('message_id'),
                'sender': event.get('sender'),
                'receiver': event.get('receiver')
            }))
        except Exception as e:
            logger.error(f"Error in message_deleted handler: {e}")
