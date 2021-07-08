import os
import shutil
import telebot
import requests
import asyncio
from shazamio import Shazam, serialize_track

TEMP_FOLDER = ".temp"

with open("TOKEN") as token_file:
    TOKEN = token_file.read().strip()  # read token string from plaintext file named TOKEN

bot = telebot.TeleBot(TOKEN, parse_mode=None)


def download_file_and_return_path(cache_id, file_id):
    file_info = bot.get_file(file_id)
    filename = file_info.file_path.split("/")[-1]  # get filename from filepath
    resp = requests.get('https://api.telegram.org/file/bot{0}/{1}'.format(TOKEN, file_info.file_path))
    folder = os.path.join(TEMP_FOLDER, str(cache_id))  # get temp folder name for specific audio sample
    os.mkdir(folder)  # create such folder
    filepath = os.path.join(folder, filename)
    with open(filepath, "wb") as f:
        f.write(resp.content)  # write downloaded sample file to temp folder
    return filepath


def download_cover_and_return_path(cache_id, url):
    name = url.split("/")[-1]  # get cover's filename from the last part of URL
    resp = requests.get(url)
    folder = os.path.join(TEMP_FOLDER, str(cache_id))  # get temp folder name for track's covers
    filepath = os.path.join(folder, name)
    with open(filepath, "wb") as f:
        f.write(resp.content)  # write downloaded track cover to sample's temp folder
    return filepath


async def recognize(path):
    shazam = Shazam()
    out = await shazam.recognize_song(path)
    return out


@bot.message_handler(commands=["start"])
def welcome(message):
    bot.send_message(message.chat.id, "Send audio or voice message to start using the bot")


@bot.message_handler(content_types=["audio", "voice"])
def handle_audio(message):
    type_is_voice = message.content_type == "voice"
    file_id = message.voice.file_id if type_is_voice else message.audio.file_id
    duration = message.voice.duration if type_is_voice else message.audio.duration
    file_local_path = download_file_and_return_path(message.id, file_id)
    data = loop.run_until_complete(recognize(file_local_path))

    if duration > 15:
        bot.reply_to(message, "Please try sending a shorter sample")
    elif not data["matches"]:
        bot.reply_to(message, "Sorry, couldn't recognize any song. Try sending a longer sample")
    else:
        track = serialize_track(data['track'])
        caption = f"{track.subtitle} - {track.title}"
        # photo_url = track.photo_url
        photo_url = data['track']['images']['coverarthq']
        if photo_url:
            cover_path = download_cover_and_return_path(message.id, photo_url)
            cover = open(cover_path, "rb")
            bot.send_photo(message.chat.id, cover, caption=caption, reply_to_message_id=message.id)
            cover.close()
        else:
            bot.reply_to(message, caption)
    shutil.rmtree(os.path.join(TEMP_FOLDER, str(message.id)))


loop = asyncio.get_event_loop()
bot.polling()
