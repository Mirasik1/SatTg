import sqlite3
from contextlib import closing
from sat import Question

from api_key import OPENAI_API_KEY
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import matplotlib
matplotlib.use('Agg')
def create_user_database(db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            # Таблица пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                telegram_id INTEGER UNIQUE,
                name TEXT
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
            # Новая таблица для мультиплеерных тестов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS multiplayer_tests (
                test_id INTEGER PRIMARY KEY,
                creator_id INTEGER,
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                FOREIGN KEY(creator_id) REFERENCES users(user_id)
            )
            ''')
            # Новая таблица для результатов мультиплеерных тестов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS multiplayer_results (
                result_id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER,
                user_id INTEGER,
                score INTEGER,
                FOREIGN KEY(test_id) REFERENCES multiplayer_tests(test_id),
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            # Новая таблица для отслеживания прогресса пользователей
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                current_question_id INTEGER DEFAULT 1,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            conn.commit()

def is_user_registered(telegram_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT name FROM users WHERE telegram_id = ?', (telegram_id,))
            user = cursor.fetchone()
            return user

def clear_user_stats(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            # Удаление статистики пользователя из таблицы user_stats
            cursor.execute('''
                DELETE FROM user_stats
                WHERE user_id = ?
            ''', (user_id,))



            # Удаление записей мультиплеерных тестов, созданных пользователем
            cursor.execute('''
                DELETE FROM multiplayer_tests
                WHERE creator_id = ?
            ''', (user_id,))

            # Удаление результатов мультиплеерных тестов пользователя
            cursor.execute('''
                DELETE FROM multiplayer_results
                WHERE user_id = ?
            ''', (user_id,))

            # Удаление прогресса пользователя из таблицы user_progress
            cursor.execute('''
                DELETE FROM user_progress
                WHERE user_id = ?
            ''', (user_id,))

            conn.commit()
def add_user(telegram_id, name , db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT OR IGNORE INTO users (telegram_id, name )
            VALUES (?, ?)
            ''', (telegram_id, name))
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

def get_question_by_question_id(question_id, db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions WHERE question_id = ?', (question_id,))
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

def get_question_by_id(id, db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('SELECT * FROM questions WHERE id = ?', (id,))
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

def get_chatgpt_explanation(question, user_answer, user_add_info):
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
            {"role": "system", "content": "Ты учитель по урокам САТ и ты мастерски знаешь каждый ответ"},
            {"role": "user", "content": prompt}
        ]
    )

    return completion.choices[0].message.content

def generate_user_stats_pie_chart(stats, section):
    if not stats:
        return None

    plt.ioff()

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

    plt.tight_layout()

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
    question = get_question_by_question_id(question_id, db_name)
    if question:
        return question.rationale
    return None

# Новые функции для поддержки мультиплеерного режима

def create_multiplayer_test(creator_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT INTO multiplayer_tests (creator_id, start_time)
            VALUES (?, CURRENT_TIMESTAMP)
            ''', (creator_id,))
            conn.commit()
            return cursor.lastrowid

def end_multiplayer_test(test_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            UPDATE multiplayer_tests
            SET end_time = CURRENT_TIMESTAMP
            WHERE test_id = ?
            ''', (test_id,))
            conn.commit()

def add_multiplayer_result(test_id, user_id, score, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT INTO multiplayer_results (test_id, user_id, score)
            VALUES (?, ?, ?)
            ''', (test_id, user_id, score))
            conn.commit()

def get_multiplayer_results(test_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT users.name, users.surname, multiplayer_results.score
            FROM multiplayer_results
            JOIN users ON multiplayer_results.user_id = users.user_id
            WHERE multiplayer_results.test_id = ?
            ORDER BY multiplayer_results.score DESC
            ''', (test_id,))
            return cursor.fetchall()

