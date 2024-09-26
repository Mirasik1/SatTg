from api_key import TELEGRAM_BOT_KEY
from telebot.handler_backends import State, StatesGroup
from telebot.storage import StateMemoryStorage
import telebot
from telebot import types, custom_filters
import func

func.create_user_database()

DEFAULT_SECTION = 'Math'  # Секция по умолчанию

state_storage = StateMemoryStorage()
bot = telebot.TeleBot(TELEGRAM_BOT_KEY, state_storage=state_storage)

class Allstates(StatesGroup):
    register_name = State()
    register_surname = State()
    results = State()
    testing = State()
    analyzing = State()
    choose_section = State()

@bot.message_handler(commands=['start'])
def handle_start(message):
    user = func.is_user_registered(message.from_user.id)
    if user:
        name, surname = user
        bot.send_message(message.chat.id,
                         f"Добро пожаловать обратно, {surname} {name}! Для получения вопроса введите команду /question.\n"
                         f"Секция по умолчанию: {DEFAULT_SECTION}. Вы можете сменить секцию командой /section.")
        bot.set_state(message.from_user.id, Allstates.testing, message.chat.id)
    else:
        bot.send_message(message.chat.id,
                         "Добро пожаловать! Пожалуйста, зарегистрируйтесь, для начала введите ваше имя.")
        bot.set_state(message.from_user.id, Allstates.register_name, message.chat.id)

