import random
from sat import Question
import sqlite3
from contextlib import closing


def count_questions_per_section(db_name="questions.db"):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                "SELECT question_type, COUNT(*) FROM questions GROUP BY question_type"
            )
            return dict(cursor.fetchall())


def get_random_questions_from_section(section, count, db_name="questions.db"):
    with sqlite3.connect(db_name) as conn:
        with closing(conn.cursor()) as cursor:
            cursor.execute(
                """
                SELECT * FROM questions 
                WHERE question_type = ? 
                ORDER BY RANDOM() 
                LIMIT ?
            """,
                (section, count),
            )
            rows = cursor.fetchall()
            questions = []
            for row in rows:
                answer_choices = row[4]
                if not answer_choices:
                    answer_choices = {}
                else:
                    try:
                        answer_choices = eval(answer_choices)
                    except SyntaxError:
                        print(f"Ошибка синтаксиса для вопроса с ID {row[1]}")
                        continue  # Пропускаем некорректную запись

                question = Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=answer_choices,
                    correct_answer=row[5],
                    rationale=row[6],
                )
                questions.append(question)
            return questions


def generate_sat_test(db_name="questions.db", total_questions=27):
    question_counts = count_questions_per_section(db_name)

    sat_sections = [
        ("Boundaries", 2, 4),
        ("Central Ideas and Details", 2, 3),
        ("Command of Evidence", 3, 5),
        ("Cross Text Connections", 2, 4),
        ("Form Structure and Sense", 2, 3),
        ("Inference", 3, 5),
        ("Text Structure and Purpose", 2, 4),
        ("Transitions", 2, 4),
        ("Words in Context", 2, 4)
    ]

    test_questions = []
    remaining_questions = total_questions

    for i, (section, min_count, max_count) in enumerate(sat_sections):
        available_count = question_counts.get(section, 0)
        if available_count < min_count:
            print(f"Недостаточно вопросов в разделе {section}. Требуется минимум {min_count}, доступно {available_count}.")
            continue

        if i == len(sat_sections) - 1:  # Последний раздел
            count = min(remaining_questions, available_count, max_count)
        else:
            count = min(
                random.randint(min_count, max_count),
                available_count,
                remaining_questions,
            )

        section_questions = get_random_questions_from_section(section, count, db_name)
        test_questions.extend(section_questions)
        remaining_questions -= len(section_questions)

        if remaining_questions == 0:
            break

    random.shuffle(test_questions)
    return test_questions


if __name__ == "__main__":
    test = generate_sat_test()
    for question in test:
        print(question)

