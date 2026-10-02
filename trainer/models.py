"""
ZenKi Trainer Models
====================

This module contains the core domain objects used by ZenKi:

- Card    -> one flashcard and its learning progress
- Deck    -> a collection of related cards
- Session -> one practice session and its results

The module intentionally contains no Streamlit code and no file I/O.
Those responsibilities belong to the UI and storage modules respectively.

The classes are designed to support:
- Japanese cards with Kanji, Hiragana, Romaji and optional Katakana
- Spanish and French vocabulary cards
- 50-card source decks
- 10 / 20 / 25-card practice sessions
- Leitner box progression
- Again / Good / Easy ratings
- Immediate repetition of difficult cards
- JSON-friendly dictionary conversion for the future storage module
"""

from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Deque, Dict, Iterable, List, Optional, Sequence


# ============================================================
# CONSTANTS
# ============================================================

MIN_LEITNER_BOX = 1
MAX_LEITNER_BOX = 5
ALLOWED_SESSION_SIZES = (10, 20, 25)
MAX_AGAIN_RETRIES = 2


# ============================================================
# ENUMS
# ============================================================

class Rating(str, Enum):
    """Allowed learner ratings for a reviewed flashcard."""

    AGAIN = "again"
    GOOD = "good"
    EASY = "easy"


# ============================================================
# CARD
# ============================================================

