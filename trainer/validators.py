"""
ZenKi Validation Module
=======================

This module contains validation helpers for ZenKi.

Responsibilities:
- Validate text fields.
- Validate supported languages and levels.
- Validate practice-session sizes.
- Validate learner ratings.
- Validate Japanese writing fields when present.
- Validate Card and Deck objects before they are used or stored.
- Provide reusable validation results for the future Streamlit UI and tests.

This module contains no Streamlit code and no file I/O.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

from .models import (
    ALLOWED_SESSION_SIZES,
    Card,
    Deck,
    MAX_LEITNER_BOX,
    MIN_LEITNER_BOX,
    Rating,
)


# ============================================================
# SUPPORTED APPLICATION VALUES
# ============================================================

SUPPORTED_LANGUAGES = {
    "Japanese",
    "Spanish",
    "French",
}

SUPPORTED_LEVELS = {
    "Japanese": {"N5", "N4"},
    "Spanish": {"A1"},
    "French": {"A1"},
}

JAPANESE_WRITING_FIELDS = (
    "kanji",
    "hiragana",
    "romaji",
    "katakana",
)


# ============================================================
# VALIDATION RESULT
# ============================================================

@dataclass
class ValidationResult:
    """
    Represents the result of a validation operation.

    valid:
        True when no validation errors were found.

    errors:
        A list of human-readable validation messages.

    warnings:
        Non-blocking messages that may be useful to the user.
    """

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

    def add_error(self, message: str) -> None:
        """Add one validation error and mark the result as invalid."""
        if message:
            self.errors.append(message)
        self.valid = False

    def add_warning(self, message: str) -> None:
        """Add a non-blocking validation warning."""
        if message:
            self.warnings.append(message)


# ============================================================
# TEXT VALIDATION
# ============================================================

def validate_required_text(
    value: object,
    field_name: str,
    max_length: Optional[int] = None,
) -> ValidationResult:
    """
    Validate a required text field.

    Rejects:
    - None
    - non-string values
    - empty strings
    - whitespace-only strings
    - strings longer than max_length when supplied
    """
    result = ValidationResult(valid=True)

    if value is None:
        result.add_error(f"{field_name} is required.")
        return result

    if not isinstance(value, str):
        result.add_error(f"{field_name} must be text.")
        return result

    if not value.strip():
        result.add_error(f"{field_name} cannot be empty.")

    if max_length is not None and len(value.strip()) > max_length:
        result.add_error(
            f"{field_name} must be {max_length} characters or fewer."
        )

    return result


def validate_optional_text(
    value: object,
    field_name: str,
    max_length: Optional[int] = None,
) -> ValidationResult:
    """Validate an optional text field."""
    result = ValidationResult(valid=True)

    if value is None or value == "":
        return result

    if not isinstance(value, str):
        result.add_error(f"{field_name} must be text when provided.")
        return result

    if max_length is not None and len(value.strip()) > max_length:
        result.add_error(
            f"{field_name} must be {max_length} characters or fewer."
        )

    return result


def validate_non_empty_text(value: object, field_name: str) -> bool:
    """Return True when value is a non-empty string."""
    return validate_required_text(value, field_name).valid


# ============================================================
# LANGUAGE / LEVEL VALIDATION
# ============================================================

def validate_language(language: object) -> ValidationResult:
    """Validate a supported ZenKi language."""
    result = validate_required_text(language, "Language")

    if not result.valid:
        return result

    if language not in SUPPORTED_LANGUAGES:
        result.add_error(
            f"Unsupported language '{language}'. "
            f"Choose one of: {', '.join(sorted(SUPPORTED_LANGUAGES))}."
        )

    return result


def validate_level(
    language: object,
    level: object,
) -> ValidationResult:
    """Validate that a level belongs to the selected language."""
    result = ValidationResult(valid=True)

    language_result = validate_language(language)

    for error in language_result.errors:
        result.add_error(error)

    if not language_result.valid:
        return result

    level_result = validate_required_text(level, "Level")

    for error in level_result.errors:
        result.add_error(error)

    if not level_result.valid:
        return result

    allowed_levels = SUPPORTED_LEVELS[language]

    if level not in allowed_levels:
        result.add_error(
            f"Level '{level}' is not available for {language}. "
            f"Choose one of: {', '.join(sorted(allowed_levels))}."
        )

    return result


# ============================================================
# PRACTICE SESSION VALIDATION
# ============================================================

def validate_practice_size(size: object) -> ValidationResult:
    """Validate the allowed practice session sizes: 10, 20 or 25."""
    result = ValidationResult(valid=True)

    if isinstance(size, bool) or not isinstance(size, int):
        result.add_error("Practice size must be an integer.")
        return result

    if size not in ALLOWED_SESSION_SIZES:
        allowed = ", ".join(str(item) for item in ALLOWED_SESSION_SIZES)
        result.add_error(
            f"Practice size must be one of: {allowed}."
        )

    return result


def is_valid_practice_size(size: object) -> bool:
    """Return True when size is a supported practice-session size."""
    return validate_practice_size(size).valid


# ============================================================
# RATING VALIDATION
# ============================================================

def validate_rating(rating: object) -> ValidationResult:
    """Validate Again, Good, or Easy."""
    result = ValidationResult(valid=True)

    if isinstance(rating, Rating):
        return result

    if not isinstance(rating, str):
        result.add_error(
            "Rating must be 'again', 'good', or 'easy'."
        )
        return result

    normalized = rating.strip().lower()

    allowed = {item.value for item in Rating}

    if normalized not in allowed:
        result.add_error(
            f"Invalid rating '{rating}'. "
            f"Choose one of: {', '.join(sorted(allowed))}."
        )

    return result


def is_valid_rating(rating: object) -> bool:
    """Return True when rating is valid."""
    return validate_rating(rating).valid


# ============================================================
# LEITNER BOX VALIDATION
# ============================================================

def validate_leitner_box(box: object) -> ValidationResult:
    """Validate a Leitner box number from 1 through 5."""
    result = ValidationResult(valid=True)

    if isinstance(box, bool) or not isinstance(box, int):
        result.add_error("Leitner box must be an integer.")
        return result

    if not MIN_LEITNER_BOX <= box <= MAX_LEITNER_BOX:
        result.add_error(
            f"Leitner box must be between "
            f"{MIN_LEITNER_BOX} and {MAX_LEITNER_BOX}."
        )

    return result


# ============================================================
# JAPANESE CARD VALIDATION
# ============================================================

def _contains_katakana(text: str) -> bool:
    """
    Return True when text contains at least one Katakana character.

    Unicode block U+30A0-U+30FF covers the main Katakana block.
    """
    return any("\u30A0" <= character <= "\u30FF" for character in text)


def _contains_hiragana(text: str) -> bool:
    """Return True when text contains at least one Hiragana character."""
    return any("\u3040" <= character <= "\u309F" for character in text)


def validate_japanese_writing(
    card: Card,
) -> ValidationResult:
    """
    Validate Japanese writing fields.

    The validation is intentionally practical rather than strict:
    - Japanese cards should have a Hiragana reading.
    - Romaji should be present for the learning display.
    - Kanji is optional because some beginner words are normally written
      only in Hiragana.
    - Katakana is optional and should only be populated when applicable.
    """
    result = ValidationResult(valid=True)

    if not card.is_japanese:
        result.add_error(
            "Japanese writing validation can only be used with Japanese cards."
        )
        return result

    if not card.hiragana.strip():
        result.add_warning(
            f"Card '{card.card_id}' has no Hiragana field."
        )
    elif not _contains_hiragana(card.hiragana):
        result.add_warning(
            f"Card '{card.card_id}' Hiragana field does not appear to contain "
            "Hiragana characters."
        )

    if not card.romaji.strip():
        result.add_error(
            f"Japanese card '{card.card_id}' must include Romaji."
        )

    if card.katakana.strip() and not _contains_katakana(card.katakana):
        result.add_warning(
            f"Card '{card.card_id}' has a Katakana field, but it does not "
            "appear to contain Katakana characters."
        )

    return result


# ============================================================
# CARD VALIDATION
# ============================================================

def validate_card(card: object) -> ValidationResult:
    """
    Validate one Card object against ZenKi's application rules.

    This complements the structural checks already performed by
    Card.__post_init__ in models.py.
    """
    result = ValidationResult(valid=True)

    if not isinstance(card, Card):
        result.add_error("Expected a Card object.")
        return result

    required_fields = {
        "Card ID": card.card_id,
        "Language": card.language,
        "Level": card.level,
        "Front": card.front,
        "Meaning": card.meaning,
        "Example": card.example,
    }

    for field_name, value in required_fields.items():
        field_result = validate_required_text(value, field_name)
        for error in field_result.errors:
            result.add_error(error)

    language_result = validate_language(card.language)
    for error in language_result.errors:
        result.add_error(error)

    level_result = validate_level(card.language, card.level)
    for error in level_result.errors:
        result.add_error(error)

    box_result = validate_leitner_box(card.box)
    for error in box_result.errors:
        result.add_error(error)

    if card.review_count < 0:
        result.add_error("Review count cannot be negative.")

    if card.correct_count < 0:
        result.add_error("Correct count cannot be negative.")

    if card.again_count < 0:
        result.add_error("Again count cannot be negative.")

    if card.correct_count > card.review_count:
        result.add_error(
            "Correct count cannot exceed review count."
        )

    if card.again_count > card.review_count:
        result.add_error(
            "Again count cannot exceed review count."
        )

    if card.last_rating is not None:
        rating_result = validate_rating(card.last_rating)
        for error in rating_result.errors:
            result.add_error(error)

    if card.is_japanese:
        japanese_result = validate_japanese_writing(card)

        for error in japanese_result.errors:
            result.add_error(error)

        for warning in japanese_result.warnings:
            result.add_warning(warning)

    return result


def validate_cards(cards: Iterable[object]) -> ValidationResult:
    """
    Validate a collection of cards.

    Also checks for duplicate card IDs.
    """
    result = ValidationResult(valid=True)
    seen_ids = set()

    try:
        card_list = list(cards)
    except TypeError:
        result.add_error("Cards must be an iterable collection.")
        return result

    if not card_list:
        result.add_error("Card collection cannot be empty.")
        return result

    for index, card in enumerate(card_list, start=1):
        card_result = validate_card(card)

        for error in card_result.errors:
            result.add_error(f"Card {index}: {error}")

        for warning in card_result.warnings:
            result.add_warning(f"Card {index}: {warning}")

        if isinstance(card, Card):
            if card.card_id in seen_ids:
                result.add_error(
                    f"Duplicate card ID found: '{card.card_id}'."
                )
            seen_ids.add(card.card_id)

    return result


# ============================================================
# DECK VALIDATION
# ============================================================

def validate_deck(
    deck: object,
    require_fifty_cards: bool = False,
) -> ValidationResult:
    """
    Validate a Deck object.

    require_fifty_cards:
        When True, enforce the planned 50-card source-deck size.
        The default stays False so preview/testing decks can be used
        while the project is still being developed.
    """
    result = ValidationResult(valid=True)

    if not isinstance(deck, Deck):
        result.add_error("Expected a Deck object.")
        return result

    for field_name, value in {
        "Deck name": deck.name,
        "Language": deck.language,
        "Level": deck.level,
    }.items():
        field_result = validate_required_text(value, field_name)
        for error in field_result.errors:
            result.add_error(error)

    language_result = validate_language(deck.language)
    for error in language_result.errors:
        result.add_error(error)

    level_result = validate_level(deck.language, deck.level)
    for error in level_result.errors:
        result.add_error(error)

    if require_fifty_cards and len(deck.cards) != 50:
        result.add_error(
            f"{deck.name} must contain exactly 50 cards; "
            f"found {len(deck.cards)}."
        )

    card_result = validate_cards(deck.cards)

    for error in card_result.errors:
        result.add_error(error)

    for warning in card_result.warnings:
        result.add_warning(warning)

    # Confirm all cards match the deck metadata.
    for card in deck.cards:
        if isinstance(card, Card):
            if card.language != deck.language:
                result.add_error(
                    f"Card '{card.card_id}' language does not match "
                    f"deck language '{deck.language}'."
                )

            if card.level != deck.level:
                result.add_error(
                    f"Card '{card.card_id}' level does not match "
                    f"deck level '{deck.level}'."
                )

    return result


def validate_all_decks(
    decks: Mapping[str, Deck] | Iterable[Deck],
    require_fifty_cards: bool = False,
) -> ValidationResult:
    """Validate multiple decks and ensure deck keys are unique."""
    result = ValidationResult(valid=True)

    if isinstance(decks, Mapping):
        deck_list = list(decks.values())
    else:
        try:
            deck_list = list(decks)
        except TypeError:
            result.add_error("Decks must be an iterable collection.")
            return result

    if not deck_list:
        result.add_error("Deck collection cannot be empty.")
        return result

    seen_deck_keys = set()

    for index, deck in enumerate(deck_list, start=1):
        deck_result = validate_deck(
            deck,
            require_fifty_cards=require_fifty_cards,
        )

        for error in deck_result.errors:
            result.add_error(f"Deck {index}: {error}")

        for warning in deck_result.warnings:
            result.add_warning(f"Deck {index}: {warning}")

        if isinstance(deck, Deck):
            key = (deck.language, deck.level)

            if key in seen_deck_keys:
                result.add_error(
                    f"Duplicate deck detected: {deck.language} {deck.level}."
                )

            seen_deck_keys.add(key)

    return result


# ============================================================
# SESSION SELECTION VALIDATION
# ============================================================

def validate_session_selection(
    deck: Deck,
    practice_size: object,
    selected_cards: Sequence[Card],
) -> ValidationResult:
    """
    Validate the cards selected for one study session.

    Rules:
    - practice size must be 10, 20, or 25
    - selected count must equal practice size
    - selected card IDs must be unique
    - every selected card must belong to the deck
    """
    result = ValidationResult(valid=True)

    if not isinstance(deck, Deck):
        result.add_error("A valid Deck object is required.")
        return result

    size_result = validate_practice_size(practice_size)
    for error in size_result.errors:
        result.add_error(error)

    if not size_result.valid:
        return result

    try:
        cards = list(selected_cards)
    except TypeError:
        result.add_error("Selected cards must be a sequence.")
        return result

    if len(cards) != practice_size:
        result.add_error(
            f"Exactly {practice_size} cards must be selected; "
            f"found {len(cards)}."
        )

    deck_ids = {card.card_id for card in deck.cards}
    selected_ids = []

    for card in cards:
        if not isinstance(card, Card):
            result.add_error("Every selected item must be a Card object.")
            continue

        selected_ids.append(card.card_id)

        if card.card_id not in deck_ids:
            result.add_error(
                f"Card '{card.card_id}' does not belong to the selected deck."
            )

    if len(selected_ids) != len(set(selected_ids)):
        result.add_error("A study session cannot contain duplicate cards.")

    return result


# ============================================================
# CONVENIENCE HELPERS
# ============================================================

def ensure_valid(result: ValidationResult) -> None:
    """
    Raise ValueError when a validation result contains errors.

    Useful for non-UI application code that needs fail-fast behavior.
    Warnings do not cause an exception.
    """
    if not result.valid:
        raise ValueError("; ".join(result.errors))


def validate_required_text_or_raise(
    value: object,
    field_name: str,
    max_length: Optional[int] = None,
) -> str:
    """
    Validate text and return its stripped form.

    Raises:
        ValueError: when validation fails.
    """
    result = validate_required_text(
        value,
        field_name,
        max_length=max_length,
    )
    ensure_valid(result)
    return value.strip()


__all__ = [
    "JAPANESE_WRITING_FIELDS",
    "SUPPORTED_LANGUAGES",
    "SUPPORTED_LEVELS",
    "ValidationResult",
    "ensure_valid",
    "is_valid_practice_size",
    "is_valid_rating",
    "validate_all_decks",
    "validate_card",
    "validate_cards",
    "validate_deck",
    "validate_japanese_writing",
    "validate_language",
    "validate_level",
    "validate_leitner_box",
    "validate_non_empty_text",
    "validate_optional_text",
    "validate_practice_size",
    "validate_rating",
    "validate_required_text",
    "validate_required_text_or_raise",
    "validate_session_selection",
]
