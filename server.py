from aiohttp import web
import socketio
import logging
import datetime
import threading
import time
import random
import sys
import asyncio
from itertools import zip_longest

class Omegle20:
    def __init__(self):
        self.log = logging

        # Show debugging
        self.log.basicConfig(level=logging.DEBUG)

        # Keep track of joined users
        self.users = {}

        # Keep time for new round
        self.next_time = datetime.datetime.now()

        # Setup SocketIO server
        self.sio = socketio.AsyncServer(async_mode='aiohttp', cors_allowed_origins='*')
        self.app = web.Application()
        self.sio.attach(self.app)

        # Serve static files for web application
        self.app.router.add_route('*', '/', self.index_handler)
        self.app.router.add_static('/', path=str('./static/'))

        # Handle connects and disconnects
        self.sio.on('connect')(self.connect)
        self.sio.on('disconnect')(self.disconnect)

        # Handle app events
        self.sio.on('join_wait')(self.join_wait)
        self.sio.on('data')(self.data)

        # Start round (argument is time in seconds)
        try:
            self.timer = TimerThread(self, 120)
            self.timer.start()
        except KeyboardInterrupt:
            sys.exit(0)

        # Serve webapp
        web.run_app(self.app, port=9999)
    
    # Display index
    async def index_handler(self, request):
        return web.FileResponse('./static/index.html')
    
    async def connect(self, sid, environ):
        print('Connected', sid)

        # Add user to list
        self.users[sid] = {
            'name': None,
            'joined': False,
            'room': None,
            'no_match': True
        }

        # Send current round time
        await self.send_time()
    
    async def disconnect(self, sid):
        print('Disconnected', sid)

        await self.sio.emit('disconnect', room=self.users[sid]['room'])
        await self.sio.emit('no_match', room=self.users[sid]['room'])

        for user in self.users:
            if self.users[user]['room'] == self.users[sid]['room']:
                self.users[user]['no_match'] = True

        # Remove user from list
        self.users.pop(sid, None)
    
    async def join_wait(self, sid, data):
        self.users[sid]['name'] = data['name']
        self.users[sid]['joined'] = True

        if len(self.users) == 2:
            await self.next_round()
            return
        
        for user in self.users.keys():
            if user != sid and self.users[user]['no_match'] and self.users[user]['joined']:
                await self.connect_users(user, sid)
    
    async def send_time(self):
        seconds = (self.next_time - datetime.datetime.now()).total_seconds()
        await self.sio.emit('next_time', seconds)
    
    async def clear_rooms(self):
        for sid in self.users.keys():
            if self.users[sid]['room']:
                self.sio.leave_room(sid, self.users[sid]['room'])
                await self.sio.emit('data', {'type': 'disconnect'})
            self.users[sid]['room'] = None
            self.users[sid]['no_match'] = False
    
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
                await self.sio.emit('no_match', room=first)
                continue
        
            if first == None:
                self.users[second]['no_match'] = True
                await self.sio.emit('no_match', room=second)
                continue
        
            await self.connect_users(first, second)

            
    async def connect_users(self, first, second):
        room_name = '%s___%s' % (first, second)
        self.users[first]['room'] = room_name
        self.users[second]['room'] = room_name

        self.users[first]['no_match'] = False
        self.users[second]['no_match'] = False

        self.sio.enter_room(first, room_name)
        self.sio.enter_room(second, room_name)

        await self.sio.emit('ready', room=first)

        await self.sio.emit('remote_name', self.users[first]['name'], room=second)
        await self.sio.emit('remote_name', self.users[second]['name'], room=first)
    

    async def next_round(self):
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
            self.app.next_time = datetime.datetime.now() + datetime.timedelta(seconds=self.seconds)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.app.next_round())
            loop.close()
            time.sleep(self.seconds)

if __name__ == '__main__':
    app = Omegle20()
