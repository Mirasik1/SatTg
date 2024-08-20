from pdfminer.high_level import extract_text
import re
from sat import Question
import time
import os
import sqlite3
from contextlib import closing
import random


def create_database(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT,
                question_type TEXT,
                text TEXT,
                answer_choices TEXT,
                correct_answer TEXT,
                rationale TEXT,
                url TEXT
            )
            ''')
            conn.commit()


def shuffle_questions(db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            # Получаем все вопросы из базы данных
            cursor.execute('SELECT * FROM questions')
            questions = cursor.fetchall()

            # Перемешиваем вопросы
            random.shuffle(questions)

            # Создаем временную таблицу для хранения перемешанных вопросов
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS shuffled_questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                question_id TEXT,
                question_type TEXT,
                text TEXT,
                answer_choices TEXT,
                correct_answer TEXT,
                rationale TEXT,
                url TEXT
            )
            ''')

            # Вставляем перемешанные вопросы в новую таблицу
            cursor.executemany('''
            INSERT INTO shuffled_questions (
                question_id, question_type, text, answer_choices, correct_answer, rationale, url
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', [(q[1], q[2], q[3], q[4], q[5], q[6], q[7]) for q in questions])

            # Удаляем старую таблицу и переименовываем новую
            cursor.execute('DROP TABLE IF EXISTS questions')
            cursor.execute('ALTER TABLE shuffled_questions RENAME TO questions')

            conn.commit()

    return "Done"

def add_question_to_db(question, db_name='questions.db'):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute('''
            INSERT INTO questions (question_id, question_type, text, answer_choices, correct_answer, rationale, url)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (question.question_id, question.question_type, question.text, str(question.answer_choices),
                  question.correct_answer, question.rationale, question.url))
            conn.commit()


def parse_file_names():
    folder_path = 'documents/english'
    file_names = os.listdir(folder_path)
    pdf_files = [file for file in file_names if file.endswith('.pdf')]
    return pdf_files


def parse_pdf(path_to_file):
    pdf_text = extract_text("documents/english/" + path_to_file)

    id_re = re.compile(r'ID: ([a-zA-Z0-9]+)')
    text_re = re.compile(r'ID: [a-zA-Z0-9]+\n\n(.*?)(?=\nA\.)', re.DOTALL)
    answers_re = re.compile(r'\n([A-D])\. (.+?)(?=\n[A-D]\.|\n\n|\Z)', re.DOTALL)
    correct_answer_re = re.compile(r'Correct Answer: ([A-D])')



    ids = id_re.findall(pdf_text)
    texts = text_re.findall(pdf_text)
    answer_blocks = answers_re.findall(pdf_text)
    correct_answers = correct_answer_re.findall(pdf_text)
    rationale = re.findall(r'\b\w+\b', pdf_text)

    rationale_list = find_sections(rationale)
    filtered_ids = ids[::2]

    answers = []
    for i in range(0, len(answer_blocks), 4):
        block = answer_blocks[i:i + 4]
        if len(block) == 4:
            answers.append({key: value for key, value in block})
    question_type = path_to_file.split('/')[-1].split('.')[0]
    questions = []
    for i in range(len(filtered_ids)):
        if i < len(texts) and i < len(answers) and i < len(correct_answers) and i< len(rationale_list):
            question = Question(
                question_id=filtered_ids[i],
                text=texts[i],
                answer_choices=answers[i],
                correct_answer=correct_answers[i],
                rationale=rationale_list[i],
                question_type=question_type
            )

            questions.append(question)
    return questions


def find_sections(words):
    start_word = "Rationale"
    end_word = "Question"
    indexes = []

    i = 0
    while i < len(words):
        if words[i] == start_word:
            start_index = i
            while i < len(words) and words[i] != end_word:
                i += 1
            if i < len(words) and words[i] == end_word:
                end_index = i
                indexes.append((start_index, end_index))
        i += 1

    rationale = []
    for start_index, end_index in indexes:
        section = words[start_index:end_index]

        section_str = " ".join(section)

        rationale.append(section_str)


    return rationale

