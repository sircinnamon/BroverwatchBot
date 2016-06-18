import discord
import asyncio
import time
from gtts import gTTS
from tempfile import NamedTemporaryFile
import os
import pickle

client = discord.Client()

player_lock = asyncio.Lock()
tts_lock = asyncio.Lock()

enabled = True
message_channel = None
tts_flag = False
use_avconv = True

nicknames = {}

helpmsg = """ COMMAND LIST:
>!bbhelp / !bb    -    Display help message
>!bbon / !gogogadgetbot    -    Enable the bot
>!bbmute / !shutup    -    Disable TTS
>!bbunmute / !speakup    -    Enable TTS
>!bbjoin / !joinvoice    -    Invite bot to current vchat
>!bbleave / !leavevoice    -    Remove bot from vchat
>!bboff / !goaway    -    Disable the bot
>!bbsay <line>    -    Say a line in current channel
>!bbnickname <nickname>    -    Set TTS nickname"""

@client.event
@asyncio.coroutine
def on_ready():
    print('Logged in as')
    print(client.user.name)
    print(client.user.id)
    print('------')
    load_nicknames()

@client.event
@asyncio.coroutine
def on_message(message):
    global message_channel
    global tts_flag
    global enabled

    if (message.content.startswith('!gogogadgetbot') or message.content.startswith('!bbon')):
        yield from client.send_message(message.channel, 'It\'s a me, Broverwatch Bot!')
        enabled = True
    elif (message.content.startswith('!bbhelp') or message.content.startswith('!bb ') or message.content == '!bb'):
            yield from client.send_message(message.channel, helpmsg)
    elif enabled:
        if message.content.startswith('!bbsay'):
            yield from say(message)           
        if (message.content.startswith('!shutup') or message.content.startswith('!bbmute')):
            tts_flag = False
            yield from client.send_message(message.channel, 'I will go quietly into that good night')
        elif (message.content.startswith('!speakup') or message.content.startswith('!bbunmute')):
            tts_flag = True
            yield from client.send_message(message.channel, 'I will not go quietly into that good night')
        elif message.content.startswith('!bbnickname'):
            if len(message.content.split(' ')) < 2:
                yield from client.send_message(message.channel, 'Bad formatting: !bbnickname <nickname>')
            else:
                requested_nickname = message.content[12:]
                set_nickname(message.author, requested_nickname)
                if requested_nickname != 'reset':
                    yield from client.send_message(message.channel, message.author.mention + ' your nickname is now ' + requested_nickname)
        elif (message.content.startswith('!joinvoice') or message.content.startswith('!bbjoin')):
            if message.author.voice_channel == None:
                yield from client.send_message(message.channel,
                message.author.mention + ' You are not in a voice channel')
            else:
                yield from client.join_voice_channel(message.author.voice_channel)
        elif (message.content.startswith('!leavevoice') or message.content.startswith('!bbleave')):
            if client.is_voice_connected(message.server):
                yield from client.voice_client_in(message.server).disconnect()
        elif (message.content.startswith('!goaway') or message.content.startswith('!bboff')):
            yield from client.send_message(message.channel, 'Ok, going away')
            enabled = False

@client.event
@asyncio.coroutine
def on_voice_state_update(before, after):
    global message_channel
    global tts_flag
    global enabled
    if enabled and not client.user == before: #the updated user is not the bot
        if client.is_voice_connected(after.server):
            voice_client = client.voice_client_in(after.server)
            if voice_client.channel == after.voice_channel:
                if(after.id in nicknames):
                    yield from tts_voice_clip(voice_client, nicknames[after.id] + ' has joined the voice channel')
                else:
                    yield from tts_voice_clip(voice_client, after.name + ' has joined the voice channel')
        if client.is_voice_connected(before.server):
            voice_client = client.voice_client_in(before.server)
            if voice_client.channel == before.voice_channel:
                if before.id in nicknames:
                    yield from tts_voice_clip(voice_client, nicknames[before.id] + ' has joined the voice channel')
                else:
                    yield from tts_voice_clip(voice_client, after.name + ' has left the voice channel')
                
def say(message):
    if(len(message.content.split(' ')) == 1):
        yield from client.send_message(message.channel, 'Please give a voice line: \"!bbsay <voiceline>\"')
        return

    filename = 'res/audioclips/' + message.content.split(' ')[1] + '.mp3'
    if os.path.isfile(filename) == False:
        yield from client.send_message(message.channel, 'Voice clip not found. RIP.')
    elif message.author.voice_channel != None and client.voice_client_in(message.server) == None: #author is in vchat bot isnt
        voice_client = yield from client.join_voice_channel(message.author.voice_channel)

        yield from voice_clip(voice_client, filename)
        yield from voice_client.disconnect()
    elif message.author.voice_channel != None and client.voice_client_in(message.server) == message.author.voice_channel: #both in same voice chat
        voice_client = client.voice_client_in(message.server)
        yield from voice_clip(voice_client, filename)
    elif message.author.voice_channel != None and client.voice_client_in(message.server) != message.author.voice_channel: #both in different voice chat
        voice_client = client.voice_client_in(message.server)
        prev_channel = voice_client.channel
        yield from voice_client.move_to(message.author.voice_channel);

        yield from voice_clip(voice_client, filename)
        yield from voice_client.move_to(prev_channel);

def voice_clip(voice_client, filename):
    global use_avconv
    with(yield from player_lock):
        player = voice_client.create_ffmpeg_player(filename, use_avconv=use_avconv)
        player.start()
        while not player.is_done():
            yield from asyncio.sleep(1)

def tts_voice_clip(voice_client, text):
    with(yield from tts_lock):
        tts = gTTS(text=text, lang='en')
        tts.save('data/tts.mp3')
        yield from voice_clip(voice_client, 'data/tts.mp3')
        os.remove('data/tts.mp3')

def set_nickname(user, nickname):
    global nicknames
    if nickname == 'reset':
        del nicknames[user.id]
    else:
        nicknames[user.id] = nickname
    pkl_file = open('data/nicknames.pkl', 'wb')
    pickle.dump(nicknames, pkl_file)
    pkl_file.close()

def load_nicknames():
    global nicknames
    if(os.path.isfile('data/nicknames.pkl') == True):
        pkl_file = open('data/nicknames.pkl', 'rb')
        nicknames = pickle.load(pkl_file)
        pkl_file.close()
            

if(os.environ.get('DISCORD_TOKEN') == None):
    token = input("You must specify the discord bot token: ")
    os.environ['DISCORD_TOKEN'] = token


client.run(os.environ.get('DISCORD_TOKEN'))
