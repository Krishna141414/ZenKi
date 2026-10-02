"""
ZenKi Analysis Module
=====================

This module provides study analytics for ZenKi using NumPy and Pandas.

Responsibilities:
- Calculate card-level and deck-level accuracy.
- Summarize Again / Good / Easy ratings.
- Find weak cards.
- Show Leitner box distribution.
- Build Pandas DataFrames from cards and review history.
- Calculate session summaries and numerical statistics with NumPy.
- Provide data in structures that the future Streamlit UI can display.

This module does not handle:
- Streamlit UI
- JSON/file persistence
- input validation rules

Those responsibilities belong to main.py, storage.py, and validators.py.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np
import pandas as pd

from .models import (
    Card,
    Deck,
    MAX_LEITNER_BOX,
    MIN_LEITNER_BOX,
    Session,
)


# ============================================================
# INTERNAL HELPERS
# ============================================================

def _require_cards(cards: Iterable[Card]) -> List[Card]:
    """Convert an iterable of cards to a validated list."""
    card_list = list(cards)

    if any(not isinstance(card, Card) for card in card_list):
        raise TypeError("All items must be Card objects.")

    return card_list


def _percentage(numerator: float, denominator: float) -> float:
    """Return a rounded percentage while safely handling zero."""
    if denominator == 0:
        return 0.0

    return round((numerator / denominator) * 100, 2)


# ============================================================
# CARD DATAFRAME
# ============================================================

def cards_to_dataframe(cards: Iterable[Card]) -> pd.DataFrame:
    """
    Convert cards into a Pandas DataFrame.

    The resulting table is suitable for display, filtering,
    statistical analysis, or later CSV export.
    """
    card_list = _require_cards(cards)

    columns = [
        "id",
        "language",
        "level",
        "front",
        "meaning",
        "example",
        "translation",
        "reading",
        "kanji",
        "hiragana",
        "romaji",
        "katakana",
        "box",
        "review_count",
        "correct_count",
        "again_count",
        "accuracy",
        "is_new",
        "is_weak",
        "last_rating",
        "last_reviewed",
    ]

    rows = []

    for card in card_list:
        rows.append(
            {
                "id": card.card_id,
                "language": card.language,
                "level": card.level,
                "front": card.front,
                "meaning": card.meaning,
                "example": card.example,
                "translation": card.translation,
                "reading": card.reading,
                "kanji": card.kanji,
                "hiragana": card.hiragana,
                "romaji": card.romaji,
                "katakana": card.katakana,
                "box": card.box,
                "review_count": card.review_count,
                "correct_count": card.correct_count,
                "again_count": card.again_count,
                "accuracy": card.accuracy,
                "is_new": card.is_new,
                "is_weak": card.is_weak,
                "last_rating": card.last_rating,
                "last_reviewed": card.last_reviewed,
            }
        )

    return pd.DataFrame(rows, columns=columns)


# ============================================================
# CARD-LEVEL ANALYSIS
# ============================================================

def card_accuracy(card: Card) -> float:
    """Return one card's historical accuracy percentage."""
    if not isinstance(card, Card):
        raise TypeError("card_accuracy expects a Card object.")

    return card.accuracy


def average_card_accuracy(cards: Iterable[Card]) -> float:
    """
    Return the mean accuracy across reviewed cards.

    NumPy is used for the numerical aggregation.
    New/unreviewed cards are excluded because they have no
    meaningful historical accuracy yet.
    """
    card_list = _require_cards(cards)

    accuracies = np.array(
        [
            card.accuracy
            for card in card_list
            if card.review_count > 0
        ],
        dtype=float,
    )

    if accuracies.size == 0:
        return 0.0

    return round(float(np.mean(accuracies)), 2)


def weighted_accuracy(cards: Iterable[Card]) -> float:
    """
    Return review-weighted accuracy across cards.

    This is usually more representative than a simple average
    because cards with more review attempts contribute proportionally.
    """
    card_list = _require_cards(cards)

    total_reviews = np.array(
        [card.review_count for card in card_list],
        dtype=float,
    )
    total_correct = np.array(
        [card.correct_count for card in card_list],
        dtype=float,
    )

    reviews = float(np.sum(total_reviews))
    correct = float(np.sum(total_correct))

    return _percentage(correct, reviews)


