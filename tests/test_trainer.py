"""ZenKi backend tests.

These tests focus on the reusable trainer package rather than Streamlit UI.
They verify the rules that main.py depends on: validation, Leitner behavior,
session statistics, analytics, JSON persistence, and session history.
"""

from __future__ import annotations

import json

import pytest

from trainer import (
    ALLOWED_SESSION_SIZES,
    Card,
    Deck,
    Rating,
    Session,
    append_session_history,
    cards_to_dataframe,
    box_distribution,
    deck_summary,
    load_deck,
    load_session_history,
    save_deck,
    validate_deck,
    validate_japanese_writing,
    validate_practice_size,
)


def make_card(index: int, language: str = "Spanish", level: str = "A1") -> Card:
    return Card(
        card_id=f"card_{index:02d}",
        language=language,
        level=level,
        front=f"palabra {index}",
        meaning=f"word {index}",
        example=f"Ejemplo {index}.",
        translation=f"Example {index}.",
    )


def make_deck(count: int = 50) -> Deck:
    cards = [make_card(i) for i in range(1, count + 1)]
    return Deck(
        name="Spanish A1",
        language="Spanish",
        level="A1",
        cards=cards,
    )


def test_allowed_session_sizes() -> None:
    assert ALLOWED_SESSION_SIZES == (10, 20, 25)
    assert validate_practice_size(10).valid
    assert validate_practice_size(20).valid
    assert validate_practice_size(25).valid
    assert not validate_practice_size(15).valid


def test_fifty_card_deck_validation() -> None:
    deck = make_deck(50)
    result = validate_deck(deck, require_fifty_cards=True)
    assert result.valid
    assert deck.is_full_deck


def test_wrong_deck_size_is_rejected() -> None:
    deck = make_deck(49)
    result = validate_deck(deck, require_fifty_cards=True)
    assert not result.valid
    assert "exactly 50 cards" in " ".join(result.errors)


def test_good_moves_one_leitner_box() -> None:
    deck = make_deck()
    card = deck.cards[0]
    session = Session(deck, 10)
    session.start(deck.cards[:10])

    session.rate_current_card(Rating.GOOD)

    assert card.box == 2
    assert card.review_count == 1
    assert card.correct_count == 1
    assert session.good_count == 1
    assert session.accuracy == 100.0


def test_easy_moves_two_leitner_boxes() -> None:
    deck = make_deck()
    card = deck.cards[0]
    session = Session(deck, 10)
    session.start(deck.cards[:10])

    session.rate_current_card(Rating.EASY)

    assert card.box == 3
    assert card.review_count == 1
    assert card.correct_count == 1
    assert session.easy_count == 1


def test_again_returns_card_to_box_one_and_requeues() -> None:
    deck = make_deck()
    card = deck.cards[0]
    session = Session(deck, 10)
    session.start(deck.cards[:10])

    session.rate_current_card(Rating.AGAIN)

    assert card.box == 1
    assert card.review_count == 1
    assert card.again_count == 1
    assert session.again_count == 1
    assert card in session.queue
    assert len(session.completed_cards) == 0


def test_again_retry_limit_allows_session_completion() -> None:
    deck = make_deck()
    session = Session(deck, 10)
    session.start(deck.cards[:10])

    # Force the current card through the retry limit, then finish the rest.
    for _ in range(3):
        session.rate_current_card("again")

    while not session.is_complete:
        session.rate_current_card("good")

    assert session.is_complete
    assert len(session.completed_cards) == 10
    assert session.again_count >= 3


def test_session_accuracy_counts_good_and_easy_only() -> None:
    deck = make_deck()
    session = Session(deck, 10)
    session.start(deck.cards[:10])

    session.rate_current_card("good")
    session.rate_current_card("easy")
    session.rate_current_card("again")

    assert session.total_ratings == 3
    assert session.correct_count == 2
    assert session.accuracy == pytest.approx(66.67, rel=1e-4)


def test_box_distribution_and_dataframe() -> None:
    deck = make_deck()
    deck.cards[0].mark_good()
    deck.cards[1].mark_easy()

    distribution = box_distribution(deck.cards)
    assert distribution == {1: 48, 2: 1, 3: 1, 4: 0, 5: 0}

    df = cards_to_dataframe(deck.cards)
    assert len(df) == 50
    assert {"front", "meaning", "box", "accuracy"}.issubset(df.columns)


def test_deck_summary_contains_expected_metrics() -> None:
    deck = make_deck()
    deck.cards[0].mark_good()
    summary = deck_summary(deck)

    assert summary["total_cards"] == 50
    assert summary["reviewed_cards"] == 1
    assert summary["new_cards"] == 49
    assert summary["accuracy"] == 100.0


def test_japanese_writing_validation() -> None:
    card = Card(
        card_id="ja_01",
        language="Japanese",
        level="N5",
        front="学生",
        meaning="student",
        example="私は学生です。",
        translation="I am a student.",
        reading="がくせい",
        kanji="学生",
        hiragana="がくせい",
        romaji="gakusei",
    )
    result = validate_japanese_writing(card)
    assert result.valid
    assert not result.errors


def test_deck_round_trip_json(tmp_path) -> None:
    deck = make_deck()
    deck.cards[0].mark_easy()

    save_deck(deck, "spanish_a1.json", data_dir=tmp_path)
    loaded = load_deck("spanish_a1.json", data_dir=tmp_path)

    assert loaded.card_count == 50
    assert loaded.cards[0].box == 3
    assert loaded.cards[0].last_rating == "easy"


def test_session_history_round_trip(tmp_path) -> None:
    entry = {
        "session_id": "session-001",
        "timestamp": "2026-10-02T20:00:00",
        "deck": "Spanish A1",
        "language": "Spanish",
        "level": "A1",
        "cards_selected": 10,
        "good": 6,
        "easy": 4,
        "again": 0,
        "total_ratings": 10,
        "correct_ratings": 10,
        "accuracy": 100.0,
    }

    history = append_session_history(entry, data_dir=tmp_path)
    loaded = load_session_history(data_dir=tmp_path)

    assert history == [entry]
    assert loaded == [entry]


def test_history_file_is_not_treated_as_a_deck(tmp_path) -> None:
    deck = make_deck()
    save_deck(deck, "spanish_a1.json", data_dir=tmp_path)
    append_session_history(
        {"session_id": "s1", "accuracy": 100.0},
        data_dir=tmp_path,
    )

    from trainer import list_deck_files

    assert [path.name for path in list_deck_files(tmp_path)] == ["spanish_a1.json"]


def test_corrupt_history_is_reported(tmp_path) -> None:
    from trainer import get_session_history_path, CorruptJSONError

    path = get_session_history_path(tmp_path)
    path.write_text("{not-json}", encoding="utf-8")

    with pytest.raises(CorruptJSONError):
        load_session_history(data_dir=tmp_path)