@bot.message_handler(state=Allstates.register_name)
def register_name(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:

        name = message.text
        telegram_id = message.from_user.id
        func.add_user(telegram_id, name )
    bot.send_message(message.chat.id,
                     "Вы успешно зарегистрированы! Для получения вопроса введите команду /question.\n"
                     f"Секция по умолчанию: {DEFAULT_SECTION}. Вы можете сменить секцию командой /section.")
    bot.set_state(message.from_user.id, Allstates.testing, message.chat.id)



@bot.message_handler(commands=['section'])
def choose_section(message):
    sections = func.get_question_sections()
    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [types.InlineKeyboardButton(text=section, callback_data=f"section:{section}") for section in sections]
    markup.add(*buttons)
    bot.send_message(message.chat.id, "Пожалуйста, выберите секцию:", reply_markup=markup)
    bot.set_state(message.from_user.id, Allstates.choose_section, message.chat.id)


@bot.callback_query_handler(func=lambda call: call.data.startswith('section:'), state=Allstates.choose_section)
def handle_section_choice(call):
    section = call.data.split(":")[1]
    with bot.retrieve_data(call.from_user.id, call.message.chat.id) as data:
        data['chosen_section'] = section
    bot.send_message(call.message.chat.id, f"Вы выбрали секцию: {section}. Для получения вопроса введите команду /question.")
    bot.set_state(call.from_user.id, Allstates.testing, call.message.chat.id)


@bot.message_handler(commands=['question'], state=Allstates.testing)
def send_random_question(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        section = data.get('chosen_section', DEFAULT_SECTION)
        question = func.get_random_question_by_section(section)
        if question:
            # Форматирование текста вопроса и ответов
            question_text = (
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
            bot.send_message(message.chat.id, "В базе данных нет вопросов для выбранной секции.")


@bot.message_handler(commands=['question_random'], state=Allstates.testing)
def send_any_random_question(message):
    question = func.get_random_question()
    if question:
        # Форматирование текста вопроса и ответов
        question_text = (
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
        bot.send_message(message.chat.id, "В базе данных нет вопросов.")

# Остальной код бота

@bot.callback_query_handler(func=lambda call: call.data.startswith('stats:'))
def handle_stats_choice(call):
    section = call.data.split(":")[1]
    stats = func.get_user_stats_by_section(call.from_user.id, section)

    if stats:
        send_stats_pie_chart(call.message, stats, section)
    else:
        bot.send_message(call.message.chat.id, "Статистика не найдена.")


def send_stats_pie_chart(message, stats, section):
    buffer = func.generate_user_stats_pie_chart(stats, section)
    section_ = section.replace('_', ' ')
    response = "Ваша статистика:"
    for section, total, correct, incorrect in stats:
        response += f"\nСекция: {section_}\nВсего вопросов: {total}\nПравильных ответов: {correct}\nНеправильных ответов: {incorrect}\n"
    if buffer:
        buffer.seek(0)
        bot.send_photo(message.chat.id, photo=buffer, caption=response)
    else:
        bot.send_message(message.chat.id, "Ошибка при создании графика статистики.")


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
        if question:
            rationale = question.rationale
            if rationale:
                bot.send_message(call.message.chat.id, f"Разбор вопроса:\n{rationale}")
            else:
                bot.send_message(call.message.chat.id, "Рассуждение по этому вопросу отсутствует.")
        else:
            bot.send_message(call.message.chat.id, "Вопрос не найден.")

        bot.set_state(call.from_user.id, Allstates.analyzing, call.message.chat.id)


@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    question_id = call.data.split(":")[0]
    user_answer = call.data.split(":")[1]
    question = func.get_question_by_question_id(question_id)

    if question:
        if question.check_answer(user_answer):
            response = f"Правильный ответ!\n\n{call.message.text}"
            response += f"\n\n✅ {user_answer}: {question.answer_choices[user_answer]}"
            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [
                types.InlineKeyboardButton(text=f"{key} ✅" if key == user_answer else key, callback_data="disabled") for
                key in question.answer_choices.keys()
            ]
            markup.add(*buttons)
            bot.edit_message_text(response, call.message.chat.id, call.message.message_id, reply_markup=markup)
        else:
            response = f"Неправильный ответ.\n\n{call.message.text}"
            response += f"\n\n❌ {user_answer}: {question.answer_choices[user_answer]}"
            markup = types.InlineKeyboardMarkup(row_width=4)
            buttons = [
                types.InlineKeyboardButton(text=f"{key} ❌" if key == user_answer else key, callback_data="disabled") for
                key in question.answer_choices.keys()
            ]
            markup.add(*buttons)
            bot.edit_message_text(call.message.text, call.message.chat.id, call.message.message_id, reply_markup=markup)

        discussion_markup = types.InlineKeyboardMarkup(row_width=2)
        discuss_button = types.InlineKeyboardButton(text="Разобрать", callback_data=f"discuss:{question.question_id}:{user_answer}")
        skip_button = types.InlineKeyboardButton(text="Пропустить", callback_data="skip")
        discussion_markup.add(discuss_button, skip_button)

        bot.send_message(call.message.chat.id,
                         f"Правильный ответ: {question.correct_answer}\n\n✅ {question.correct_answer}: {question.answer_choices[question.correct_answer]}\n"
                         f"Выберите действие:",
                         reply_markup=discussion_markup
                         )
        correct = 1 if question.check_answer(user_answer) else 0
        incorrect = 1 if not question.check_answer(user_answer) else 0
        func.update_user_stats(call.from_user.id, question.question_type, 1, correct, incorrect)


@bot.message_handler(commands=['stats'])
def send_user_stats(message):
    sections = func.get_question_sections()
    text_section = func.get_cleaned_question_sections()
    markup = types.InlineKeyboardMarkup(row_width=2)

    buttons = [types.InlineKeyboardButton(text=text_section[i], callback_data=f"stats:{sections[i]}") for i in
               range(len(sections))]
    markup.add(*buttons)

    bot.send_message(message.chat.id, "Выберите тип секции:", reply_markup=markup)


@bot.message_handler(state=Allstates.analyzing)
def analyze_answer(message):
    with bot.retrieve_data(message.from_user.id, message.chat.id) as data:
        question_id = data['question_id']
        user_answer = data['user_answer']

        question = func.get_question_by_question_id(question_id)

        if question:
            explanation = func.get_rationale_by_question_id(question_id)
            bot.send_message(message.chat.id, explanation)
            bot.send_message(message.chat.id, "Давайте перейдем на следующий вопрос, нажмите /question")
        else:
            bot.send_message(message.chat.id, "Вопрос не найден.")
            bot.send_message(message.chat.id, "Давайте перейдем на следующий вопрос, нажмите /question")

    bot.set_state(message.from_user.id, Allstates.testing, message.chat.id)

@bot.message_handler(commands=['all_stats'])
def send_stats(message):
    stats = func.get_user_stats(message.from_user.id)
    if stats:
        response = "Ваша статистика:\n"
        for section, total, correct, incorrect in stats:
            response += (
                f"\nСекция: {section}\n"
                f"Всего вопросов: {total}\n"
                f"Правильных ответов: {correct}\n"
                f"Неправильных ответов: {incorrect}\n"
            )
        bot.send_message(message.chat.id, response)
    else:
        bot.send_message(message.chat.id, "Статистика не найдена.")



@bot.message_handler(commands=['help'])
def send_help(message):
    help_text = (
        "Добро пожаловать в бот подготовки к SAT! Вот список доступных команд:\n\n"
        "/start - Начало работы с ботом. Регистрация пользователя.\n"
        "/section - Выбор секции для вопросов.\n"
        "/question - Получить случайный вопрос для тренировки по выбранной секции.\n"
        "/question_random - Получить случайный вопрос для тренировки без учета секции.\n"
        "/stats - Показать статистику по категориям вопросов.\n"
        "/all_stats - Показать общую статистику пользователя.\n"
        "/help - Показать это сообщение.\n\n"
        "Выберите нужную команду и следуйте инструкциям. Если у вас возникли вопросы, не стесняйтесь обращаться за помощью!"
    )
    bot.send_message(message.chat.id, help_text)

bot.add_custom_filter(custom_filters.StateFilter(bot))
bot.infinity_polling(skip_pending=True)