def get_weak_cards(
    cards: Iterable[Card],
    limit: Optional[int] = None,
) -> List[Card]:
    """
    Return cards needing more attention.

    Cards are ranked by:
    1. Lowest accuracy
    2. Higher Again count
    3. Lower Leitner box

    New cards are excluded because they have no review history.
    """
    card_list = [
        card
        for card in _require_cards(cards)
        if card.review_count > 0 and card.is_weak
    ]

    card_list.sort(
        key=lambda card: (
            card.accuracy,
            -card.again_count,
            card.box,
        )
    )

    if limit is not None:
        if limit <= 0:
            raise ValueError("limit must be greater than zero.")
        return card_list[:limit]

    return card_list


def get_new_cards(cards: Iterable[Card]) -> List[Card]:
    """Return cards that have never been reviewed."""
    return [card for card in _require_cards(cards) if card.is_new]


# ============================================================
# LEITNER BOX ANALYSIS
# ============================================================

def box_distribution(cards: Iterable[Card]) -> Dict[int, int]:
    """
    Return the number of cards in each Leitner box.

    All five boxes are always present, including boxes with zero cards.
    """
    card_list = _require_cards(cards)

    distribution = {
        box: 0
        for box in range(MIN_LEITNER_BOX, MAX_LEITNER_BOX + 1)
    }

    for card in card_list:
        distribution[card.box] += 1

    return distribution


def box_distribution_dataframe(cards: Iterable[Card]) -> pd.DataFrame:
    """Return Leitner box distribution as a Pandas DataFrame."""
    distribution = box_distribution(cards)

    return pd.DataFrame(
        [
            {
                "box": box,
                "cards": count,
            }
            for box, count in distribution.items()
        ]
    )


# ============================================================
# RATING ANALYSIS
# ============================================================

def rating_counts(
    history: Iterable[Mapping[str, Any]],
) -> Dict[str, int]:
    """
    Count Again / Good / Easy ratings from review history.

    Unknown rating values raise ValueError instead of silently
    producing misleading analytics.
    """
    counts = {
        "again": 0,
        "good": 0,
        "easy": 0,
    }

    for entry in history:
        rating = str(entry.get("rating", "")).strip().lower()

        if rating not in counts:
            raise ValueError(
                f"Unknown rating '{rating}' found in review history."
            )

        counts[rating] += 1

    return counts


def rating_counts_from_session(session: Session) -> Dict[str, int]:
    """Count ratings directly from a ZenKi Session."""
    if not isinstance(session, Session):
        raise TypeError(
            "rating_counts_from_session expects a Session object."
        )

    return rating_counts(session.rating_history)


def rating_dataframe(
    history: Iterable[Mapping[str, Any]],
) -> pd.DataFrame:
    """Convert review history into a Pandas DataFrame."""
    rows = []

    for entry in history:
        rows.append(
            {
                "card_id": entry.get("card_id", ""),
                "rating": entry.get("rating", ""),
                "box_after": entry.get("box_after", np.nan),
                "timestamp": entry.get("timestamp"),
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "card_id",
            "rating",
            "box_after",
            "timestamp",
        ],
    )


# ============================================================
# SESSION ANALYSIS
# ============================================================

def session_accuracy(session: Session) -> float:
    """Return accuracy for a completed or in-progress Session."""
    if not isinstance(session, Session):
        raise TypeError("session_accuracy expects a Session object.")

    ratings = np.array(
        [
            1 if entry["rating"] in {"good", "easy"} else 0
            for entry in session.rating_history
        ],
        dtype=float,
    )

    if ratings.size == 0:
        return 0.0

    return round(float(np.mean(ratings) * 100), 2)


