from telegram.ext import Updater
from telegram.ext import ConversationHandler, CommandHandler, MessageHandler, Filters
import logging
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)

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
    PROXY_URL = open('.socks5', 'r').read()
    REQUEST_KWARGS.update({'proxy_url': PROXY_URL})

if not os.path.isdir('tracks'):
    os.mkdir('tracks')


TRACK, TITLE, PERFORMER, SEND_TRACK = range(4)


def log_user(user, text):
    logger.info("User {} {}".format(user.username, text))


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "{}" caused error "{}"'.format(update, context.error))
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
    logging.info('Started downloading track{}.mp3 from {}'.format(track.file_unique_id, user))
    file.download('tracks/track{}.mp3'.format(track.file_unique_id))
    logging.info('Finished downloading track{}.mp3 from {}'.format(track.file_unique_id, user))
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

    logging.info('Started sending track{}.mp3 to {}'.format(track_id, user))
    update.message.reply_audio(audio=open('tracks/track{}.mp3'.format(track_id), 'rb'), performer=performer,
                               title=title)
    logging.info('Finished sending track{}.mp3 to {}'.format(track_id, user))
    os.remove('tracks/track{}.mp3'.format(track_id))
    context.user_data.clear()
    return ConversationHandler.END


def cancel(update, context):
    log_user(update.message.from_user, 'cancelled the conversation')
    update.message.reply_text('Operation was cancelled')

    if context.user_data.get('track_unique_id'):
        track_id = context.user_data['track_unique_id']
        os.remove('tracks/track{}.mp3'.format(track_id))
    context.user_data.clear()

    return ConversationHandler.END


def main():
    updater = Updater(token=TOKEN, request_kwargs=REQUEST_KWARGS, use_context=True)

    # Get the dispatcher to register handlers
    dispatcher = updater.dispatcher

    # Add conversation handler with the states GENDER, PHOTO, LOCATION and BIO
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

    # log all errors
    dispatcher.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
