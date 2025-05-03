import logging
import json
import smtplib
from email.mime.text import MIMEText
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters, CallbackContext
import config

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

with open(config.ANIMALS_JSON, 'r', encoding='utf-8') as f:
    animals = json.load(f)
with open(config.QUESTIONS_JSON, 'r', encoding='utf-8') as f:
    questions = json.load(f)

def reset_user_data(user_data: dict):
    user_data.clear()
    user_data['scores'] = {animal: 0 for animal in animals}
    user_data['current_question'] = 0
    user_data['question_sent'] = False
    user_data['awaiting_feedback'] = False

def send_result_email(user_id: int, totem_animal: str):
    msg = MIMEText(f"Пользователь {user_id} получил тотемное животное: {animals[totem_animal]['name']}")
    msg['Subject'] = 'Результат викторины Московского зоопарка'
    msg['From'] = config.EMAIL_ADDRESS
    msg['To'] = config.ZOO_EMAIL
    try:
        with smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT) as server:
            server.login(config.EMAIL_ADDRESS, config.EMAIL_PASSWORD)
            server.sendmail(config.EMAIL_ADDRESS, config.ZOO_EMAIL, msg.as_string())
        logger.info(f"Email отправлен для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки email: {e}")

def start(update: Update, context: CallbackContext):
    reset_user_data(context.user_data)
    chat_id = update.effective_chat.id
    context.bot.send_message(
        chat_id=chat_id,
        text=(
            'Добро пожаловать в викторину "Твоё тотемное животное"! 🐾\n'
            'Отвечай на вопросы и узнай, какое животное из Московского зоопарка тебе подходит!'
        )
    )
    send_question(update, context)

def send_question(update: Update, context: CallbackContext):
    user_data = context.user_data
    if user_data.get('question_sent'):
        return

    q_idx = user_data['current_question']
    chat_id = update.effective_chat.id

    if q_idx < len(questions):
        q = questions[q_idx]
        keyboard = [
            [InlineKeyboardButton(opt['text'], callback_data=f"{q_idx}:{i}")]
            for i, opt in enumerate(q['options'])
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        context.bot.send_message(chat_id=chat_id, text=q['text'], reply_markup=reply_markup)
        user_data['question_sent'] = True
        logger.info(f"Отправлен вопрос {q_idx} пользователю {update.effective_user.id}")
    else:
        show_result(update, context)

def handle_answer(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    user_data = context.user_data

    try:
        q_idx_str, opt_idx_str = query.data.split(':')
        q_idx, opt_idx = int(q_idx_str), int(opt_idx_str)
        for animal in questions[q_idx]['options'][opt_idx]['animals']:
            user_data['scores'][animal] += 1

        user_data['current_question'] += 1
        user_data['question_sent'] = False

        logger.info(
            f"Пользователь {query.from_user.id} ответил на вопрос {q_idx}, "
            f"переход к {user_data['current_question']}"
        )
        send_question(update, context)

    except Exception as e:
        logger.error(f"Ошибка обработки ответа: {e}")
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Произошла ошибка. Пожалуйста, начните заново с /start.'
        )

def show_result(update: Update, context: CallbackContext):
    user_data = context.user_data
    scores = user_data['scores']
    max_score = max(scores.values())
    winners = [a for a, sc in scores.items() if sc == max_score]
    totem = winners[0]
    info = animals[totem]
    caption = (
        f"Твоё тотемное животное — {info['name']}!\n\n"
        f"{info['description']}\n\n"
        "Хочешь стать опекуном? Это поддержка животного, сертификат и пропуск в зоопарк!"
    )

    chat_id = update.effective_chat.id
    try:
        context.bot.send_photo(chat_id=chat_id, photo=info['photo'], caption=caption)
    except Exception as e:
        logger.error(f"Ошибка отправки фото: {e}")
        context.bot.send_message(chat_id=chat_id, text=caption)

    keyboard = [
        [InlineKeyboardButton('Узнать больше об опеке', callback_data='learn_more')],
        [InlineKeyboardButton('Поделиться результатом', callback_data=f'share:{totem}')],
        [InlineKeyboardButton('Связаться с зоопарком', callback_data='contact')],
        [InlineKeyboardButton('Попробовать ещё раз', callback_data='restart')],
        [InlineKeyboardButton('Оставить отзыв', callback_data='feedback')],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    context.bot.send_message(chat_id=chat_id, text='Что дальше? 😺', reply_markup=reply_markup)

    send_result_email(update.effective_user.id, totem)
    logger.info(f"Результат ({info['name']}) отправлен пользователю {update.effective_user.id}")

def handle_button(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    data = query.data

    if data == 'learn_more':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=(
                'Программа опеки позволяет стать опекуном животного, '
                'оплатив часть его содержания. Вы получите сертификат, '
                'пропуск в зоопарк и табличку у вольера! '
                f'Пишите: {config.ZOO_EMAIL}'
            )
        )
    elif data.startswith('share:'):
        totem = data.split(':', 1)[1]
        text = (
            f"Моё тотемное животное — {animals[totem]['name']}! "
            f"Узнай своё в Московском зоопарке: {config.BOT_USERNAME}"
        )
        context.bot.send_message(chat_id=update.effective_chat.id, text=text)
    elif data == 'contact':
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=f'📧 {config.ZOO_EMAIL}, 📞 +7 499 252 3580'
        )
    elif data == 'restart':
        reset_user_data(context.user_data)
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Викторина перезапущена! 🎉'
        )
        start(update, context)
    elif data == 'feedback':
        context.user_data['awaiting_feedback'] = True
        context.bot.send_message(chat_id=update.effective_chat.id, text='Оставьте ваш отзыв:')
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Неизвестная команда. Начните заново с /start.'
        )

def handle_text(update: Update, context: CallbackContext):
    user_data = context.user_data
    if user_data.get('awaiting_feedback'):
        feedback = update.message.text
        try:
            with open(config.FEEDBACK_FILE, 'a', encoding='utf-8') as f:
                f.write(f"User {update.effective_user.id}: {feedback}\n")
            context.bot.send_message(chat_id=update.effective_chat.id, text='Спасибо за отзыв! 😊')
        except Exception as e:
            logger.error(f"Ошибка сохранения отзыва: {e}")
            context.bot.send_message(chat_id=update.effective_chat.id, text='Не удалось сохранить отзыв.')
        user_data['awaiting_feedback'] = False
    else:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text='Пожалуйста, отвечайте через кнопки или введите /start для начала.'
        )

def main():
    updater = Updater(config.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler('start', start))
    dp.add_handler(CallbackQueryHandler(handle_answer, pattern=r'^\d+:\d+$'))
    dp.add_handler(CallbackQueryHandler(handle_button, pattern=r'^(learn_more|share:.*|contact|restart|feedback)$'))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()
