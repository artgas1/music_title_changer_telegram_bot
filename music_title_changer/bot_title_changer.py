from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
from telegram.ext import Updater
import logging
import os

logging.basicConfig(filename='log.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

TRACK, TITLE, PERFORMER, SEND_TRACK = range(4)


def log_user(user, text):
    logger.info(f"User {user.username} {text}")


def log_error(update, text):
    logger.error(f'Update "{update}" caused error "{text}"')


def error_handler(update, context):
    log_error(update, context.error)
    for dev_id in DEVS:
        context.bot.send_message(dev_id, context.error)


def start(update, context):
    log_user(update.message.from_user, 'started conversation')
    update.message.reply_text('Send me track')
    return TRACK


def download_track(update, context):
    user = update.message.from_user.username

    track = update.message.audio
    file = track.get_file()
    context.user_data['track_unique_id'] = track.file_unique_id
    logger.info(f'Started downloading track{track.file_unique_id}.mp3 from {user}')
    file.download(f'tracks/track{track.file_unique_id}.mp3')
    logger.info(f'Finished downloading track{track.file_unique_id}.mp3 from {user}')
    update.message.reply_text('Send me title of track')
    return TITLE


def get_title(update, context):
    title = update.message.text
    context.user_data['title'] = title
    update.message.reply_text('Send me performer of track')

    log_user(update.message.from_user, 'sent title of track')
    return PERFORMER


def get_performer(update, context):
    user = update.message.from_user.username

    performer = update.message.text
    title = context.user_data['title']
    track_id = context.user_data['track_unique_id']
    log_user(update.message.from_user, 'sent performer of track')

    logger.info(f'Started sending track{track_id}.mp3 to {user}')
    update.message.reply_audio(audio=open(f'tracks/track{track_id}.mp3', 'rb'), performer=performer,
                               title=title)
    logger.info(f'Finished sending track{track_id}.mp3 to {user}')
    os.remove(f'tracks/track{track_id}.mp3')
    context.user_data.clear()
    return ConversationHandler.END


def cancel(update, context):
    log_user(update.message.from_user, 'cancelled the conversation')
    update.message.reply_text('Operation was cancelled')

    if context.user_data.get('track_unique_id'):
        track_id = context.user_data['track_unique_id']
        os.remove(f'tracks/track{track_id}.mp3')
    context.user_data.clear()

    return ConversationHandler.END


def main():
    updater = Updater(token=TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)
    dispatcher = updater.dispatcher

    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TRACK: [MessageHandler(Filters.audio, download_track)],
            TITLE: [MessageHandler(Filters.text & (~Filters.command('cancel')), get_title)],
            PERFORMER: [MessageHandler(Filters.text & (~Filters.command('cancel')), get_performer)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    dispatcher.add_handler(conversation_handler)
    dispatcher.add_error_handler(error_handler)

    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    if not os.path.isfile('.token') or os.stat('.token').st_size == 0:
        print('Add bot token in .token file')
        raise SystemExit
    if not os.path.isfile('.devs') or os.stat('.devs').st_size == 0:
        print('Add developers ids splitted by whitespace in .devs file')
        raise SystemExit

    TOKEN = open('.token', 'r').read().split()[0]
    DEVS = open('.devs', 'r').read().split()

    # proxy format: socks5://95.110.194.245:54871
    REQUEST_KWARGS = {}

    if os.path.isfile('.socks5') and os.stat('.socks5').st_size != 0:
        PROXY_URL = open('.socks5', 'r').read().replace('\n', '')
        REQUEST_KWARGS = {'proxy_url': PROXY_URL}

    if not os.path.isdir('tracks'):
        os.mkdir('tracks')

    main()