def session_summary(session: Session) -> Dict[str, Any]:
    """
    Return a complete session summary.

    Accuracy:
        (Good + Easy) / all rating attempts * 100

    Both the individual rating counts and the combined accuracy are
    preserved so the Streamlit result page can show Good, Easy, Again
    separately.
    """
    if not isinstance(session, Session):
        raise TypeError("session_summary expects a Session object.")

    counts = rating_counts_from_session(session)
    accuracy = session_accuracy(session)

    return {
        "deck": session.deck.name,
        "language": session.deck.language,
        "level": session.deck.level,
        "cards_selected": session.practice_size,
        "good": counts["good"],
        "easy": counts["easy"],
        "again": counts["again"],
        "total_ratings": sum(counts.values()),
        "correct_ratings": counts["good"] + counts["easy"],
        "accuracy": accuracy,
        "completed": len(session.completed_cards),
        "remaining": len(session.queue),
    }


def session_summary_dataframe(session: Session) -> pd.DataFrame:
    """Return a one-row DataFrame for easy Streamlit/table display."""
    return pd.DataFrame([session_summary(session)])


# ============================================================
# DECK ANALYSIS
# ============================================================

def deck_summary(deck: Deck) -> Dict[str, Any]:
    """
    Return a comprehensive statistical summary for one deck.

    Uses both Pandas and NumPy through the functions above.
    """
    if not isinstance(deck, Deck):
        raise TypeError("deck_summary expects a Deck object.")

    cards = deck.cards

    review_counts = np.array(
        [card.review_count for card in cards],
        dtype=float,
    )

    again_counts = np.array(
        [card.again_count for card in cards],
        dtype=float,
    )

    accuracies = np.array(
        [
            card.accuracy
            for card in cards
            if card.review_count > 0
        ],
        dtype=float,
    )

    total_reviews = float(np.sum(review_counts))
    total_again = float(np.sum(again_counts))
    total_correct = float(
        np.sum([card.correct_count for card in cards])
    )

    return {
        "deck": deck.name,
        "language": deck.language,
        "level": deck.level,
        "total_cards": len(cards),
        "new_cards": len(get_new_cards(cards)),
        "reviewed_cards": sum(
            1 for card in cards if card.review_count > 0
        ),
        "weak_cards": len(get_weak_cards(cards)),
        "total_reviews": int(total_reviews),
        "total_correct": int(total_correct),
        "total_again": int(total_again),
        "accuracy": _percentage(total_correct, total_reviews),
        "average_card_accuracy": (
            round(float(np.mean(accuracies)), 2)
            if accuracies.size
            else 0.0
        ),
        "median_card_accuracy": (
            round(float(np.median(accuracies)), 2)
            if accuracies.size
            else 0.0
        ),
        "average_reviews_per_card": (
            round(float(np.mean(review_counts)), 2)
            if review_counts.size
            else 0.0
        ),
        "box_distribution": box_distribution(cards),
    }


def deck_summary_dataframe(deck: Deck) -> pd.DataFrame:
    """Return the main deck summary as a one-row DataFrame."""
    summary = deck_summary(deck)

    # Keep box distribution out of the main tabular row and expose
    # each box as its own column for easier UI/charting.
    boxes = summary.pop("box_distribution")

    for box, count in boxes.items():
        summary[f"box_{box}"] = count

    return pd.DataFrame([summary])


def deck_card_dataframe(deck: Deck) -> pd.DataFrame:
    """Return all cards in a deck as a Pandas DataFrame."""
    if not isinstance(deck, Deck):
        raise TypeError("deck_card_dataframe expects a Deck object.")

    return cards_to_dataframe(deck.cards)


# ============================================================
# DAILY / SESSION SCORE
# ============================================================

def calculate_score(
    good: int,
    easy: int,
    again: int,
) -> float:
    """
    Calculate a simple study score from rating counts.

    Scoring:
        Good  = 1.0 point
        Easy  = 1.0 point
        Again = 0.0 points

    The returned value is a percentage from 0 to 100 and therefore
    matches the same interpretation as session accuracy.
    """
    values = np.array(
        [good, easy, again],
        dtype=float,
    )

    if np.any(values < 0):
        raise ValueError("Rating counts cannot be negative.")

    attempts = float(np.sum(values))

    if attempts == 0:
        return 0.0

    correct = float(values[0] + values[1])

    return round(float((correct / attempts) * 100), 2)


