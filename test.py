import sqlite3


def get_unique_answer_choices(db_name='questions.db'):
    unique_choices = set()
    with sqlite3.connect(db_name) as conn:
        cursor = conn.cursor()
        cursor.execute('''
        SELECT answer_choices FROM questions WHERE question_type = 'Transitions'
        ''')
        rows = cursor.fetchall()


    return rows


# Пример вызова функции
unique_answer_choices = get_unique_answer_choices()
print(unique_answer_choices)
