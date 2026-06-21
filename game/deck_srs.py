"""SRS sessions for Anki / character flashcard decks."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

from game.cards import Card
from game.data import save_game_data
from game.deck_modes import is_tone_mode, normalize_mode, requires_meaning
from game.deck_store import (
    chinese_display,
    generate_choices,
    generate_meaning_choices,
    generate_reverse_choices,
    mode_schedule,
    remember_mistake,
    save_store,
)
from game.pinyin import build_reading, cycle_tone, parse_reading
from game.scheduling import (
    due_count,
    pick_due_id,
    schedule_correct,
    schedule_wrong,
    sorted_due_ids,
    today_str,
)
from game.srs import AnswerResult, Question


@dataclass
class DeckContext:
    deck_file: str
    cards: list[Card]
    srs: dict
    store: dict
    mode: str = "standard"
    global_data: dict | None = None
    by_id: dict[str, Card] = field(init=False)
    fronts: list[str] = field(init=False)
    backs: list[str] = field(init=False)
    meanings: list[str] = field(init=False)

    def __post_init__(self) -> None:
        self.mode = normalize_mode(self.mode)
        self.by_id = {c.id: c for c in self.cards}
        self.fronts = [c.front for c in self.cards]
        self.backs = [c.back for c in self.cards]
        self.meanings = [c.meaning for c in self.cards if c.meaning]

    def eligible_cards(self) -> list[Card]:
        if requires_meaning(self.mode):
            return [c for c in self.cards if c.meaning]
        return self.cards

    def save(self) -> None:
        save_store(self.store)


@dataclass
class ToneDrill:
    char: str
    correct: str
    syllables: list[str]
    tones: list[int]
    level: int
    selected: int = 0

    def reading(self) -> str:
        return build_reading(self.syllables, self.tones)

    def adjust_tone(self, delta: int) -> None:
        idx = self.selected
        self.tones[idx] = cycle_tone(self.tones[idx], delta)

    def move_syllable(self, delta: int) -> None:
        self.selected = (self.selected + delta) % len(self.syllables)


def _schedule(ctx: DeckContext) -> dict:
    return mode_schedule(ctx.srs, ctx.mode, _eligible_ids(ctx))


def _make_tone_drill(ctx: DeckContext, card: Card) -> ToneDrill:
    syllables = parse_reading(card.back)
    if not syllables:
        syllables = [card.back]
    sched = _schedule(ctx)
    level = sched["intervals"].get(card.id, 1)
    return ToneDrill(
        char=card.front,
        correct=card.back,
        syllables=syllables,
        tones=[5] * len(syllables),
        level=level,
    )


def _eligible_ids(ctx: DeckContext) -> list[str]:
    return [c.id for c in ctx.eligible_cards()]


def _record_streak(
    ctx: DeckContext,
    schedule: dict,
    current_streak: int,
    max_streak_this_session: int,
) -> tuple[int, bool]:
    new_max = max(max_streak_this_session, current_streak)
    schedule["all_time_high_streak"] = max(
        int(schedule.get("all_time_high_streak", 0)),
        new_max,
    )
    new_high = False
    if ctx.global_data is not None:
        global_high = int(ctx.global_data.get("all_time_high_streak", 0))
        if new_max > global_high:
            ctx.global_data["all_time_high_streak"] = new_max
            new_high = True
    return new_max, new_high


def _save_deck_session(ctx: DeckContext) -> None:
    if ctx.global_data is not None:
        save_game_data(ctx.global_data)
    ctx.save()


def _pick_card_id(ctx: DeckContext) -> str:
    ids = _eligible_ids(ctx)
    if not ids:
        raise RuntimeError("no cards for current mode")
    card_id = pick_due_id(_schedule(ctx), ids, today_str())
    if card_id is None:
        raise RuntimeError("no cards due today")
    return card_id


def _make_question(ctx: DeckContext, card: Card) -> Question:
    sched = _schedule(ctx)
    level = sched["intervals"].get(card.id, 1)
    mode = ctx.mode

    if mode == "reverse":
        correct = chinese_display(card.front) or card.front
        choices = generate_reverse_choices(correct, card.id, sched, ctx.fronts)
        return Question(char=card.back, correct=correct, choices=choices, level=level)

    if mode == "translate":
        correct = card.meaning
        choices = generate_meaning_choices(correct, card.id, sched, ctx.meanings)
        return Question(char=card.front, correct=correct, choices=choices, level=level)

    if mode == "translate_reverse":
        correct = chinese_display(card.front) or card.front
        choices = generate_reverse_choices(correct, card.id, sched, ctx.fronts)
        return Question(char=card.meaning, correct=correct, choices=choices, level=level)

    correct = card.back
    choices = generate_choices(correct, card.id, sched, ctx.backs)
    return Question(char=card.front, correct=correct, choices=choices, level=level)


@dataclass
class DeckEndlessSession:
    ctx: DeckContext
    current_streak: int = 0
    max_streak_this_session: int = 0
    current: Question | None = None
    current_tone: ToneDrill | None = None
    _current_id: str | None = None

    def __post_init__(self) -> None:
        _schedule(self.ctx)

    @property
    def schedule(self) -> dict:
        return _schedule(self.ctx)

    @property
    def due_remaining(self) -> int:
        return due_count(self.schedule, _eligible_ids(self.ctx), today_str())

    @property
    def srs(self) -> dict:
        return self.ctx.srs

    @property
    def is_tone_mode(self) -> bool:
        return is_tone_mode(self.ctx.mode)

    def next_question(self) -> Question | None:
        if self.is_tone_mode:
            raise RuntimeError("use next_tone_drill in tone mode")
        try:
            card_id = _pick_card_id(self.ctx)
        except RuntimeError:
            return None
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current_tone = None
        self.current = _make_question(self.ctx, card)
        return self.current

    def next_tone_drill(self) -> ToneDrill | None:
        try:
            card_id = _pick_card_id(self.ctx)
        except RuntimeError:
            return None
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current = None
        self.current_tone = _make_tone_drill(self.ctx, card)
        return self.current_tone

    def answer(self, index: int) -> AnswerResult:
        if self.current is None or self._current_id is None:
            raise RuntimeError("no active question")
        q = self.current
        card_id = self._current_id
        selected = q.choices[index]

        if selected == q.correct:
            self.current_streak += 1
            new_iv = schedule_correct(self.schedule, card_id, today_str())
            self.max_streak_this_session, new_high = _record_streak(
                self.ctx,
                self.schedule,
                self.current_streak,
                self.max_streak_this_session,
            )
            return AnswerResult(
                correct=True,
                message=f"Correct! -> {new_iv}d",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )

        streak_broken = self.current_streak
        remember_mistake(self.schedule, card_id, selected, mode=self.ctx.mode)
        schedule_wrong(self.schedule, card_id, today_str())
        self.current_streak = 0
        sub = f"You picked '{selected}'"
        if streak_broken > 0:
            sub = f"Streak broken at {streak_broken}. {sub}"
        return AnswerResult(
            correct=False,
            message=f"Wrong - answer was '{q.correct}'",
            submessage=sub,
            streak_broken=streak_broken,
        )

    def answer_tone(self, drill: ToneDrill) -> AnswerResult:
        if self._current_id is None:
            raise RuntimeError("no active question")
        card_id = self._current_id
        selected = drill.reading()
        correct = drill.correct

        if selected == correct:
            self.current_streak += 1
            new_iv = schedule_correct(self.schedule, card_id, today_str())
            self.max_streak_this_session, new_high = _record_streak(
                self.ctx,
                self.schedule,
                self.current_streak,
                self.max_streak_this_session,
            )
            return AnswerResult(
                correct=True,
                message=f"Correct! -> {new_iv}d",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )

        streak_broken = self.current_streak
        remember_mistake(self.schedule, card_id, selected, mode=self.ctx.mode)
        schedule_wrong(self.schedule, card_id, today_str())
        self.current_streak = 0
        sub = f"You entered '{selected}'"
        if streak_broken > 0:
            sub = f"Streak broken at {streak_broken}"
        return AnswerResult(
            correct=False,
            message="Wrong",
            submessage=sub,
            streak_broken=streak_broken,
        )

    def save(self) -> None:
        _save_deck_session(self.ctx)


@dataclass
class DeckPackSession:
    ctx: DeckContext
    pack_count: int = 1
    sorted_pool: list[str] = field(default_factory=list)
    current_pack: list[str] = field(default_factory=list)
    current: Question | None = None
    current_tone: ToneDrill | None = None
    pack_cleared: bool = False
    pack_rolled: bool = False
    all_done: bool = False
    current_streak: int = 0
    max_streak_this_session: int = 0
    _current_id: str | None = None

    def __post_init__(self) -> None:
        ids = _eligible_ids(self.ctx)
        self.sorted_pool = sorted_due_ids(_schedule(self.ctx), ids, today_str())
        self._load_next_pack()

    @property
    def schedule(self) -> dict:
        return _schedule(self.ctx)

    @property
    def due_remaining(self) -> int:
        return due_count(self.schedule, _eligible_ids(self.ctx), today_str())

    @property
    def srs(self) -> dict:
        return self.ctx.srs

    @property
    def is_tone_mode(self) -> bool:
        return is_tone_mode(self.ctx.mode)

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
            return "Caught up for today!"
        return f"Pack #{self.pack_count} ({len(self.current_pack)} cards)"

    def next_question(self) -> Question | None:
        if self.is_tone_mode:
            raise RuntimeError("use next_tone_drill in tone mode")
        if self.all_done or not self.current_pack:
            return None
        card_id = random.choice(self.current_pack)
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current_tone = None
        self.current = _make_question(self.ctx, card)
        return self.current

    def next_tone_drill(self) -> ToneDrill | None:
        if self.all_done or not self.current_pack:
            return None
        card_id = random.choice(self.current_pack)
        card = self.ctx.by_id[card_id]
        self._current_id = card_id
        self.current = None
        self.current_tone = _make_tone_drill(self.ctx, card)
        return self.current_tone

    def answer(self, index: int) -> AnswerResult:
        if self.current is None or self._current_id is None:
            raise RuntimeError("no active question")
        q = self.current
        card_id = self._current_id
        selected = q.choices[index]
        retry = False

        if selected == q.correct:
            self.current_streak += 1
            new_iv = schedule_correct(self.schedule, card_id, today_str())
            self.max_streak_this_session, new_high = _record_streak(
                self.ctx,
                self.schedule,
                self.current_streak,
                self.max_streak_this_session,
            )
            if card_id in self.current_pack:
                self.current_pack.remove(card_id)
            result = AnswerResult(
                correct=True,
                message=f"Correct! -> {new_iv}d",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )
        else:
            streak_broken = self.current_streak
            remember_mistake(self.schedule, card_id, selected, mode=self.ctx.mode)
            schedule_wrong(self.schedule, card_id, today_str())
            self.current_streak = 0
            retry = True
            front = self.ctx.by_id[card_id].front
            sub = f"'{front}' stays in this pack"
            if streak_broken > 0:
                sub = f"Streak broken at {streak_broken}. {sub}"
            result = AnswerResult(
                correct=False,
                message=f"Wrong - answer was '{q.correct}'",
                submessage=sub,
                streak_broken=streak_broken,
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

    def answer_tone(self, drill: ToneDrill) -> AnswerResult:
        if self._current_id is None:
            raise RuntimeError("no active question")
        card_id = self._current_id
        selected = drill.reading()
        correct = drill.correct
        retry = False

        if selected == correct:
            self.current_streak += 1
            new_iv = schedule_correct(self.schedule, card_id, today_str())
            self.max_streak_this_session, new_high = _record_streak(
                self.ctx,
                self.schedule,
                self.current_streak,
                self.max_streak_this_session,
            )
            if card_id in self.current_pack:
                self.current_pack.remove(card_id)
            result = AnswerResult(
                correct=True,
                message=f"Correct! -> {new_iv}d",
                submessage=f"Streak: {self.current_streak}",
                new_high_streak=new_high,
            )
        else:
            streak_broken = self.current_streak
            matrix = self.schedule["confusion_matrix"].setdefault(card_id, [])
            if selected not in matrix:
                matrix.append(selected)
            schedule_wrong(self.schedule, card_id, today_str())
            self.current_streak = 0
            retry = True
            front = self.ctx.by_id[card_id].front
            sub = f"'{front}' stays in this pack"
            if streak_broken > 0:
                sub = f"Streak broken at {streak_broken}. {sub}"
            result = AnswerResult(
                correct=False,
                message="Wrong",
                submessage=sub,
                streak_broken=streak_broken,
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
        _save_deck_session(self.ctx)