def get_user_multiplayer_history(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT multiplayer_tests.test_id, multiplayer_tests.start_time, multiplayer_results.score
            FROM multiplayer_results
            JOIN multiplayer_tests ON multiplayer_results.test_id = multiplayer_tests.test_id
            WHERE multiplayer_results.user_id = ?
            ORDER BY multiplayer_tests.start_time DESC
            ''', (user_id,))
            return cursor.fetchall()

# ... (предыдущий код остается без изменений)

def generate_multiplayer_leaderboard(test_id, db_name='users.db'):
    results = get_multiplayer_results(test_id)
    
    if not results:
        return None

    plt.ioff()

    df = pd.DataFrame(results, columns=['Name', 'Surname', 'Score'])
    df['Full Name'] = df['Name'] + ' ' + df['Surname']

    fig, ax = plt.subplots(figsize=(10, 6))

    bars = ax.barh(df['Full Name'], df['Score'])
    ax.set_xlabel('Score')
    ax.set_ylabel('Participants')
    ax.set_title('Multiplayer Test Leaderboard')

    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2, f'{width}', 
                ha='left', va='center')

    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    return buffer

def get_active_multiplayer_tests(db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT test_id, creator_id, start_time
            FROM multiplayer_tests
            WHERE end_time IS NULL
            ORDER BY start_time DESC
            ''')
            return cursor.fetchall()

def get_multiplayer_test_details(test_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT multiplayer_tests.test_id, users.name, users.surname, 
                   multiplayer_tests.start_time, multiplayer_tests.end_time,
                   COUNT(multiplayer_results.user_id) as participant_count
            FROM multiplayer_tests
            JOIN users ON multiplayer_tests.creator_id = users.user_id
            LEFT JOIN multiplayer_results ON multiplayer_tests.test_id = multiplayer_results.test_id
            WHERE multiplayer_tests.test_id = ?
            GROUP BY multiplayer_tests.test_id
            ''', (test_id,))
            return cursor.fetchone()

def add_user_to_multiplayer_test(test_id, user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT OR IGNORE INTO multiplayer_results (test_id, user_id, score)
            VALUES (?, ?, 0)
            ''', (test_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

def update_multiplayer_score(test_id, user_id, score, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            UPDATE multiplayer_results
            SET score = score + ?
            WHERE test_id = ? AND user_id = ?
            ''', (score, test_id, user_id))
            conn.commit()
            return cursor.rowcount > 0

def get_user_current_multiplayer_test(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT multiplayer_tests.test_id
            FROM multiplayer_tests
            JOIN multiplayer_results ON multiplayer_tests.test_id = multiplayer_results.test_id
            WHERE multiplayer_results.user_id = ? AND multiplayer_tests.end_time IS NULL
            ORDER BY multiplayer_tests.start_time DESC
            LIMIT 1
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

def generate_user_multiplayer_history_chart(user_id, db_name='users.db'):
    history = get_user_multiplayer_history(user_id)
    
    if not history:
        return None

    plt.ioff()

    df = pd.DataFrame(history, columns=['Test ID', 'Date', 'Score'])
    df['Date'] = pd.to_datetime(df['Date'])

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(df['Date'], df['Score'], marker='o')
    ax.set_xlabel('Date')
    ax.set_ylabel('Score')
    ax.set_title('User Multiplayer Test History')

    plt.xticks(rotation=45)
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    buffer.seek(0)
    plt.close()

    return buffer
def initialize_user_progress(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT OR IGNORE INTO user_progress (user_id, current_question_id)
            VALUES (?, 1)
            ''', (user_id,))
            conn.commit()


def update_current_question_id(user_id, question_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT INTO user_progress (user_id, current_question_id)
            VALUES (?, ?)
            ON CONFLICT(user_id) DO UPDATE SET
                current_question_id = excluded.current_question_id
            ''', (user_id, question_id))
            conn.commit()

def get_current_question_id(user_id, db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            SELECT current_question_id FROM user_progress
            WHERE user_id = ?
            ''', (user_id,))
            result = cursor.fetchone()
            return result[0] if result else None

def create_user_progress_table(db_name='users.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                user_id INTEGER PRIMARY KEY,
                current_question_id INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            )
            ''')
            conn.commit()
def generate_pie_chart(stats):
    correct_answers = sum([correct for _, _, correct, _ in stats])
    incorrect_answers = sum([incorrect for _, _, _, incorrect in stats])

    labels = 'Correct', 'Incorrect'
    sizes = [correct_answers, incorrect_answers]
    colors = ['#4CAF50', '#FF5733']
    explode = (0.1, 0)  # немного отделить первый сегмент

    plt.figure(figsize=(6, 6))
    plt.pie(sizes, explode=explode, labels=labels, colors=colors, autopct='%1.1f%%', shadow=True, startangle=140)
    plt.axis('equal')  # Сохранить соотношение сторон, чтобы круговая диаграмма была кругом

    # Сохранение диаграммы в буфер
    buffer = BytesIO()
    plt.savefig(buffer, format='png')
    plt.close()
    buffer.seek(0)
    return buffer