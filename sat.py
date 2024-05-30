class Question:
    def __init__(self, question_id, text, answer_choices, correct_answer, rationale,question_type):
        self.question_id = question_id
        self.text = " ".join(text) if isinstance(text, list) else text
        self.answer_choices = answer_choices
        self.correct_answer = correct_answer
        self.rationale = rationale
        self.question_type = question_type


    def __str__(self):
        answer_choices_str = "\n".join([f"{key}: {value}" for key, value in self.answer_choices.items()])
        return (f"Question ID: {self.question_id}\n"
                f"Type: {self.question_type}\n"
                f"Text: {self.text}\n"
                f"Answer Choices:\n{answer_choices_str}\n"
                f"Correct Answer: {self.correct_answer}\n"
                f"Rationale: {self.rationale}\n")

    def check_answer(self, answer):
        """
        Проверяет правильность переданного варианта ответа.

        :param answer: Вариант ответа, который нужно проверить (например, 'A', 'B', 'C', 'D')
        :return: True, если ответ правильный, False в противном случае
        """
        return answer == self.correct_answer