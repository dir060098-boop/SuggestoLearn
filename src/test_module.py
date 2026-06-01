import random
from dataclasses import dataclass, field
from src.srs import update_srs


@dataclass
class Question:
    word_id:    int
    word:       str
    correct:    str
    options:    list[str]   # 4 items, shuffled
    answered:   str | None = None

    @property
    def is_correct(self) -> bool:
        return self.answered == self.correct


@dataclass
class TestSession:
    questions:  list[Question] = field(default_factory=list)
    current:    int = 0

    @property
    def total(self) -> int:
        return len(self.questions)

    @property
    def done(self) -> bool:
        return self.current >= self.total

    @property
    def score(self) -> float:
        if not self.questions:
            return 0.0
        correct = sum(1 for q in self.questions if q.is_correct)
        return round(correct / self.total * 100, 1)

    @property
    def errors(self) -> list[Question]:
        return [q for q in self.questions if not q.is_correct]

    def current_question(self) -> Question | None:
        if self.done:
            return None
        return self.questions[self.current]

    def answer(self, choice: str) -> bool:
        q = self.current_question()
        if q is None:
            return False
        q.answered = choice

        # SRS quality: 5 = correct on first try, 2 = wrong
        quality = 5 if q.is_correct else 2
        update_srs(q.word_id, quality)

        self.current += 1
        return q.is_correct


def build_test(words: list[dict]) -> TestSession:
    """
    Build a test from a list of word dicts.
    Each question: show word → pick correct translation from 4 options.
    """
    translations = [w["translation"] for w in words]
    questions = []

    for w in words:
        correct = w["translation"]
        distractors = [t for t in translations if t != correct]
        distractors = random.sample(distractors, min(3, len(distractors)))

        # Pad to 3 distractors if word list is small
        while len(distractors) < 3:
            distractors.append("—")

        options = distractors + [correct]
        random.shuffle(options)

        questions.append(Question(
            word_id=w["id"],
            word=w["word"],
            correct=correct,
            options=options,
        ))

    random.shuffle(questions)
    return TestSession(questions=questions)
