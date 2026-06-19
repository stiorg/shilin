"""SRS game logic — endless streak and focused 5-pack modes."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game.data import BOPOMOFO_DICT, generate_dynamic_choices, save_game_data


@dataclass
class Question:
    char: str
    correct: str
    choices: list[str]
    level: int
    hint: str = ""


@dataclass
class AnswerResult:
    correct: bool
    message: str
    submessage: str = ""
    new_high_streak: bool = False
    streak_broken: int = 0


@dataclass
class EndlessSession:
    game_data: dict
    current_streak: int = 0
    max_streak_this_session: int = 0
    current: Question | None = None

    @property
    def intervals(self) -> dict:
        return self.game_data["intervals"]

    @property
    def confusion_matrix(self) -> dict:
        return self.game_data["confusion_matrix"]

    def next_question(self) -> Question:
        chars = list(BOPOMOFO_DICT.keys())
        weights = [1.0 / self.intervals[c] for c in chars]
        char = random.choices(chars, weights=weights, k=1)[0]
        correct = BOPOMOFO_DICT[char]
        choices = generate_dynamic_choices(correct, char, self.game_data)
        self.current = Question(char, correct, choices, self.intervals[char])
        return self.current

    def answer(self, index: int) -> AnswerResult:
        if self.current is None:
            raise RuntimeError("no active question")
        q = self.current
        selected = q.choices[index]

        if selected == q.correct:
            self.current_streak += 1
            self.intervals[q.char] = min(self.intervals[q.char] * 2, 32)
            new_high = False
            if self.current_streak > self.max_streak_this_session:
                self.max_streak_this_session = self.current_streak
            if self.max_streak_this_session > self.game_data["all_time_high_streak"]:
                self.game_data["all_time_high_streak"] = self.max_streak_this_session
                new_high = True
            return AnswerResult(
                correct=True,
                message=f"Correct! {q.char} -> Lv.{self.intervals[q.char]}",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )

        streak_broken = self.current_streak
        if selected not in self.confusion_matrix[q.char]:
            self.confusion_matrix[q.char].append(selected)
        self.intervals[q.char] = 1
        self.current_streak = 0
        msg = f"Wrong - answer was '{q.correct}'"
        sub = f"You picked '{selected}'"
        if streak_broken > 0:
            sub = f"Streak broken at {streak_broken}. {sub}"
        return AnswerResult(
            correct=False,
            message=msg,
            submessage=sub,
            streak_broken=streak_broken,
        )

    def save(self) -> None:
        save_game_data(self.game_data)


@dataclass
class PackSession:
    game_data: dict
    pack_count: int = 1
    sorted_pool: list[str] = field(default_factory=list)
    current_pack: list[str] = field(default_factory=list)
    current: Question | None = None
    pack_cleared: bool = False
    pack_rolled: bool = False
    all_done: bool = False

    def __post_init__(self) -> None:
        chars = list(BOPOMOFO_DICT.keys())
        self.sorted_pool = sorted(chars, key=lambda c: self.game_data["intervals"][c])
        self._load_next_pack()

    @property
    def intervals(self) -> dict:
        return self.game_data["intervals"]

    @property
    def confusion_matrix(self) -> dict:
        return self.game_data["confusion_matrix"]

    def _load_next_pack(self) -> None:
        self.pack_cleared = False
        if not self.sorted_pool:
            self.current_pack = []
            self.all_done = True
            return
        self.current_pack = self.sorted_pool[:5]
        self.sorted_pool = self.sorted_pool[5:]

    def pack_label(self) -> str:
        if self.all_done:
            return "All packs cleared!"
        return f"Pack #{self.pack_count}: {', '.join(self.current_pack)}"

    def next_question(self) -> Question | None:
        if self.all_done or not self.current_pack:
            return None
        char = random.choice(self.current_pack)
        correct = BOPOMOFO_DICT[char]
        choices = generate_dynamic_choices(correct, char, self.game_data)
        self.current = Question(char, correct, choices, self.intervals[char])
        return self.current

    def answer(self, index: int) -> AnswerResult:
        if self.current is None:
            raise RuntimeError("no active question")
        q = self.current
        selected = q.choices[index]
        retry = False

        if selected == q.correct:
            self.intervals[q.char] = min(self.intervals[q.char] * 2, 32)
            if q.char in self.current_pack:
                self.current_pack.remove(q.char)
            result = AnswerResult(
                correct=True,
                message=f"Correct! {q.char} -> Lv.{self.intervals[q.char]}",
            )
        else:
            if selected not in self.confusion_matrix[q.char]:
                self.confusion_matrix[q.char].append(selected)
            self.intervals[q.char] = 1
            retry = True
            result = AnswerResult(
                correct=False,
                message=f"Wrong - answer was '{q.correct}'",
                submessage=f"'{q.char}' stays in this pack",
            )

        if not self.current_pack:
            self.pack_cleared = True
            save_game_data(self.game_data)
            self.pack_count += 1
            self._load_next_pack()
            self.pack_rolled = not self.all_done
        elif retry:
            pass

        return result

    def save(self) -> None:
        save_game_data(self.game_data)
