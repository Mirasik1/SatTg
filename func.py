import sqlite3
from contextlib import closing
from sat import Question
from openai import OpenAI
from api_key import OPENAI_API_KEY
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import matplotlib
matplotlib.use('Agg')


def is_user_registered(telegram_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT name, surname FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
            return user
def get_random_question(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
            row = cursor.fetchone()
            if row:
                return Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=eval(row[4]),  # Преобразуем строку обратно в словарь
                    correct_answer=row[5],
                    rationale=row[6]
                )
            return None
def create_user_database(db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            # Таблица пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                name TEXT,
                surname TEXT
            )
            ''')
            # Таблица секций
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS sections (
                section_id INTEGER PRIMARY KEY,
                section_name TEXT UNIQUE
            )
            ''')
            # Таблица статистики пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_stats (
                stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                section_id INTEGER,
                total_questions INTEGER,
                correct_answers INTEGER,
                incorrect_answers INTEGER,
                UNIQUE(user_id, section_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id),
                FOREIGN KEY(section_id) REFERENCES sections(section_id)
            )
            ''')
            conn.commit()

def add_user(telegram_id, name, surname, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, name, surname)
            VALUES (?, ?, ?)
            ''', (telegram_id, name, surname))
            conn.commit()

def update_user_stats(telegram_id, section_name, total_questions, correct_answers, incorrect_answers, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            # Получаем ID пользователя
            cursor.execute('SELECT user_id FROM users WHERE telegram_id = ?', (telegram_id,))
            user_id = cursor.fetchone()
            if user_id:
                user_id = user_id[0]
            else:
                return

            # Получаем ID секции
            cursor.execute('SELECT section_id FROM sections WHERE section_name = ?', (section_name,))
            section_id = cursor.fetchone()
            if section_id:
                section_id = section_id[0]
            else:
                add_section(section_name)
                cursor.execute('SELECT section_id FROM sections WHERE section_name = ?', (section_name,))
                section_id = cursor.fetchone()[0]

            # Обновляем статистику пользователя
            cursor.execute('''
            INSERT INTO user_stats (user_id, section_id, total_questions, correct_answers, incorrect_answers)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(user_id, section_id) DO UPDATE SET
            total_questions = total_questions + excluded.total_questions,
            correct_answers = correct_answers + excluded.correct_answers,
            incorrect_answers = incorrect_answers + excluded.incorrect_answers
            ''', (user_id, section_id, total_questions, correct_answers, incorrect_answers))
            conn.commit()


def add_section(section_name, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT OR IGNORE INTO sections (section_name)
            VALUES (?)
            ''', (section_name,))
            conn.commit()

def get_random_question(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions ORDER BY RANDOM() LIMIT 1')
            row = cursor.fetchone()
            if row:
                return Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=eval(row[4]),
                    correct_answer=row[5],
                    rationale=row[6]
                )
            return None

def get_user_stats(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT sections.section_name, total_questions, correct_answers, incorrect_answers
            FROM user_stats
            JOIN sections ON user_stats.section_id = sections.section_id
            WHERE user_stats.user_id = (SELECT user_id FROM users WHERE telegram_id = ?)
            ''', (user_id,))
            stats = cursor.fetchall()
            return stats
def get_question_by_id(question_id, db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions WHERE question_id = ?', (question_id,))
            row = cursor.fetchone()
            if row:
                return Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=eval(row[4]),  # Преобразуем строку обратно в словарь
                    correct_answer=row[5],
                    rationale=row[6]
                )
            return None


def get_chatgpt_explanation(question, user_answer,user_add_info):
    prompt = (
        f"{user_add_info}"
        f"Разбери каждый вариант ответа"
        f"Привет! Пожалуйста, просмотри данный вопрос, ответ пользователя, правильный ответ и все варианты ответов. "
        f"Объясни, почему ответ пользователя правильный или неправильный, и сравни все варианты ответов.\n\n"
        f"Вопрос:\n{question.text}\n\n"
        f"Ответ пользователя:\n{user_answer}\n"
        f"Правильный ответ:\n{question.correct_answer}\n\n"
        f"Варианты ответов:{question.answer_choices}\n"
    )




    client = OpenAI(api_key=OPENAI_API_KEY)

    completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system",
             "content": "Ты учитель по урокам САТ и ты мастерски знаешь каждый ответ"},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content


def generate_user_stats_pie_chart(stats, section):
    if not stats:
        return None

    # Отключение интерактивного режима Matplotlib
    plt.ioff()

    # Удаление подчеркиваний из section
    section = section.replace('_', ' ')

    df = pd.DataFrame(stats, columns=['Section', 'Total Questions', 'Correct Answers', 'Incorrect Answers'])

    fig, ax = plt.subplots(figsize=(4, 4))

    row = df.iloc[0]
    labels = ['Correct Answers', 'Incorrect Answers']
    sizes = [row['Correct Answers'], row['Incorrect Answers']]
    colors = ['#4CAF50', '#FF5722']
    explode = (0, 0)

    wedges, texts, autotexts = ax.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%',
                                      startangle=140, wedgeprops=dict(edgecolor='w'))

    for text in texts:
        text.set_color('black')
        text.set_fontsize(10)
    for autotext in autotexts:
        autotext.set_color('black')
        autotext.set_fontsize(10)

    ax.axis('equal')
    ax.set_title(section, color='black', fontsize=10)

    # Увеличение отступов для предотвращения обрезания текста
    plt.tight_layout()

    # Сохранение в буфер
    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    return buffer

def get_question_sections(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT DISTINCT question_type FROM questions')
            sections = cursor.fetchall()
            return [section[0] for section in sections]

def get_cleaned_question_sections(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT DISTINCT question_type FROM questions')
            sections = cursor.fetchall()
            cleaned_sections = [section[0].replace('_', ' ').replace('Results', '').strip() for section in sections]
            return cleaned_sections

def get_user_stats_by_section(user_id, section, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT section_name, total_questions, correct_answers, incorrect_answers
            FROM user_stats
            JOIN sections ON user_stats.section_id = sections.section_id
            WHERE user_stats.user_id = (SELECT user_id FROM users WHERE telegram_id = ?) AND sections.section_name = ?
            ''', (user_id, section))
            stats = list(cursor.fetchall())
            return stats
def get_random_question_by_section(section, db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions WHERE question_type = ? ORDER BY RANDOM() LIMIT 1', (section,))
            row = cursor.fetchone()
            if row:
                return Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=eval(row[4]),
                    correct_answer=row[5],
                    rationale=row[6]
                )
            return None
def get_rationale_by_question_id(question_id, db_name='questions.db'):
    # Retrieve the full question details including rationale
    question = get_question_by_id(question_id, db_name)
    if question:
        return question.rationale
    return None