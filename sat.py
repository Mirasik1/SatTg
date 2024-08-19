class Question:
    def __init__(self, question_id, text, answer_choices, correct_answer, rationale, question_type, url=None):
        self.question_id = question_id
        self.text = " ".join(text) if isinstance(text, list) else text
        self.answer_choices = answer_choices
        self.correct_answer = correct_answer
        self.rationale = rationale
        self.question_type = question_type
        self.url = url

    def __str__(self):
        return (f"Question ID: {self.question_id}\n"
                f"Type: {self.question_type}\n"
                f"Text: {self.text}\n"
                f"Answer Choices:\n{self.answer_choices}\n"
                f"Correct Answer: {self.correct_answer}\n"
                f"Rationale: {self.rationale}\n"
                f"URL: {self.url}\n")

    def check_answer(self, answer):
        return answer == self.correct_answer

    def to_dict(self):
        return {
            'question_id': self.question_id,
            'text': self.text,
            'answer_choices': self.answer_choices,
            'correct_answer': self.correct_answer,
            'rationale': self.rationale,
            'question_type': self.question_type,
            'url': self.url
        }