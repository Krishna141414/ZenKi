"""
ZenKi Storage Module
====================

Handles JSON file storage for ZenKi decks and learner progress.

Responsibilities:
- Save a Deck object to JSON.
- Load a Deck object from JSON.
- Validate basic file/content conditions.
- Handle missing, empty, invalid, and corrupt JSON safely.
- Save JSON atomically so an interrupted write is less likely to damage a deck.
- Export deck cards/progress to CSV when needed.

The module contains no Streamlit/UI code.
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Dict, Iterable, List

from .models import Card, Deck


DEFAULT_DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SESSION_HISTORY_FILENAME = "session_history.json"


# ============================================================
# CUSTOM EXCEPTIONS
# ============================================================

class StorageError(Exception):
    """Base exception for ZenKi storage errors."""


class DeckFileNotFoundError(StorageError):
    """Raised when a requested deck file does not exist."""


class EmptyDeckFileError(StorageError):
    """Raised when a deck file exists but contains no JSON data."""


class CorruptJSONError(StorageError):
    """Raised when a deck file contains invalid JSON."""


class InvalidDeckDataError(StorageError):
    """Raised when valid JSON does not describe a valid Deck."""


# ============================================================
# PATH HELPERS
# ============================================================

def get_data_directory(data_dir: str | Path | None = None) -> Path:
    """Return the data directory and create it when necessary."""
    directory = Path(data_dir) if data_dir is not None else DEFAULT_DATA_DIR
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def get_deck_path(
    filename: str,
    data_dir: str | Path | None = None,
) -> Path:
    """
    Build a safe path for a deck file.

    The storage layer only accepts JSON filenames so callers cannot
    accidentally request a different file type.
    """
    clean_name = Path(filename).name

    if not clean_name:
        raise ValueError("Deck filename cannot be empty.")

    if not clean_name.lower().endswith(".json"):
        raise ValueError("Deck filename must have a .json extension.")

    return get_data_directory(data_dir) / clean_name


# ============================================================
# JSON SERIALIZATION
# ============================================================

def deck_to_dict(deck: Deck) -> Dict[str, Any]:
    """Convert a Deck object into JSON-friendly dictionary data."""
    if not isinstance(deck, Deck):
        raise TypeError("deck_to_dict expects a Deck object.")

    return deck.to_dict()


def deck_from_dict(data: Dict[str, Any]) -> Deck:
    """Convert dictionary data into a validated Deck object."""
    if not isinstance(data, dict):
        raise InvalidDeckDataError("Deck JSON root must be an object.")

    try:
        return Deck.from_dict(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise InvalidDeckDataError(
            f"JSON contains invalid deck data: {exc}"
        ) from exc


# ============================================================
# SAVE / LOAD
# ============================================================

def save_deck(
    deck: Deck,
    filename: str,
    data_dir: str | Path | None = None,
    indent: int = 2,
) -> Path:
    """
    Save a Deck to JSON and return the created file path.

    The write uses a temporary file followed by os.replace() so the
    destination is updated atomically on the same filesystem.
    """
    path = get_deck_path(filename, data_dir)
    payload = deck_to_dict(deck)

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(
                payload,
                temporary,
                ensure_ascii=False,
                indent=indent,
            )
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, path)

    except (OSError, TypeError, ValueError) as exc:
        if "temporary_path" in locals():
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass

        raise StorageError(
            f"Could not save deck to '{path}': {exc}"
        ) from exc

    return path


def load_deck(
    filename: str,
    data_dir: str | Path | None = None,
) -> Deck:
    """
    Load and validate a Deck from JSON.

    Raises a specific StorageError subtype for:
    - missing file
    - empty file
    - invalid/corrupt JSON
    - structurally invalid deck data
    """
    path = get_deck_path(filename, data_dir)

    if not path.exists():
        raise DeckFileNotFoundError(
            f"Deck file was not found: '{path}'."
        )

    if not path.is_file():
        raise DeckFileNotFoundError(
            f"Deck path is not a file: '{path}'."
        )

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageError(
            f"Could not read deck file '{path}': {exc}"
        ) from exc

    if not raw_text.strip():
        raise EmptyDeckFileError(
            f"Deck file is empty: '{path}'."
        )

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CorruptJSONError(
            f"Invalid JSON in '{path}' at line {exc.lineno}, "
            f"column {exc.colno}: {exc.msg}"
        ) from exc

    return deck_from_dict(data)


def save_decks(
    decks: Iterable[Deck],
    data_dir: str | Path | None = None,
) -> List[Path]:
    """
    Save multiple decks.

    The filename convention is:
        <language>_<level>.json

    Example:
        Japanese + N5 -> japanese_n5.json
    """
    saved_paths: List[Path] = []

    for deck in decks:
        filename = (
            f"{deck.language}_{deck.level}"
            .replace(" ", "_")
            .lower()
            + ".json"
        )
        saved_paths.append(
            save_deck(deck, filename, data_dir=data_dir)
        )

    return saved_paths


# ============================================================
# DECK INSPECTION
# ============================================================

def deck_exists(
    filename: str,
    data_dir: str | Path | None = None,
) -> bool:
    """Return True when the requested JSON deck file exists."""
    return get_deck_path(filename, data_dir).is_file()


def list_deck_files(
    data_dir: str | Path | None = None,
) -> List[Path]:
    """Return JSON deck files in the data directory, sorted by name."""
    directory = get_data_directory(data_dir)
    return sorted(
        path
        for path in directory.glob("*.json")
        if path.name != SESSION_HISTORY_FILENAME
    )


def validate_deck_file(
    filename: str,
    data_dir: str | Path | None = None,
) -> bool:
    """
    Load a deck to validate both JSON syntax and Deck structure.

    Returns True when valid. StorageError is raised otherwise.
    """
    load_deck(filename, data_dir=data_dir)
    return True


# ============================================================
# SESSION HISTORY
# ============================================================

def get_session_history_path(
    data_dir: str | Path | None = None,
) -> Path:
    """Return the JSON path used for completed study-session history."""
    return get_data_directory(data_dir) / SESSION_HISTORY_FILENAME


def load_session_history(
    data_dir: str | Path | None = None,
    limit: int | None = 50,
) -> List[Dict[str, Any]]:
    """
    Load completed session summaries.

    A missing history file is treated as an empty history.  Invalid JSON
    raises CorruptJSONError so the UI can report the problem safely.
    """
    if limit is not None and limit <= 0:
        raise ValueError("History limit must be greater than zero.")

    path = get_session_history_path(data_dir)

    if not path.exists():
        return []

    if not path.is_file():
        raise StorageError(f"Session history path is not a file: '{path}'.")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise StorageError(
            f"Could not read session history '{path}': {exc}"
        ) from exc

    if not raw_text.strip():
        return []

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise CorruptJSONError(
            f"Invalid JSON in session history '{path}' at line "
            f"{exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc

    if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
        raise StorageError(
            "Session history JSON must contain a list of objects."
        )

    return data[-limit:] if limit is not None else data


def save_session_history(
    history: Iterable[Dict[str, Any]],
    data_dir: str | Path | None = None,
    limit: int | None = 50,
    indent: int = 2,
) -> Path:
    """Atomically save completed session summaries to JSON."""
    if limit is not None and limit <= 0:
        raise ValueError("History limit must be greater than zero.")

    entries = list(history)
    if any(not isinstance(item, dict) for item in entries):
        raise TypeError("Every session-history entry must be a dictionary.")

    if limit is not None:
        entries = entries[-limit:]

    path = get_session_history_path(data_dir)
    temporary_path = None

    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".session_history_",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(entries, temporary, ensure_ascii=False, indent=indent)
            temporary.write("\n")
            temporary.flush()
            os.fsync(temporary.fileno())

        os.replace(temporary_path, path)
    except (OSError, TypeError, ValueError) as exc:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass
        raise StorageError(
            f"Could not save session history to '{path}': {exc}"
        ) from exc

    return path


def append_session_history(
    entry: Dict[str, Any],
    data_dir: str | Path | None = None,
    limit: int | None = 50,
) -> List[Dict[str, Any]]:
    """Append one completed session and return the retained history."""
    if not isinstance(entry, dict):
        raise TypeError("Session-history entry must be a dictionary.")

    history = load_session_history(data_dir=data_dir, limit=None)
    history.append(entry)
    save_session_history(history, data_dir=data_dir, limit=limit)
    return history[-limit:] if limit is not None else history


# ============================================================
# CSV EXPORT
# ============================================================

def export_deck_to_csv(
    deck: Deck,
    filename: str | Path,
    include_progress: bool = True,
) -> Path:
    """
    Export deck cards to CSV.

    CSV is optional in the ZenKi project but useful for analysis,
    backup, and inspection outside the application.
    """
    if not isinstance(deck, Deck):
        raise TypeError("export_deck_to_csv expects a Deck object.")

    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
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
    ]

    if include_progress:
        fieldnames.extend(
            [
                "box",
                "review_count",
                "correct_count",
                "again_count",
                "last_rating",
                "last_reviewed",
            ]
        )

    try:
        with path.open(
            "w",
            encoding="utf-8-sig",
            newline="",
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=fieldnames,
            )
            writer.writeheader()

            for card in deck.cards:
                row = card.to_dict()
                writer.writerow(
                    {field: row.get(field, "") for field in fieldnames}
                )

    except OSError as exc:
        raise StorageError(
            f"Could not export deck to '{path}': {exc}"
        ) from exc

    return path


__all__ = [
    "CorruptJSONError",
    "DeckFileNotFoundError",
    "EmptyDeckFileError",
    "InvalidDeckDataError",
    "StorageError",
    "DEFAULT_DATA_DIR",
    "SESSION_HISTORY_FILENAME",
    "deck_from_dict",
    "deck_to_dict",
    "deck_exists",
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
]