@dataclass
class Card:
    """
    Represents one flashcard and its learning state.

    Japanese cards can use:
        kanji, hiragana, romaji, katakana

    Spanish/French cards can leave Japanese-specific fields empty
    and use front + meaning + example + translation.

    The 'front' field is the primary text shown to the learner.
    """

    card_id: str
    language: str
    level: str
    front: str
    meaning: str
    example: str
    translation: str = ""
    reading: str = ""
    kanji: str = ""
    hiragana: str = ""
    romaji: str = ""
    katakana: str = ""

    box: int = MIN_LEITNER_BOX
    review_count: int = 0
    correct_count: int = 0
    again_count: int = 0
    last_rating: Optional[str] = None
    last_reviewed: Optional[str] = None

    def __post_init__(self) -> None:
        """Validate and normalize card data after creation."""
        self.card_id = self.card_id.strip()
        self.language = self.language.strip()
        self.level = self.level.strip()
        self.front = self.front.strip()
        self.meaning = self.meaning.strip()
        self.example = self.example.strip()
        self.translation = self.translation.strip()
        self.reading = self.reading.strip()
        self.kanji = self.kanji.strip()
        self.hiragana = self.hiragana.strip()
        self.romaji = self.romaji.strip()
        self.katakana = self.katakana.strip()

        if not self.card_id:
            raise ValueError("Card ID cannot be empty.")

        if not self.language:
            raise ValueError("Card language cannot be empty.")

        if not self.level:
            raise ValueError("Card level cannot be empty.")

        if not self.front:
            raise ValueError("Card front cannot be empty.")

        if not self.meaning:
            raise ValueError("Card meaning cannot be empty.")

        if not self.example:
            raise ValueError("Card example cannot be empty.")

        self._validate_box(self.box)

        if self.review_count < 0:
            raise ValueError("Review count cannot be negative.")

        if self.correct_count < 0:
            raise ValueError("Correct count cannot be negative.")

        if self.again_count < 0:
            raise ValueError("Again count cannot be negative.")

        if self.correct_count > self.review_count:
            raise ValueError("Correct count cannot exceed review count.")

        if self.again_count > self.review_count:
            raise ValueError("Again count cannot exceed review count.")

        if self.last_rating is not None:
            self.last_rating = self._normalize_rating(self.last_rating)

    # --------------------------------------------------------
    # VALIDATION HELPERS
    # --------------------------------------------------------

    @staticmethod
    def _validate_box(box: int) -> None:
        """Validate a Leitner box number."""
        if not isinstance(box, int):
            raise TypeError("Leitner box must be an integer.")

        if not MIN_LEITNER_BOX <= box <= MAX_LEITNER_BOX:
            raise ValueError(
                f"Leitner box must be between "
                f"{MIN_LEITNER_BOX} and {MAX_LEITNER_BOX}."
            )

    @staticmethod
    def _normalize_rating(rating: str | Rating) -> str:
        """Convert a rating into its standard lowercase string form."""
        if isinstance(rating, Rating):
            return rating.value

        normalized = str(rating).strip().lower()

        if normalized not in {item.value for item in Rating}:
            raise ValueError(
                f"Invalid rating '{rating}'. "
                f"Expected: again, good, or easy."
            )

        return normalized

    # --------------------------------------------------------
    # JAPANESE DISPLAY DATA
    # --------------------------------------------------------

    @property
    def is_japanese(self) -> bool:
        """Return True when this card belongs to a Japanese deck."""
        return self.language.strip().lower() == "japanese"

    def japanese_writing(self) -> Dict[str, str]:
        """
        Return Japanese writing forms in learning order.

        Order:
            Kanji -> Hiragana -> Romaji -> Katakana (when applicable)

        Empty fields are omitted.
        """
        if not self.is_japanese:
            return {}

        result: Dict[str, str] = {}

        if self.kanji:
            result["kanji"] = self.kanji

        if self.hiragana:
            result["hiragana"] = self.hiragana

        if self.romaji:
            result["romaji"] = self.romaji

        if self.katakana:
            result["katakana"] = self.katakana

        return result

    # --------------------------------------------------------
    # LEITNER BEHAVIOR
    # --------------------------------------------------------

    def mark_again(self) -> None:
        """
        Apply the Again rating.

        Again returns the card to Box 1 and records the failed review.
        Immediate repetition inside a Session is handled by Session.
        """
        self.box = MIN_LEITNER_BOX
        self.review_count += 1
        self.again_count += 1
        self.last_rating = Rating.AGAIN.value
        self.last_reviewed = datetime.now().isoformat(timespec="seconds")

    def mark_good(self) -> None:
        """
        Apply the Good rating.

        Good advances the card by one Leitner box, up to Box 5.
        """
        self.box = min(MAX_LEITNER_BOX, self.box + 1)
        self.review_count += 1
        self.correct_count += 1
        self.last_rating = Rating.GOOD.value
        self.last_reviewed = datetime.now().isoformat(timespec="seconds")

    def mark_easy(self) -> None:
        """
        Apply the Easy rating.

        Easy advances the card by two Leitner boxes, up to Box 5.
        """
        self.box = min(MAX_LEITNER_BOX, self.box + 2)
        self.review_count += 1
        self.correct_count += 1
        self.last_rating = Rating.EASY.value
        self.last_reviewed = datetime.now().isoformat(timespec="seconds")

    def apply_rating(self, rating: str | Rating) -> None:
        """Apply one of the supported learner ratings."""
        normalized = self._normalize_rating(rating)

        if normalized == Rating.AGAIN.value:
            self.mark_again()
        elif normalized == Rating.GOOD.value:
            self.mark_good()
        else:
            self.mark_easy()

    @property
    def accuracy(self) -> float:
        """Return the card's historical accuracy as a percentage."""
        if self.review_count == 0:
            return 0.0

        return round((self.correct_count / self.review_count) * 100, 2)

    @property
    def is_new(self) -> bool:
        """Return True when the card has never been reviewed."""
        return self.review_count == 0

    @property
    def is_weak(self) -> bool:
        """
        Return True when the card needs extra attention.

        A card is considered weak when it is in Box 1 or has a
        historical accuracy below 60%.
        """
        return self.box == MIN_LEITNER_BOX or (
            self.review_count > 0 and self.accuracy < 60
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the Card into JSON-friendly dictionary data."""
        return {
            "id": self.card_id,
            "language": self.language,
            "level": self.level,
            "front": self.front,
            "meaning": self.meaning,
            "example": self.example,
            "translation": self.translation,
            "reading": self.reading,
            "kanji": self.kanji,
            "hiragana": self.hiragana,
            "romaji": self.romaji,
            "katakana": self.katakana,
            "box": self.box,
            "review_count": self.review_count,
            "correct_count": self.correct_count,
            "again_count": self.again_count,
            "last_rating": self.last_rating,
            "last_reviewed": self.last_reviewed,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Card":
        """Create a Card from dictionary data, ready for JSON loading."""
        if not isinstance(data, dict):
            raise TypeError("Card data must be a dictionary.")

        return cls(
            card_id=str(data.get("id", data.get("card_id", ""))),
            language=str(data.get("language", "")),
            level=str(data.get("level", "")),
            front=str(data.get("front", "")),
            meaning=str(data.get("meaning", "")),
            example=str(data.get("example", "")),
            translation=str(data.get("translation", "")),
            reading=str(data.get("reading", "")),
            kanji=str(data.get("kanji", "")),
            hiragana=str(data.get("hiragana", "")),
            romaji=str(data.get("romaji", "")),
            katakana=str(data.get("katakana", "")),
            box=int(data.get("box", MIN_LEITNER_BOX)),
            review_count=int(data.get("review_count", 0)),
            correct_count=int(data.get("correct_count", 0)),
            again_count=int(data.get("again_count", 0)),
            last_rating=data.get("last_rating"),
            last_reviewed=data.get("last_reviewed"),
        )


# ============================================================
# DECK
# ============================================================

@dataclass
class Deck:
    """
    Represents a language/level collection of flashcards.

    A final ZenKi deck is expected to contain 50 cards, while a
    Session may select only 10, 20, or 25 cards from that deck.
    """

    name: str
    language: str
    level: str
    cards: List[Card] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate deck metadata and card collection."""
        self.name = self.name.strip()
        self.language = self.language.strip()
        self.level = self.level.strip()

        if not self.name:
            raise ValueError("Deck name cannot be empty.")

        if not self.language:
            raise ValueError("Deck language cannot be empty.")

        if not self.level:
            raise ValueError("Deck level cannot be empty.")

        for card in self.cards:
            if not isinstance(card, Card):
                raise TypeError("Deck cards must be Card objects.")

    def add_card(self, card: Card) -> None:
        """Add one card to the deck while preventing duplicate IDs."""
        if not isinstance(card, Card):
            raise TypeError("Only Card objects can be added to a deck.")

        if any(existing.card_id == card.card_id for existing in self.cards):
            raise ValueError(
                f"A card with ID '{card.card_id}' already exists in this deck."
            )

        self.cards.append(card)

    def add_cards(self, cards: Iterable[Card]) -> None:
        """Add multiple cards using the same validation as add_card."""
        for card in cards:
            self.add_card(card)

    def remove_card(self, card_id: str) -> Card:
        """Remove and return a card by ID."""
        for index, card in enumerate(self.cards):
            if card.card_id == card_id:
                return self.cards.pop(index)

        raise KeyError(f"Card '{card_id}' was not found in the deck.")

    def get_card(self, card_id: str) -> Card:
        """Return a card by ID."""
        for card in self.cards:
            if card.card_id == card_id:
                return card

        raise KeyError(f"Card '{card_id}' was not found in the deck.")

    def get_cards_by_box(self, box: int) -> List[Card]:
        """Return all cards belonging to a particular Leitner box."""
        Card._validate_box(box)
        return [card for card in self.cards if card.box == box]

    def get_new_cards(self) -> List[Card]:
        """Return cards that have never been reviewed."""
        return [card for card in self.cards if card.is_new]

    def get_weak_cards(self) -> List[Card]:
        """Return cards that need extra attention."""
        return [card for card in self.cards if card.is_weak]

    def get_due_cards(self) -> List[Card]:
        """
        Return cards that should receive attention first.

        At this model stage, cards in Box 1 are treated as due.
        Date-based scheduling will be handled more fully by the
        future storage/scheduling layer.
        """
        return self.get_cards_by_box(MIN_LEITNER_BOX)

    @property
    def card_count(self) -> int:
        """Return the total number of cards in the deck."""
        return len(self.cards)

    @property
    def is_full_deck(self) -> bool:
        """Return True when this deck has the planned 50 cards."""
        return self.card_count == 50

    def box_distribution(self) -> Dict[int, int]:
        """Return the number of cards in each Leitner box."""
        distribution = {box: 0 for box in range(1, MAX_LEITNER_BOX + 1)}

        for card in self.cards:
            distribution[card.box] += 1

        return distribution

    def accuracy(self) -> float:
        """Return the average historical accuracy of reviewed cards."""
        reviewed = [card for card in self.cards if card.review_count > 0]

        if not reviewed:
            return 0.0

        total_reviews = sum(card.review_count for card in reviewed)
        total_correct = sum(card.correct_count for card in reviewed)

        if total_reviews == 0:
            return 0.0

        return round((total_correct / total_reviews) * 100, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Convert the deck into JSON-friendly dictionary data."""
        return {
            "name": self.name,
            "language": self.language,
            "level": self.level,
            "cards": [card.to_dict() for card in self.cards],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Deck":
        """Create a Deck from dictionary data."""
        if not isinstance(data, dict):
            raise TypeError("Deck data must be a dictionary.")

        raw_cards = data.get("cards", [])

        if not isinstance(raw_cards, list):
            raise TypeError("Deck 'cards' must be a list.")

        deck = cls(
            name=str(data.get("name", "")),
            language=str(data.get("language", "")),
            level=str(data.get("level", "")),
        )

        for card_data in raw_cards:
            deck.add_card(Card.from_dict(card_data))

        return deck


# ============================================================
# SESSION
# ============================================================

@dataclass
class Session:
    """
    Represents one practice session.

    The Session is responsible for:
    - choosing a practice size of 10, 20 or 25
    - maintaining the current review queue
    - handling Again retries
    - recording Good / Easy / Again results
    - calculating session-level statistics

    Long-term persistence is intentionally not handled here.
    """

    deck: Deck
    practice_size: int

    queue: Deque[Card] = field(default_factory=deque, init=False)
    completed_cards: List[Card] = field(default_factory=list, init=False)
    rating_history: List[Dict[str, Any]] = field(default_factory=list, init=False)

    attempts: int = field(default=0, init=False)
    good_count: int = field(default=0, init=False)
    easy_count: int = field(default=0, init=False)
    again_count: int = field(default=0, init=False)

    _retry_counts: Counter[str] = field(
        default_factory=Counter, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """Validate session configuration."""
        if not isinstance(self.deck, Deck):
            raise TypeError("Session deck must be a Deck object.")

        if self.practice_size not in ALLOWED_SESSION_SIZES:
            raise ValueError(
                "Practice size must be one of: "
                + ", ".join(str(size) for size in ALLOWED_SESSION_SIZES)
                + "."
            )

        if self.deck.card_count < self.practice_size:
            raise ValueError(
                f"Deck contains {self.deck.card_count} cards, but "
                f"{self.practice_size} cards were requested."
            )

    # --------------------------------------------------------
    # SESSION START / QUEUE
    # --------------------------------------------------------

    def start(self, cards: Optional[Sequence[Card]] = None) -> None:
        """
        Start the session with a selected set of unique cards.

        If cards are supplied, they must belong to the deck and there
        must be exactly practice_size of them.

        Actual randomized/due-card selection can be performed by the
        UI or future scheduling logic before calling this method.
        """
        if cards is None:
            selected = list(self.deck.cards[: self.practice_size])
        else:
            selected = list(cards)

        self._validate_selected_cards(selected)

        self.queue = deque(selected)
        self.completed_cards = []
        self.rating_history = []
        self.attempts = 0
        self.good_count = 0
        self.easy_count = 0
        self.again_count = 0
        self._retry_counts.clear()

    def _validate_selected_cards(self, cards: Sequence[Card]) -> None:
        """Validate the cards selected for the session."""
        if len(cards) != self.practice_size:
            raise ValueError(
                f"Exactly {self.practice_size} cards must be selected."
            )

        ids = [card.card_id for card in cards]

        if len(set(ids)) != len(ids):
            raise ValueError("A session cannot contain duplicate cards.")

        deck_ids = {card.card_id for card in self.deck.cards}

        if any(card.card_id not in deck_ids for card in cards):
            raise ValueError("Every selected card must belong to the deck.")

    @property
    def current_card(self) -> Optional[Card]:
        """Return the next card in the queue, or None when empty."""
        return self.queue[0] if self.queue else None

    @property
    def is_started(self) -> bool:
        """Return True when the session currently has cards queued."""
        return bool(self.queue or self.completed_cards)

    @property
    def is_complete(self) -> bool:
        """Return True when all selected cards are finished."""
        return not self.queue

    @property
    def selected_count(self) -> int:
        """Return the number of original cards selected for the session."""
        return len(self.completed_cards) + self._unique_cards_remaining()

    def _unique_cards_remaining(self) -> int:
        """Count unique selected cards still present in the queue."""
        completed_ids = {card.card_id for card in self.completed_cards}
        return len(
            {
                card.card_id
                for card in self.queue
                if card.card_id not in completed_ids
            }
        )

    # --------------------------------------------------------
    # RATINGS
    # --------------------------------------------------------

    def rate_current_card(self, rating: str | Rating) -> Card:
        """
        Rate the current card and update session state.

        Again:
            - moves the card back to Box 1
            - requeues it for immediate repetition
            - allows a limited number of immediate retries

        Good:
            - advances one Leitner box
            - completes the card for this session

        Easy:
            - advances two Leitner boxes
            - completes the card for this session
        """
        card = self.current_card

        if card is None:
            raise RuntimeError("There is no current card to rate.")

        normalized = Card._normalize_rating(rating)

        if normalized == Rating.AGAIN.value:
            self._handle_again(card)
        elif normalized == Rating.GOOD.value:
            self._handle_good(card)
        else:
            self._handle_easy(card)

        return card

    def _handle_again(self, card: Card) -> None:
        """Handle an Again rating."""
        self.queue.popleft()

        card.mark_again()

        self.attempts += 1
        self.again_count += 1
        self._retry_counts[card.card_id] += 1

        self.rating_history.append(
            {
                "card_id": card.card_id,
                "rating": Rating.AGAIN.value,
                "box_after": card.box,
                "timestamp": card.last_reviewed,
            }
        )

        # Reinsert the card later in the queue to avoid showing it
        # immediately over and over again.
        if self._retry_counts[card.card_id] <= MAX_AGAIN_RETRIES:
            insert_position = min(2, len(self.queue))
            items = list(self.queue)
            items.insert(insert_position, card)
            self.queue = deque(items)
        else:
            # After the retry limit, consider the card completed for
            # this session. It remains in Box 1 and will be prioritized
            # again in a future study session.
            self.completed_cards.append(card)

    def _handle_good(self, card: Card) -> None:
        """Handle a Good rating."""
        self.queue.popleft()
        card.mark_good()

        self.attempts += 1
        self.good_count += 1
        self.completed_cards.append(card)

        self.rating_history.append(
            {
                "card_id": card.card_id,
                "rating": Rating.GOOD.value,
                "box_after": card.box,
                "timestamp": card.last_reviewed,
            }
        )

    def _handle_easy(self, card: Card) -> None:
        """Handle an Easy rating."""
        self.queue.popleft()
        card.mark_easy()

        self.attempts += 1
        self.easy_count += 1
        self.completed_cards.append(card)

        self.rating_history.append(
            {
                "card_id": card.card_id,
                "rating": Rating.EASY.value,
                "box_after": card.box,
                "timestamp": card.last_reviewed,
            }
        )

    # --------------------------------------------------------
    # SESSION STATISTICS
    # --------------------------------------------------------

    @property
    def total_ratings(self) -> int:
        """Return the total number of recorded ratings."""
        return self.good_count + self.easy_count + self.again_count

    @property
    def correct_count(self) -> int:
        """Return Good + Easy ratings."""
        return self.good_count + self.easy_count

    @property
    def accuracy(self) -> float:
        """
        Return session accuracy.

        Accuracy is based on the rating attempts:
            (Good + Easy) / total ratings * 100
        """
        if self.total_ratings == 0:
            return 0.0

        return round((self.correct_count / self.total_ratings) * 100, 2)

    def summary(self) -> Dict[str, Any]:
        """Return a compact summary suitable for UI/statistics modules."""
        return {
            "deck": self.deck.name,
            "language": self.deck.language,
            "level": self.deck.level,
            "selected_cards": self.practice_size,
            "good": self.good_count,
            "easy": self.easy_count,
            "again": self.again_count,
            "total_ratings": self.total_ratings,
            "accuracy": self.accuracy,
            "completed": len(self.completed_cards),
            "remaining": len(self.queue),
        }


# ============================================================
# MODULE EXPORTS
# ============================================================

__all__ = [
    "ALLOWED_SESSION_SIZES",
    "MAX_AGAIN_RETRIES",
    "MAX_LEITNER_BOX",
    "MIN_LEITNER_BOX",
    "Card",
    "Deck",
    "Rating",
    "Session",
]
