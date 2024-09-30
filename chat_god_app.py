from twitchio.ext import commands
from twitchio import *
from datetime import datetime, timedelta
from flask import Flask, render_template, session, request
from flask_socketio import SocketIO, emit
import asyncio
import threading
import pytz
import random
import os
from voices_manager import TTSManager

TWITCH_CHANNEL_NAME = os.getenv('CHATGOD_CHANNEL_NAME')

socketio = SocketIO
app = Flask(__name__)
socketio = SocketIO(app, async_mode="threading")

@app.route("/")
def home():
    return render_template('index.html') #redirects to index.html in templates folder

@socketio.on("tts")
def toggletts(value):
    print("TTS: Received the value " + str(value['checked']))
    twitchbot.update_tts_enabled(value['user_number'], value['checked'])

@socketio.on("pickrandom")
def pickrandom(value):
    twitchbot.random_user(value['user_number'])
    print("Getting new random user for user " + str(value['user_number']))

@socketio.on("adduser")
def adduser(value):
    twitchbot.add_user(
        value['user_number'],
        value['current'],
        value['tts_enabled'],
        value['keypassphrase'],
        value['voice_name'],
        value['voice_style'],
    )

@socketio.on("choose")
def chooseuser(value):
    user = twitchbot.update_current(value['user_number'], value['chosen_user'])
    socketio.emit('message_send',
        {
            'message': f"{user.current} was picked!",
            'current_user': f"{user.current}",
            'user_number': value['user_number']
        }
    )

@socketio.on("voicename")
def choose_voice_name(value):
    if (value['voice_name']) != None:
        twitchbot.update_voice_name(int(value['user_number']), value['voice_name'])
        print("Updating voice name to: " + value['voice_name'])

@socketio.on("voicestyle")
def choose_voice_style(value):
    if (value['voice_style']) != None:
        twitchbot.update_voice_style(value['user_number'], value['voice_style'])
        print("Updating voice style to: " + value['voice_style'])

class User:
    def __init__(self, current, tts_enabled, keypassphrase, voice_name, voice_style):
        self.current = current
        self.tts_enabled = tts_enabled
        self.keypassphrase = keypassphrase
        self.voice_name = voice_name
        self.voice_style = voice_style
        self.pool = {}
        0

class Bot(commands.Bot):
    seconds_active = 450 # of seconds until a chatter is booted from the list
    max_users = 2000 # of users who can be in user pool
    tts_manager = None

    def __init__(self):
        self.tts_manager = TTSManager()
        self.users = {}

        #connects to twitch channel
        super().__init__(token=os.getenv('TWITCH_ACCESS_TOKEN'), prefix='?', initial_channels=[TWITCH_CHANNEL_NAME])

    async def event_ready(self):
        print(f'Logged in as | {self.nick}')
        print(f'User id is | {self.user_id}')

    async def event_message(self, message):
        await self.process_message(message)

    async def process_message(self, message: Message):
        for user_number, user in self.users.items():
            # If this is our current_user, read out their message
            if message.author.name == user.current:
                socketio.emit('message_send',
                    {
                        'message': f"{message.content}",
                        'current_user': f"{user.current}",
                        'user_number': user_number
                    }
                )
                if user.tts_enabled:
                    self.tts_manager.text_to_audio(message.content, user.voice_name, user.voice_style)

            # Add this chatter to the user pool
            if message.content == user.keypassphrase:
                if message.author.name.lower() in user.pool:
                    user.pool.pop(message.author.name.lower())
                # Add user to end of pool with new msg time
                user.pool[message.author.name.lower()] = message.timestamp
                # Now we remove the oldest viewer if they're past the activity threshold, or if we're past the max # of users
                activity_threshold = datetime.now(pytz.utc) - timedelta(seconds=self.seconds_active) # calculate the cutoff time
                # The first user in the dict is the user who chatted longest ago
                oldest_user = list(user.pool.keys())[0]
                if user.pool[oldest_user].replace(tzinfo=pytz.utc) < activity_threshold or len(user.pool) > self.max_users:
                    user.pool.pop(oldest_user) # remove them from the list
                    if len(user.pool) == self.max_users:
                        print(f"{oldest_user} was popped due to hitting max users")
                    else:
                        print(f"{oldest_user} was popped due to not talking for {self.seconds_active} seconds")


    #picks a random user from the queue
    def random_user(self, user_number):
        try:
            user = self.users[user_number]
            user.current = random.choice(list(user.pool.keys()))
            socketio.emit('message_send',
                {
                    'message': f"{user.current} was picked!",
                    'current_user': user.current,
                    'user_number': user_number
                }
            )
            print("Random User is: " + user.current)
        except Exception:
            return

    def add_user(self, user_number, current, tts_enabled, keypassphrase, voice_name, voice_style):
        user = User(
            current,
            tts_enabled,
            keypassphrase,
            voice_name,
            voice_style
        )
        self.users[user_number] = user

    def update_current(self, user_number, current):
        user = self.users[user_number]
        user.current = current
        return user

    def update_tts_enabled(self, user_number, tts_enabled):
        self.users[user_number].tts_enabled = tts_enabled

    def update_voice_name(self, user_number, voice_name):
        self.users[user_number].voice_name = voice_name

    def update_voice_style(self, user_number, voice_style):
        self.users[user_number].voice_style = voice_style



def startTwitchBot():
    global twitchbot
    asyncio.set_event_loop(asyncio.new_event_loop())
    twitchbot = Bot()
    twitchbot.run()

if __name__=='__main__':

    # Creates and runs the twitchio bot on a separate thread
    bot_thread = threading.Thread(target=startTwitchBot)
    bot_thread.start()

    socketio.run(app)
