import questions_parser
import time

start_time = time.time()
questions_parser.create_database()
all=[]
file_names = questions_parser.parse_file_names()
print(file_names)


for file_name in file_names:
    questions = questions_parser.parse_pdf(file_name)
    all.extend(questions)
    for question in questions:
        questions_parser.add_question_to_db(question)



end_time = time.time()
print(int(end_time-start_time))