"""
ZenKi Trainer Package
=====================

Reusable backend components for the ZenKi language spaced-repetition
flashcard trainer.

The package currently exposes four backend areas:

- models.py      -> Card, Deck, Session, Rating and Leitner rules
- storage.py     -> JSON/file storage and CSV export
- validators.py  -> input and data validation
- analysis.py    -> NumPy/Pandas analytics

Streamlit presentation and application routing remain in main.py.
"""

# ============================================================
# PACKAGE METADATA
# ============================================================

__title__ = "ZenKi Trainer"
__version__ = "0.2.0"
__author__ = "ZenKi Project"


# ============================================================
# CORE MODELS
# ============================================================

from .models import (
    ALLOWED_SESSION_SIZES,
    MAX_AGAIN_RETRIES,
    MAX_LEITNER_BOX,
    MIN_LEITNER_BOX,
    Card,
    Deck,
    Rating,
    Session,
)


# ============================================================
# STORAGE
# ============================================================

from .storage import (
    DEFAULT_DATA_DIR,
    SESSION_HISTORY_FILENAME,
    CorruptJSONError,
    DeckFileNotFoundError,
    EmptyDeckFileError,
    InvalidDeckDataError,
    StorageError,
    deck_exists,
    deck_from_dict,
    deck_to_dict,
    export_deck_to_csv,
    get_data_directory,
    get_deck_path,
    get_session_history_path,
    load_session_history,
    save_session_history,
    append_session_history,
    list_deck_files,
    load_deck,
    save_deck,
    save_decks,
    validate_deck_file,
)


# ============================================================
# VALIDATION
# ============================================================

from .validators import (
    JAPANESE_WRITING_FIELDS,
    SUPPORTED_LANGUAGES,
    SUPPORTED_LEVELS,
    ValidationResult,
    ensure_valid,
    is_valid_practice_size,
    is_valid_rating,
    validate_all_decks,
    validate_card,
    validate_cards,
    validate_deck,
    validate_japanese_writing,
    validate_language,
    validate_level,
    validate_leitner_box,
    validate_non_empty_text,
    validate_optional_text,
    validate_practice_size,
    validate_rating,
    validate_required_text,
    validate_required_text_or_raise,
    validate_session_selection,
)


# ============================================================
# ANALYSIS
# ============================================================

from .analysis import (
    average_card_accuracy,
    box_distribution,
    box_distribution_dataframe,
    calculate_score,
    card_accuracy,
    card_accuracy_statistics,
    cards_to_dataframe,
    deck_card_dataframe,
    deck_summary,
    deck_summary_dataframe,
    get_new_cards,
    get_weak_cards,
    language_summary,
    numerical_statistics,
    rating_counts,
    rating_counts_from_session,
    rating_dataframe,
    score_label,
    session_accuracy,
    session_summary,
    session_summary_dataframe,
    weighted_accuracy,
    weak_cards_dataframe,
)


# ============================================================
# PUBLIC PACKAGE API
# ============================================================

__all__ = [
    # Package metadata
    "__title__",
    "__version__",
    "__author__",

    # Models / OOP
    "ALLOWED_SESSION_SIZES",
    "MAX_AGAIN_RETRIES",
    "MAX_LEITNER_BOX",
    "MIN_LEITNER_BOX",
    "Card",
    "Deck",
    "Rating",
    "Session",

    # Storage / JSON / file processing
    "DEFAULT_DATA_DIR",
    "SESSION_HISTORY_FILENAME",
    "StorageError",
    "DeckFileNotFoundError",
    "EmptyDeckFileError",
    "CorruptJSONError",
    "InvalidDeckDataError",
    "deck_exists",
    "deck_from_dict",
    "deck_to_dict",
    "export_deck_to_csv",
    "get_data_directory",
    "get_deck_path",
    "get_session_history_path",
    "load_session_history",
    "save_session_history",
    "append_session_history",
    "list_deck_files",
    "load_deck",
    "save_deck",
    "save_decks",
    "validate_deck_file",

    # Validation
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

    # Analysis / NumPy + Pandas
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
