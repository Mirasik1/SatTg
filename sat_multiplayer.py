import random
import time
from telebot import TeleBot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from sat_test_generator import generate_sat_test

class SATMultiplayerTest:
    def __init__(self, bot: TeleBot):
        self.bot = bot
        self.active_tests = {}  # {test_id: {questions, participants, current_question, scores, start_time}}
        self.user_tests = {}  # {user_id: test_id}

    def create_test(self, creator_id):
        test_id = random.randint(100000, 999999)
        questions = generate_sat_test()
        self.active_tests[test_id] = {
            'questions': questions,
            'participants': [creator_id],
            'current_question': 0,
            'scores': {creator_id: 0},
            'start_time': None
        }
        self.user_tests[creator_id] = test_id
        return test_id

    def join_test(self, user_id, test_id):
        if test_id in self.active_tests:
            self.active_tests[test_id]['participants'].append(user_id)
            self.active_tests[test_id]['scores'][user_id] = 0
            self.user_tests[user_id] = test_id
            return True
        return False

    def start_test(self, test_id):
        if test_id in self.active_tests:
            self.active_tests[test_id]['start_time'] = time.time()
            self.send_question(test_id)
            return True
        return False

    def send_question(self, test_id):
        test = self.active_tests[test_id]
        if test['current_question'] < len(test['questions']):
            question = test['questions'][test['current_question']]
            markup = InlineKeyboardMarkup()
            for key, value in question.answer_choices.items():
                markup.add(InlineKeyboardButton(text=f"{key}: {value}", callback_data=f"answer:{test_id}:{key}"))
            
            for user_id in test['participants']:
                self.bot.send_message(user_id, f"Вопрос {test['current_question'] + 1}:\n{question.text}", reply_markup=markup)
            
            # Устанавливаем таймер на 1 минуту для каждого вопроса
            self.bot.threaded(self.question_timeout, (test_id,))
        else:
            self.end_test(test_id)

    def question_timeout(self, test_id):
        time.sleep(60)  # 60 секунд на вопрос
        test = self.active_tests.get(test_id)
        if test and test['current_question'] < len(test['questions']):
            test['current_question'] += 1
            for user_id in test['participants']:
                self.bot.send_message(user_id, "Время на этот вопрос истекло!")
            self.send_question(test_id)

    def handle_answer(self, user_id, test_id, answer):
        test = self.active_tests.get(test_id)
        if test and test['current_question'] < len(test['questions']):
            question = test['questions'][test['current_question']]
            is_correct = question.check_answer(answer)
            
            # Рассчитываем очки на основе оставшегося времени и сложности вопроса
            elapsed_time = time.time() - test['start_time'] - (test['current_question'] * 60)
            time_factor = max(0, (60 - elapsed_time) / 60)
            difficulty_factor = 1  # Здесь можно добавить логику для определения сложности вопроса
            points = int(30 * time_factor * difficulty_factor) if is_correct else 0
            
            test['scores'][user_id] += points
            
            self.bot.send_message(user_id, f"{'Правильно!' if is_correct else 'Неправильно.'} Вы получили {points} очков.")
            
            # Переходим к следующему вопросу, если все ответили или время истекло
            if all(user in test['scores'] for user in test['participants']):
                test['current_question'] += 1
                self.send_question(test_id)

    def end_test(self, test_id):
        test = self.active_tests.get(test_id)
        if test:
            # Преобразуем очки в шкалу SAT (400-1600)
            max_possible_score = len(test['questions']) * 30
            for user_id, score in test['scores'].items():
                sat_score = int(400 + (score / max_possible_score) * 1200)
                test['scores'][user_id] = sat_score
                self.bot.send_message(user_id, f"Тест завершен! Ваш итоговый балл SAT: {sat_score}")
            
            # Отправляем общие результаты всем участникам
            results = "\n".join([f"Участник {user_id}: {score}" for user_id, score in test['scores'].items()])
            for user_id in test['participants']:
                self.bot.send_message(user_id, f"Результаты теста:\n{results}")
            
            # Очищаем данные теста
            for user_id in test['participants']:
                if user_id in self.user_tests:
                    del self.user_tests[user_id]
            del self.active_tests[test_id]