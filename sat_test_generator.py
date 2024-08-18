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
            return [
                Question(
                    question_id=row[1],
                    question_type=row[2],
                    text=row[3],
                    answer_choices=eval(row[4]),
                    correct_answer=row[5],
                    rationale=row[6],
                )
                for row in rows
            ]


def generate_sat_test(db_name="questions.db", total_questions=27):
    question_counts = count_questions_per_section(db_name)

    sat_sections = [
        ("Words_in_Context", 2, 4),
        ("Text_Structure", 2, 3),
        ("Quantitative_Reasoning", 3, 5),
        ("Inference", 2, 4),
        ("Synthesis", 2, 3),
        ("Command_of_Evidence", 3, 5),
        ("Words_in_Context_Results", 2, 4),
    ]

    test_questions = []
    remaining_questions = total_questions

    for i, (section, min_count, max_count) in enumerate(sat_sections):
        available_count = question_counts.get(section, 0)
        if i == len(sat_sections) - 1:  # Last section
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
    print(f"Generated test with {len(test)} questions:")
    for i, question in enumerate(test, 1):
        print(f"{i}. {question.question_type}: {question.question_id}")
