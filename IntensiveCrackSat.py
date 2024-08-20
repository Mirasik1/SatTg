import questions_parser
from api_key import TELEGRAM_BOT_KEY
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import telebot
from telebot import types, custom_filters
import func



func.create_user_database()

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TELEGRAM_BOT_KEY, state_storage=state_storage)

class Allstates(StatesGroup):
    register_name = State()
    register_surname = State()
    testing = State()


@bot.message_handler(state=Allstates.testing)
def send_next_question(message,user_id=None):
    if user_id is None:
        id = message.from_user.id
    else:
        id = user_id
    try:
        current_question_id = func.get_current_question_id(id)
        print(id)
        print(f"current_question_id: {current_question_id}")

        if current_question_id is None:
            current_question_id = 1

        question = func.get_question_by_id(current_question_id)


        if question:
            question_text = (
                f"ID: {current_question_id}/917\n"
                f"Question ID: {question.question_id}\n"
                f"Question Type: {question.question_type}\n"
                f"Text:\n{question.text}\n\n"
                "Answer Choices:\n"
            )

            for key, value in question.answer_choices.items():
                question_text += f"{key}: {value}\n"

            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [types.InlineKeyboardButton(text=key, callback_data=f"{question.question_id}:{key}") for key in
                       question.answer_choices.keys()]
            markup.add(*buttons)

            bot.send_message(message.chat.id, question_text, reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Вопросы закончились! Вы ответили на все вопросы.")
    except Exception as e:
        print(f"Error in send_next_question: {e}")
        bot.send_message(message.chat.id, "Произошла ошибка при получении вопроса.")



@bot.message_handler(state=Allstates.register_name)
def register_name(message):
    name = message.text
    bot.send_message(message.chat.id, "Теперь введите вашу фамилию.")
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        data['name'] = name
    bot.set_state(message.from_user.id, Allstates.register_surname, message.chat.id)

@bot.message_handler(state=Allstates.register_surname)
def register_surname(message):
    surname = message.text
    telegram_id = message.from_user.id
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        name = data['name']
        func.add_user(telegram_id, name, surname)
    bot.send_message(message.chat.id, "Вы успешно зарегистрированы!")

    bot.send_message(message.chat.id, "Нажмите '/start' для начала.")
    bot.set_state(message.from_user.id, Allstates.testing, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('discuss') or call.data.startswith('skip'))
def handle_discussion_or_skip(call):
    if call.data.startswith('skip'):
        bot.delete_message(call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "Давайте перейдем на следующий вопрос, нажмите /question")
    elif call.data.startswith('discuss'):
        question_id = call.data.split(":")[1]
        user_answer = call.data.split(":")[2]

        # Retrieve question including rationale
        question = func.get_question_by_question_id(question_id)
        print(question)
        if question:
            rationale = question.rationale
            if rationale:
                bot.send_message(call.message.chat.id, f"Разбор вопроса:\n{rationale}")
            else:
                bot.send_message(call.message.chat.id, "Рассуждение по этому вопросу отсутствует.")
        else:
            bot.send_message(call.message.chat.id, "Вопрос не найден.")

        bot.set_state(call.from_user.id, Allstates.testing, call.message.chat.id)

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    # Разделение данных
    question_id = call.data.split(":")[0]
    user_answer = call.data.split(":")[1]
    question = func.get_question_by_question_id(question_id)

    if question:
        # Проверка правильности ответа
        is_correct = question.check_answer(user_answer)
        response = f"{'Правильный' if is_correct else 'Неправильный'} ответ.\n\n{call.message.text}"

        # Добавление информации о правильности ответа
        if is_correct:
            response += f"\n\n✅ {user_answer}: {question.answer_choices[user_answer]}"
            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [
                types.InlineKeyboardButton(text=f"{key} ✅" if key == user_answer else key, callback_data="disabled")
                for key in question.answer_choices.keys()]
            markup.add(*buttons)
        else:
            response += f"\n\n❌ {user_answer}: {question.answer_choices[user_answer]}"
            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [
                types.InlineKeyboardButton(text=f"{key} ❌" if key == user_answer else key, callback_data="disabled")
                for key in question.answer_choices.keys()]
            markup.add(*buttons)

        # Редактирование сообщения с результатом
        bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=markup)

        # Обновление статистики пользователя
        correct = 1 if is_correct else 0
        incorrect = 1 if not is_correct else 0
        func.update_user_stats(call.from_user.id, question.question_type, 1, correct, incorrect)

        # Обновление текущего номера вопроса
        current_question_id = func.get_current_question_id(call.from_user.id)
        if current_question_id is None:
            current_question_id = 1
        else:
            current_question_id += 1

        func.update_current_question_id(call.from_user.id, current_question_id)

        # Отправка правильного ответа и предложений по дальнейшим действиям
        discussion_markup = types.InlineKeyboardMarkup(row_width=2)
        discuss_button = types.InlineKeyboardButton(text="Разобрать", callback_data=f"discuss:{question.question_id}:{user_answer}")
        skip_button = types.InlineKeyboardButton(text="Пропустить", callback_data="skip")
        discussion_markup.add(discuss_button, skip_button)

        bot.send_message(call.message.chat.id,
                         f"Правильный ответ: {question.correct_answer}\n\n✅ {question.correct_answer}: {question.answer_choices[question.correct_answer]}\n"
                         f"Выберите действие:",
                         reply_markup=discussion_markup)

        # Предложение следующего вопроса
        send_next_question(call.message,call.from_user.id)
    else:
        bot.send_message(call.message.chat.id, "Вопрос не найден.")


@bot.message_handler(commands=['start'])
def handle_start(message):
    user = func.is_user_registered(message.from_user.id)
    if user:
        name, surname = user
        bot.send_message(message.chat.id,
                         f"Щас начнется ебля {name} {surname}")

        bot.send_message(message.chat.id, "Ох ебля пошла.")
        bot.set_state(message.from_user.id, Allstates.testing, message.chat.id)
        send_next_question(message)

    else:
        bot.send_message(message.chat.id,
                         "Добро пожаловать! Пожалуйста, зарегистрируйтесь, для начала введите ваше имя.")
        bot.set_state(message.from_user.id, Allstates.register_name, message.chat.id)



bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)