from aiohttp import web
import socketio
import logging
import datetime
import threading
import time
import random
import asyncio
from itertools import zip_longest

class Omegle20:
    def __init__(self):
        self.log = logging
        self.log.basicConfig(level=logging.DEBUG)

        self.users = {}
        self.next_round = datetime.datetime.now()

        self.sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
        self.app = web.Application()
        self.sio.attach(self.app)

        self.app.router.add_route('*', '/', self.index_handler)
        self.app.router.add_static('/', path=str('./static/'))

        self.sio.on('connect')(self.connect)
        self.sio.on('disconnect')(self.disconnect)

        self.sio.on('join_wait')(self.join_wait)
        self.sio.on('data')(self.data)

        self.timer = TimerThread(self, 300)
        self.timer.start()

        web.run_app(self.app, port=9999)
    
    async def index_handler(self, request):
        return web.FileResponse('./static/index.html')
    
    async def connect(self, sid, environ):
        print('Connected', sid)
        self.sio.enter_room(sid, 'default')
        self.users[sid] = {
            'name': None,
            'joined': False,
            'room': None,
            'no_match': False
        }
        await self.send_time()
    
    async def disconnect(self, sid):
        print('Disconnected', sid)
        self.users.pop(sid, None)
    
    async def join_wait(self, sid, data):
        self.users[sid]['name'] = data['name']
        self.users[sid]['joined'] = True

        if len(self.users) > 1:
            await self.next_round()
    
    async def send_time(self):
        seconds = (self.next_round - datetime.datetime.now()).total_seconds()
        await self.sio.emit('next_round', seconds)
    
    async def clear_rooms(self):
        for sid in self.users.keys():
            if self.users[sid]['room']:
                self.sio.leave_room(sid, self.users[sid]['room'])
            self.users[sid]['room'] = None
            self.users[sid]['no_match'] = False
        await self.sio.emit('data', {'type': 'disconnect'})
    
    async def match_users(self):
        users = []
        for sid, user in self.users.items():
            if not user['joined']:
                continue
            users.append(sid)
        
        random.shuffle(users)

        for first, second in self.grouper(users, 2):
            if second == None:
                self.users[first]['no_match'] = True
                continue

            room_name = '%s_%s' % (first, second)
            self.users[first]['room'] = room_name
            self.users[second]['room'] = room_name

            self.sio.enter_room(first, room_name)
            self.sio.enter_room(second, room_name)

            await self.sio.emit('ready', room=room_name, skip_sid=sid)

    async def next_round(self, next_time):
        await self.clear_rooms()
        await self.match_users()
        await self.send_time()
    
    async def data(self, sid, data):
        if self.users[sid]['room']:
            await self.sio.emit('data', data, room=self.users[sid]['room'], skip_sid=sid)
    
    def grouper(self, iterable, num, fillvalue=None):
        args = [iter(iterable)] * num
        return zip_longest(fillvalue=fillvalue, *args)

class TimerThread(threading.Thread):
    def __init__(self, app, seconds):
        super().__init__()
        self.app = app
        self.seconds = seconds
    
    def run(self):
        while True:
            self.app.next_round = datetime.datetime.now() + datetime.timedelta(seconds=self.seconds)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.app.next_round())
            loop.close()
            time.sleep(self.seconds)

if __name__ == '__main__':
    app = Omegle20()
