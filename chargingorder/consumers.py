# coding=utf-8
from chargingorder.models import GroupName

__author__ = 'Administrator'

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
import json


class ChargingConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        pile_sn = self.scope['url_route']['kwargs']['pile_sn']
        gun_num = self.scope['url_route']['kwargs']['gun_num']
        self.room_group_name = 'group_{0}_{1}'.format(pile_sn, gun_num)
        print("ChargingConsumer", pile_sn, gun_num, self.channel_name)
        # # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        await database_sync_to_async(self.create_group)(self.room_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        await database_sync_to_async(self.delete_group)(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):

        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat.message',
                "message": text_data,
            }
        )

    # Receive message from room group
    async def chat_message(self, event):
        message = event["message"]
        print("chat_message", type(message), message)
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    def create_group(self, group_name, channel_name):
        try:
            group = GroupName.objects.get(name=group_name)
            group.nums = group.nums + 1
            group.save()
        except GroupName.DoesNotExist as ex:
            group = GroupName()
            group.name = group_name
            group.channel_name = channel_name
            group.nums = 1
            group.save()

    def delete_group(self, group_name, channel_name):
        try:
            group = GroupName.objects.get(name=group_name)
            if group.nums > 1:
                group.nums = group.nums - 1
                group.save()
            else:
                group.delete()
        except GroupName.DoesNotExist as ex:
            pass

