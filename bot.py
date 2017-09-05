"""
Twitch bot

    TODO ( Soon TM ):
        * Check if user has mod/sub priviliges when using commands
        * Fetch moderator-list for channels from Twitch
        * Check that the bot actually connects to twitch and the channels on startup
        * Move commands.py and blacklist.py to json or something for easier live editing?
        * Make it so commands can take arguments
        * Allow blacklist to contain regex
"""

import socket
import re
from time import sleep

from commands import commands
from config import config
from blacklist import blacklist

class TwitchBot():

    def __init__(self):
        self.sock = socket.socket()

    def connect(self, channels):
        """Establish a connection with Twitch IRC and connect to channels"""
        if config['debug']:
            print("Connecting to Twitch")

        self.sock.connect((config['host'], config['port']))
        self.sock.send(f"PASS {config['oauth_pass']}\r\n".encode("utf-8"))
        self.sock.send(f"NICK {config['nick']}\r\n".encode("utf-8"))

        for channel in channels:
            self.join_channel(channel)

    def run(self):
        while True:
            response = self.sock.recv(1024).decode("utf-8")
            self.handle_message(response)
            sleep(2) # To prevent getting banned from sending to many messages (20 per 30sec)

    def join_channel(self, channel, greeting="/me has joined the channel"):
        self.sock.send(f"JOIN #{channel}\r\n".encode("utf-8"))
        self.send_message(greeting, channel)

    def respond_to_ping(self):
        self.sock.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
        if config['debug']:
            print("Pinging server")

    def send_message(self, message, channel):
        """Sends a message to a Twitch channel"""
        self.sock.send(f"PRIVMSG #{channel} :{message}\r\n".encode("utf-8"))
        if config['debug']:
            print(f"OUT - {channel}: {message}")

    def handle_message(self, message):
        """Decide what to do with a message from server"""

        chat_message = re.compile(r"^:\w+!\w+@\w+\.tmi\.twitch\.tv PRIVMSG #\w+ :")
        if re.match(chat_message, message): # Message is from a chat
            channel = message[1::].split("!")[0]
            user = re.search(r'\w+', message).group(0)
            message = chat_message.sub("", message)[:-2]

            res = self.check_blacklist(message, channel)
            if res[0] != -1:
                self.timeout_user(channel, user, res[0], res[1])
            elif message[0] == "!":
                self.handle_commands(message[1::], channel, user)

        elif message == "PING :tmi.twitch.tv\r\n":
            self.respond_to_ping()

    def handle_commands(self, command, channel, username):
        """Execute a command"""
        user_auth_level = self.get_user_authority_level(channel, username)
        for group in ['global', channel]:
            for auth_level in user_auth_level:
                if command in commands[group][auth_level]:
                    self.send_message(commands[group][command], channel)

    def get_user_authority_level(self, channel, username):
        authority_levels = ['channelowner', 'mod', 'sub', 'all']
        if username == channel:
            return authority_levels
        else:
            return authority_levels[3]

    def check_blacklist(self, message, channel):
        """Check if part of a message is blacklisted"""
        if channel in blacklist:
            for phrase in blacklist[channel]:
                if phrase in message:
                    return blacklist[channel][phrase]
        return [-1, '']

    def timeout_user(self, channel, username, time, timeout_message):
        if timeout_message:
            self.send_message(timeout_message, channel)
        self.send_message(f"/timeout {username} {time}", channel)

        if config['debug']:
            print(f"Timed out user {username} for {time} seconds.")


if __name__ == "__main__":
    bot = TwitchBot()
    bot.connect(config['channels'])
    bot.run()
