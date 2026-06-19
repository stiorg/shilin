"""SRS sessions for Anki / character flashcard decks."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game.cards import Card
from game.deck_store import generate_choices, save_store
from game.srs import AnswerResult, Question


@dataclass
class DeckContext:
    deck_file: str
    cards: list[Card]
    srs: dict
    store: dict
    by_id: dict[str, Card] = field(init=False)
    answers: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.by_id = {c.id: c for c in self.cards}
        self.answers = [c.back for c in self.cards]

    def save(self) -> None:
        save_store(self.store)


def _make_question(ctx: DeckContext, card: Card) -> Question:
    correct = card.back
    choices = generate_choices(correct, card.id, ctx.srs, ctx.answers)
    level = ctx.srs["intervals"].get(card.id, 1)
    return Question(char=card.front, correct=correct, choices=choices, level=level)


@dataclass
class DeckEndlessSession:
    ctx: DeckContext
    current_streak: int = 0
    max_streak_this_session: int = 0
    current: Question | None = None
    _current_id: str | None = None

    @property
    def srs(self) -> dict:
        return self.ctx.srs

    def next_question(self) -> Question:
        ids = [c.id for c in self.ctx.cards]
        weights = [1.0 / self.srs["intervals"].get(cid, 1) for cid in ids]
        card_id = random.choices(ids, weights=weights, k=1)[0]
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current = _make_question(self.ctx, card)
        return self.current

    def answer(self, index: int) -> AnswerResult:
        if self.current is None or self._current_id is None:
            raise RuntimeError("no active question")
        q = self.current
        card_id = self._current_id
        selected = q.choices[index]

        if selected == q.correct:
            self.current_streak += 1
            self.srs["intervals"][card_id] = min(self.srs["intervals"].get(card_id, 1) * 2, 32)
            new_high = False
            if self.current_streak > self.max_streak_this_session:
                self.max_streak_this_session = self.current_streak
            if self.max_streak_this_session > self.srs["all_time_high_streak"]:
                self.srs["all_time_high_streak"] = self.max_streak_this_session
                new_high = True
            return AnswerResult(
                correct=True,
                message=f"Correct! → Lv.{self.srs['intervals'][card_id]}",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )

        streak_broken = self.current_streak
        matrix = self.srs["confusion_matrix"].setdefault(card_id, [])
        if selected not in matrix:
            matrix.append(selected)
        self.srs["intervals"][card_id] = 1
        self.current_streak = 0
        sub = f"You picked '{selected}'"
        if streak_broken > 0:
            sub = f"Streak broken at {streak_broken}. {sub}"
        return AnswerResult(
            correct=False,
            message=f"Wrong — answer was '{q.correct}'",
            submessage=sub,
            streak_broken=streak_broken,
        )

    def save(self) -> None:
        self.ctx.save()


@dataclass
class DeckPackSession:
    ctx: DeckContext
    pack_count: int = 1
    sorted_pool: list[str] = field(default_factory=list)
    current_pack: list[str] = field(default_factory=list)
    current: Question | None = None
    pack_cleared: bool = False
    pack_rolled: bool = False
    all_done: bool = False
    _current_id: str | None = None

    def __post_init__(self) -> None:
        ids = [c.id for c in self.ctx.cards]
        self.sorted_pool = sorted(ids, key=lambda cid: self.srs["intervals"].get(cid, 1))
        self._load_next_pack()

    @property
    def srs(self) -> dict:
        return self.ctx.srs

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
        return f"Pack #{self.pack_count} ({len(self.current_pack)} cards)"

    def next_question(self) -> Question | None:
        if self.all_done or not self.current_pack:
            return None
        card_id = random.choice(self.current_pack)
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current = _make_question(self.ctx, card)
        return self.current

    def answer(self, index: int) -> AnswerResult:
        if self.current is None or self._current_id is None:
            raise RuntimeError("no active question")
        q = self.current
        card_id = self._current_id
        selected = q.choices[index]
        retry = False

        if selected == q.correct:
            self.srs["intervals"][card_id] = min(self.srs["intervals"].get(card_id, 1) * 2, 32)
            if card_id in self.current_pack:
                self.current_pack.remove(card_id)
            result = AnswerResult(
                correct=True,
                message=f"Correct! → Lv.{self.srs['intervals'][card_id]}",
            )
        else:
            matrix = self.srs["confusion_matrix"].setdefault(card_id, [])
            if selected not in matrix:
                matrix.append(selected)
            self.srs["intervals"][card_id] = 1
            retry = True
            front = self.ctx.by_id[card_id].front
            result = AnswerResult(
                correct=False,
                message=f"Wrong — answer was '{q.correct}'",
                submessage=f"'{front}' stays in this pack",
            )

        if not self.current_pack:
            self.pack_cleared = True
            self.ctx.save()
            self.pack_count += 1
            self._load_next_pack()
            self.pack_rolled = not self.all_done
        elif retry:
            pass

        return result

    def save(self) -> None:
        self.ctx.save()