def score_label(score: float) -> str:
    """
    Return a neutral descriptive label for a score.

    The labels describe the measured result and are not a quality
    ranking of the learner.
    """
    if not 0 <= score <= 100:
        raise ValueError("Score must be between 0 and 100.")

    if score == 100:
        return "All ratings were correct"
    if score >= 80:
        return "Most ratings were correct"
    if score >= 60:
        return "Mixed results"
    return "More review needed"


# ============================================================
# ANALYTICS TABLES
# ============================================================

def weak_cards_dataframe(
    cards: Iterable[Card],
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Return weak cards in an analysis-ready Pandas DataFrame."""
    weak = get_weak_cards(cards, limit=limit)

    return cards_to_dataframe(weak)


def language_summary(
    decks: Mapping[str, Deck] | Iterable[Deck],
) -> pd.DataFrame:
    """
    Create a Pandas summary table across multiple decks.

    The table is useful for a future Progress dashboard.
    """
    if isinstance(decks, Mapping):
        deck_list = list(decks.values())
    else:
        deck_list = list(decks)

    for deck in deck_list:
        if not isinstance(deck, Deck):
            raise TypeError("All items must be Deck objects.")

    rows = []

    for deck in deck_list:
        summary = deck_summary(deck)

        rows.append(
            {
                "language": summary["language"],
                "level": summary["level"],
                "deck": summary["deck"],
                "total_cards": summary["total_cards"],
                "new_cards": summary["new_cards"],
                "reviewed_cards": summary["reviewed_cards"],
                "weak_cards": summary["weak_cards"],
                "accuracy": summary["accuracy"],
                "total_reviews": summary["total_reviews"],
            }
        )

    return pd.DataFrame(
        rows,
        columns=[
            "language",
            "level",
            "deck",
            "total_cards",
            "new_cards",
            "reviewed_cards",
            "weak_cards",
            "accuracy",
            "total_reviews",
        ],
    )


# ============================================================
# NUMPY STUDY STATISTICS
# ============================================================

def numerical_statistics(values: Sequence[float | int]) -> Dict[str, float]:
    """
    Calculate basic numerical statistics using NumPy.

    Useful for analysis demonstrations and future dashboard cards.
    """
    array = np.asarray(values, dtype=float)

    if array.size == 0:
        return {
            "count": 0.0,
            "mean": 0.0,
            "median": 0.0,
            "minimum": 0.0,
            "maximum": 0.0,
            "standard_deviation": 0.0,
        }

    return {
        "count": float(array.size),
        "mean": round(float(np.mean(array)), 2),
        "median": round(float(np.median(array)), 2),
        "minimum": round(float(np.min(array)), 2),
        "maximum": round(float(np.max(array)), 2),
        "standard_deviation": round(float(np.std(array)), 2),
    }


def card_accuracy_statistics(cards: Iterable[Card]) -> Dict[str, float]:
    """Return NumPy statistics for reviewed card accuracies."""
    reviewed = [
        card.accuracy
        for card in _require_cards(cards)
        if card.review_count > 0
    ]

    return numerical_statistics(reviewed)


# ============================================================
# EXPORTS
# ============================================================

__all__ = [
    "average_card_accuracy",
    "box_distribution",
    "box_distribution_dataframe",
    "calculate_score",
    "card_accuracy",
    "card_accuracy_statistics",
    "cards_to_dataframe",
    "deck_card_dataframe",
    "deck_summary",
    "deck_summary_dataframe",
    "get_new_cards",
    "get_weak_cards",
    "language_summary",
    "numerical_statistics",
    "rating_counts",
    "rating_counts_from_session",
    "rating_dataframe",
    "score_label",
    "session_accuracy",
    "session_summary",
    "session_summary_dataframe",
    "weighted_accuracy",
    "weak_cards_dataframe",
]
