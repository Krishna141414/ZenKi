
"""
ZenKi
=====

Streamlit interface for the ZenKi language spaced-repetition flashcard trainer.

This file is the application/UI layer.  The reusable backend responsibilities
are intentionally delegated to the trainer package:

    trainer.models       -> Card, Deck, Session, Leitner behavior
    trainer.storage      -> JSON loading/saving and file operations
    trainer.validators   -> input and data validation
    trainer.analysis     -> NumPy/Pandas analytics

The language decks are stored as JSON files inside the project's data/ folder.
"""

from __future__ import annotations

import html
import random
import textwrap
from datetime import datetime
from pathlib import Path

import pandas as pd
from typing import Dict, List, Optional, Tuple

import streamlit as st

from trainer.analysis import (
    box_distribution_dataframe,
    cards_to_dataframe,
    deck_summary,
    get_weak_cards,
    session_summary,
    weak_cards_dataframe,
)
from trainer.models import (
    ALLOWED_SESSION_SIZES,
    Card,
    Deck,
    Session,
)
from trainer.storage import (
    CorruptJSONError,
    DeckFileNotFoundError,
    EmptyDeckFileError,
    InvalidDeckDataError,
    StorageError,
    load_deck,
    save_deck,
    load_session_history,
    append_session_history,
)
from trainer.validators import (
    validate_deck,
    validate_language,
    validate_level,
    validate_practice_size,
    validate_session_selection,
)


# ============================================================
# PAGE SETUP
# ============================================================

st.set_page_config(
    page_title="ZenKi",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# APPLICATION CONFIGURATION
# ============================================================

APP_NAME = "ZenKi"
PROJECT_ROOT = Path(__file__).resolve().parent
DATA_DIR = PROJECT_ROOT / "data"

DECK_CONFIG: Dict[str, Dict] = {
    "Japanese": {
        "flag": "🇯🇵",
        "levels": {
            "N5": {
                "file": "japanese_n5.json",
                "label": "N5 — Beginner",
                "description": (
                    "Everyday Japanese vocabulary with Kanji, Hiragana, "
                    "Romaji and useful example sentences."
                ),
            },
            "N4": {
                "file": "japanese_n4.json",
                "label": "N4 — Elementary",
                "description": (
                    "More advanced Japanese vocabulary with reading support "
                    "and Katakana where naturally applicable."
                ),
            },
        },
    },
    "Spanish": {
        "flag": "🇪🇸",
        "levels": {
            "A1": {
                "file": "spanish_a1.json",
                "label": "A1 — Beginner",
                "description": (
                    "Practical beginner vocabulary with simple contextual examples."
                ),
            },
        },
    },
    "French": {
        "flag": "🇫🇷",
        "levels": {
            "A1": {
                "file": "french_a1.json",
                "label": "A1 — Beginner",
                "description": (
                    "Practical beginner vocabulary with simple contextual examples."
                ),
            },
        },
    },
}

THEMES = {
    "Midnight Aurora": ("#111827", "#223047", "#8B82E8", "#67D6D0"),
    "Sakura Night": ("#1B1720", "#332536", "#D58BAA", "#E6AFC1"),
    "Ocean Focus": ("#0D1B1E", "#1B3A40", "#5CB9B1", "#78B7E8"),
}


# ============================================================
# VISUAL THEME
# ============================================================

def apply_theme(name: str) -> None:
    """Apply the selected ZenKi visual theme."""
    bg, surface, accent, accent2 = THEMES[name]

    st.markdown(
        f"""
        <style>
        :root {{
            --bg:{bg};
            --surface:{surface};
            --accent:{accent};
            --accent2:{accent2};
            --text:#F8FAFC;
            --muted:#C1CDDA;
            --border:#3A4A60;
            --soft-surface:rgba(255,255,255,.045);
        }}

        /* Remove Streamlit's unused top header strip. */
        [data-testid="stHeader"],
        [data-testid="stDecoration"] {{
            background:transparent !important;
        }}

        [data-testid="stHeader"],
        header[data-testid="stHeader"] {{
            display:none !important;
            height:0 !important;
            min-height:0 !important;
            padding:0 !important;
            margin:0 !important;
            border:0 !important;
            background:transparent !important;
        }}

        [data-testid="stDecoration"] {{
            display:none !important;
        }}

        [data-testid="stAppViewContainer"] > .main {{
            padding-top:0 !important;
        }}

        header {{
            background:transparent !important;
        }}

        .stApp {{
            background:
              radial-gradient(
                  circle at 10% 0%,
                  color-mix(in srgb, var(--accent) 12%, transparent),
                  transparent 32%
              ),
              radial-gradient(
                  circle at 92% 10%,
                  color-mix(in srgb, var(--accent2) 9%, transparent),
                  transparent 28%
              ),
              var(--bg);
            color:var(--text);
        }}

        .main .block-container {{
            max-width:1150px;
            padding-top:1.25rem;
            padding-bottom:4rem;
        }}

        [data-testid="stSidebar"] {{
            background:linear-gradient(180deg,var(--surface),var(--bg));
            border-right:1px solid var(--border);
        }}

        h1,h2,h3,h4,p,label,span,div,li {{
            color:var(--text);
        }}

        .muted {{
            color:var(--muted) !important;
        }}

        /* Streamlit / BaseWeb selectbox readability */
        div[data-baseweb="select"] *,
        div[data-baseweb="popover"] *,
        div[data-baseweb="menu"] *,
        [role="listbox"] *,
        [role="option"] *,
        input,
        textarea {{
            color:var(--text) !important;
        }}

        div[data-baseweb="popover"],
        div[data-baseweb="popover"] > div,
        div[data-baseweb="popover"] > div > div,
        div[data-baseweb="popover"] [data-baseweb="menu"],
        div[data-baseweb="menu"],
        div[data-baseweb="menu"] > div,
        div[data-baseweb="menu"] ul,
        [role="listbox"],
        ul[role="listbox"] {{
            background:var(--surface) !important;
            background-color:var(--surface) !important;
            color:var(--text) !important;
            border:1px solid var(--border) !important;
            box-shadow:0 16px 40px rgba(0,0,0,.28) !important;
        }}

        div[data-baseweb="menu"] li,
        [role="option"] {{
            background:var(--surface) !important;
            background-color:var(--surface) !important;
            color:var(--text) !important;
            border-radius:10px !important;
        }}

        div[data-baseweb="menu"] li:hover,
        [role="option"]:hover,
        [role="option"][aria-selected="true"] {{
            background:rgba(255,255,255,.10) !important;
            background-color:rgba(255,255,255,.10) !important;
            color:var(--text) !important;
        }}

        div[data-baseweb="select"] > div {{
            background:var(--surface) !important;
            color:var(--text) !important;
            border:1px solid var(--border) !important;
            border-radius:12px !important;
        }}

        div[data-baseweb="select"] input {{
            color:var(--text) !important;
            caret-color:var(--accent2) !important;
        }}

        div[data-baseweb="select"] svg {{
            fill:var(--muted) !important;
        }}

        .hero,
        .panel,
        .flashcard,
        .stat {{
            border:1px solid var(--border);
            background:
                linear-gradient(
                    145deg,
                    rgba(255,255,255,.045),
                    rgba(255,255,255,.015)
                ),
                var(--surface);
            border-radius:24px;
        }}

        .hero {{
            padding:30px;
            margin-bottom:25px;
            box-shadow:0 20px 50px rgba(0,0,0,.16);
        }}

        .kicker {{
            color:var(--accent2) !important;
            font-size:12px;
            font-weight:800;
            letter-spacing:.14em;
            text-transform:uppercase;
        }}

        .hero-title {{
            color:var(--text) !important;
            font-size:clamp(36px,5vw,58px);
            font-weight:850;
            line-height:1;
            margin:10px 0 14px;
        }}

        .hero .muted {{
            color:var(--muted) !important;
            line-height:1.75;
            font-size:15px;
        }}

        .pill {{
            display:inline-block;
            margin:7px 6px 0 0;
            padding:7px 12px;
            border:1px solid var(--border);
            border-radius:999px;
            color:var(--muted) !important;
            font-size:12px;
            background:var(--soft-surface);
        }}

        .panel {{
            padding:22px;
            height:100%;
        }}

        .panel h3 {{
            color:var(--text) !important;
        }}

        .stat {{
            padding:18px;
            min-height:105px;
        }}

        .stat-label {{
            color:var(--muted) !important;
            font-size:12px;
            font-weight:700;
        }}

        .stat-value {{
            color:var(--text) !important;
            font-size:28px;
            font-weight:850;
            margin-top:4px;
        }}

        .flashcard {{
            min-height:390px;
            padding:45px 28px;
            text-align:center;
            display:flex;
            flex-direction:column;
            justify-content:center;
            box-shadow:0 22px 55px rgba(0,0,0,.18);
        }}

        .card-label {{
            color:var(--accent2) !important;
            font-size:11px;
            font-weight:800;
            letter-spacing:.13em;
            text-transform:uppercase;
        }}

        .front {{
            color:var(--text) !important;
            font-size:clamp(48px,8vw,82px);
            font-weight:900;
            line-height:1.05;
            margin:18px 0 8px;
        }}

        .script-stack {{
            display:flex;
            flex-direction:column;
            gap:12px;
            margin:22px auto 8px;
            width:min(620px,100%);
        }}

        .script-row {{
            display:flex;
            align-items:center;
            justify-content:space-between;
            gap:18px;
            padding:12px 16px;
            border:1px solid var(--border);
            border-radius:14px;
            background:rgba(255,255,255,.035);
            text-align:left;
        }}

        .script-label {{
            color:var(--muted) !important;
            font-size:12px;
            font-weight:800;
            min-width:95px;
        }}

        .script-value {{
            color:var(--text) !important;
            font-size:27px;
            font-weight:800;
            text-align:right;
            flex:1;
        }}

        .script-value.romaji {{
            color:var(--accent2) !important;
            font-size:20px;
        }}

        .script-value.katakana {{
            color:var(--accent) !important;
        }}

        .answer {{
            margin-top:26px;
            padding:22px;
            border-radius:18px;
            border:1px solid var(--border);
            background:rgba(0,0,0,.10);
            text-align:left;
        }}

        .answer .muted {{
            color:var(--muted) !important;
        }}

        .meaning {{
            color:var(--text) !important;
            font-size:30px;
            font-weight:850;
            margin-top:5px;
        }}

        .reading {{
            color:var(--accent2) !important;
            font-size:18px;
            font-weight:700;
            margin-top:6px;
        }}

        .example-box {{
            margin-top:18px;
            padding:16px 18px;
            border:1px solid var(--border);
            border-left:3px solid var(--accent);
            background:rgba(255,255,255,.035) !important;
            border-radius:12px;
            line-height:1.7;
        }}

        .example-label,
        .translation-label {{
            color:var(--accent2) !important;
            font-size:10px;
            font-weight:850;
            letter-spacing:.12em;
            text-transform:uppercase;
        }}

        .example-text {{
            color:var(--text) !important;
            font-size:17px;
            font-weight:650;
            margin-top:5px;
        }}

        .translation-label {{
            margin-top:11px;
        }}

        .translation {{
            color:var(--muted) !important;
            margin-top:3px;
            font-size:14px;
        }}

        div.stButton > button {{
            min-height:44px;
            border-radius:14px;
            border:1px solid var(--border);
            background:rgba(255,255,255,.035);
            color:var(--text) !important;
            font-weight:750;
        }}

        div.stButton > button:hover {{
            border-color:var(--accent);
            background:rgba(255,255,255,.065);
            transform:translateY(-1px);
        }}

        .leitner-grid {{
            display:grid;
            grid-template-columns:repeat(5,1fr);
            gap:12px;
            margin-top:18px;
        }}

        .leitner-box {{
            border:1px solid var(--border);
            border-radius:16px;
            padding:16px 12px;
            background:rgba(255,255,255,.035);
            text-align:center;
        }}

        .leitner-box-label {{
            color:var(--muted) !important;
            font-size:11px;
            font-weight:800;
            text-transform:uppercase;
            letter-spacing:.08em;
        }}

        .leitner-box-count {{
            color:var(--text) !important;
            font-size:28px;
            font-weight:850;
            margin-top:5px;
        }}

        .leitner-box-note {{
            color:var(--muted) !important;
            font-size:11px;
            margin-top:4px;
        }}

        .leitner-track {{
            height:7px;
            margin-top:12px;
            border-radius:999px;
            background:var(--border);
            overflow:hidden;
        }}

        .leitner-fill {{
            height:100%;
            border-radius:999px;
            background:linear-gradient(90deg,var(--accent),var(--accent2));
        }}

        .flow-grid {{
            display:grid;
            grid-template-columns:repeat(5,minmax(0,1fr));
            gap:12px;
            align-items:stretch;
            margin-top:18px;
        }}

        .flow-card {{
            position:relative;
            padding:18px 15px;
            border:1px solid var(--border);
            border-radius:18px;
            background:linear-gradient(145deg,rgba(255,255,255,.045),rgba(255,255,255,.015)),var(--surface);
            text-align:center;
        }}

        .flow-number {{
            color:var(--accent2) !important;
            font-size:11px;
            font-weight:900;
            letter-spacing:.1em;
            text-transform:uppercase;
        }}

        .flow-title {{
            color:var(--text) !important;
            font-size:17px;
            font-weight:850;
            margin-top:7px;
        }}

        .flow-module {{
            color:var(--accent2) !important;
            font-size:12px;
            font-weight:750;
            margin-top:5px;
        }}

        .flow-note {{
            color:var(--muted) !important;
            font-size:11px;
            line-height:1.5;
            margin-top:7px;
        }}

        .flow-arrow {{
            position:absolute;
            right:-12px;
            top:50%;
            transform:translateY(-50%);
            color:var(--accent2);
            font-size:18px;
            font-weight:900;
            z-index:2;
        }}

        @media (max-width: 900px) {{
            .leitner-grid,
            .flow-grid {{
                grid-template-columns:repeat(2,minmax(0,1fr));
            }}
            .flow-arrow {{
                display:none;
            }}
        }}

        .footer {{
            color:var(--muted) !important;
            font-size:12px;
            text-align:center;
            padding-top:20px;
            margin-top:40px;
            border-top:1px solid var(--border);
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# SESSION STATE
# ============================================================

def init_state() -> None:
    """Initialize application state without overwriting existing values."""
    defaults = {
        "page": "Home",
        "language": "Japanese",
        "level": "N5",
        "size": 10,
        "theme": "Midnight Aurora",
        "current_deck": None,
        "deck_key": None,
        "study_session": None,
        "revealed": False,
        "last_error": None,
        "last_save_message": None,
        "session_history": None,
    }

    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


init_state()
apply_theme(st.session_state.theme)


# ============================================================
# DECK / STORAGE HELPERS
# ============================================================

def selected_deck_key() -> str:
    """Return a stable key for the selected language and level."""
    return f"{st.session_state.language}:{st.session_state.level}"


def selected_filename() -> str:
    """Return the JSON filename for the selected deck."""
    return DECK_CONFIG[
        st.session_state.language
    ]["levels"][
        st.session_state.level
    ]["file"]


def load_selected_deck(force_reload: bool = False) -> Optional[Deck]:
    """
    Load the selected JSON deck through storage.py.

    The loaded deck is then validated before the UI uses it.
    """
    key = selected_deck_key()

    if (
        not force_reload
        and st.session_state.deck_key == key
        and st.session_state.current_deck is not None
    ):
        return st.session_state.current_deck

    try:
        deck = load_deck(
            selected_filename(),
            data_dir=DATA_DIR,
        )

        validation = validate_deck(
            deck,
            require_fifty_cards=True,
        )

        if not validation.valid:
            raise InvalidDeckDataError(
                "; ".join(validation.errors)
            )

        st.session_state.current_deck = deck
        st.session_state.deck_key = key
        st.session_state.last_error = None
        return deck

    except DeckFileNotFoundError as exc:
        st.session_state.last_error = str(exc)
    except EmptyDeckFileError as exc:
        st.session_state.last_error = str(exc)
    except CorruptJSONError as exc:
        st.session_state.last_error = str(exc)
    except InvalidDeckDataError as exc:
        st.session_state.last_error = str(exc)
    except StorageError as exc:
        st.session_state.last_error = str(exc)
    except (OSError, ValueError, TypeError) as exc:
        st.session_state.last_error = (
            f"Could not load the selected deck: {exc}"
        )

    return None


def save_current_deck(deck: Deck) -> bool:
    """Persist a deck's current progress through storage.py."""
    try:
        save_deck(
            deck,
            selected_filename(),
            data_dir=DATA_DIR,
        )
        st.session_state.last_save_message = "Progress saved."
        st.session_state.last_error = None
        return True

    except (StorageError, OSError, TypeError, ValueError) as exc:
        st.session_state.last_error = (
            f"Progress could not be saved: {exc}"
        )
        return False


def load_history() -> List[Dict]:
    """Load persisted session history once per Streamlit session."""
    if st.session_state.session_history is None:
        try:
            st.session_state.session_history = load_session_history(
                data_dir=DATA_DIR,
                limit=50,
            )
        except StorageError as exc:
            st.session_state.session_history = []
            st.session_state.last_error = f"Session history could not be loaded: {exc}"
    return st.session_state.session_history


def record_completed_session(study_session: Session) -> None:
    """Persist one completed session exactly once."""
    if not isinstance(study_session, Session) or not study_session.is_complete:
        return

    history = load_history()
    summary = session_summary(study_session)
    completed_at = datetime.now().isoformat(timespec="microseconds")
    session_id = (
        f"{summary['language']}:{summary['level']}:"
        f"{summary['cards_selected']}:{completed_at}"
    )

    if any(item.get("session_id") == session_id for item in history):
        return

    entry = {
        "session_id": session_id,
        "timestamp": completed_at,
        **summary,
    }

    try:
        updated = append_session_history(
            entry,
            data_dir=DATA_DIR,
            limit=50,
        )
        st.session_state.session_history = updated
    except StorageError as exc:
        st.session_state.last_error = f"Session history could not be saved: {exc}"


# ============================================================
# VALIDATION / SESSION SELECTION
# ============================================================

def validate_current_selection() -> bool:
    """Validate the current language, level and practice-size choices."""
    language_result = validate_language(st.session_state.language)
    level_result = validate_level(
        st.session_state.language,
        st.session_state.level,
    )
    size_result = validate_practice_size(st.session_state.size)

    errors = (
        language_result.errors
        + level_result.errors
        + size_result.errors
    )

    if errors:
        st.error(" • ".join(errors))
        return False

    return True


def select_session_cards(deck: Deck, practice_size: int) -> List[Card]:
    """
    Select cards for a practice session.

    Selection strategy:
    1. Previously reviewed weak cards are prioritized.
    2. New/unreviewed cards are then prioritized.
    3. Remaining cards are considered from lower Leitner boxes first.
    4. Cards inside each priority group are randomized.

    This preserves the requested random experience for new study while
    still giving the spaced-repetition system control over review priority.
    """
    size_result = validate_practice_size(practice_size)

    if not size_result.valid:
        raise ValueError("; ".join(size_result.errors))

    if deck.card_count < practice_size:
        raise ValueError(
            f"The selected deck has {deck.card_count} cards, but "
            f"{practice_size} cards were requested."
        )

    reviewed_weak = [
        card
        for card in deck.cards
        if card.review_count > 0 and card.is_weak
    ]

    new_cards = [
        card
        for card in deck.cards
        if card.is_new
    ]

    selected_ids = {
        card.card_id
        for card in reviewed_weak + new_cards
    }

    remaining_cards = [
        card
        for card in deck.cards
        if card.card_id not in selected_ids
    ]

    random.shuffle(reviewed_weak)
    random.shuffle(new_cards)

    grouped_remaining: Dict[int, List[Card]] = {
        box: []
        for box in range(1, 6)
    }

    for card in remaining_cards:
        grouped_remaining[card.box].append(card)

    for cards in grouped_remaining.values():
        random.shuffle(cards)

    ordered_candidates = list(reviewed_weak) + list(new_cards)

    for box in range(1, 6):
        ordered_candidates.extend(grouped_remaining[box])

    selected = ordered_candidates[:practice_size]
    random.shuffle(selected)

    selection_result = validate_session_selection(
        deck,
        practice_size,
        selected,
    )

    if not selection_result.valid:
        raise ValueError("; ".join(selection_result.errors))

    return selected


def start_session() -> bool:
    """Create a real Session object from the selected JSON-backed Deck."""
    if not validate_current_selection():
        return False

    deck = load_selected_deck()

    if deck is None:
        if st.session_state.last_error:
            st.error(st.session_state.last_error)
        return False

    try:
        selected = select_session_cards(
            deck,
            st.session_state.size,
        )

        study_session = Session(
            deck=deck,
            practice_size=st.session_state.size,
        )
        study_session.start(selected)

        st.session_state.study_session = study_session
        st.session_state.revealed = False
        st.session_state.last_save_message = None
        st.session_state.last_error = None
        st.session_state.page = "Study"
        return True

    except (ValueError, TypeError, RuntimeError) as exc:
        st.error(f"Could not start the study session: {exc}")
        return False


def reset_study_session() -> None:
    """Clear only the active study session while preserving saved progress/history."""
    st.session_state.study_session = None
    st.session_state.revealed = False
    st.session_state.last_save_message = None


def rate_current_card(rating: str) -> bool:
    """
    Rate the current card through models.Session and immediately persist
    the updated deck through storage.py.
    """
    study_session = st.session_state.study_session

    if not isinstance(study_session, Session):
        st.error("There is no active study session.")
        return False

    try:
        study_session.rate_current_card(rating)

        # Save immediately so a browser refresh/restart does not lose
        # the learner's latest Leitner progress.
        saved = save_current_deck(study_session.deck)

        # Every rating moves us to a fresh card state. This prevents the
        # next card from inheriting the previous card's revealed state.
        st.session_state.revealed = False

        if study_session.is_complete:
            record_completed_session(study_session)
            st.session_state.page = "Summary"

        return saved

    except (ValueError, TypeError, RuntimeError) as exc:
        st.error(f"Could not record the rating: {exc}")
        return False


# ============================================================
# DISPLAY HELPERS
# ============================================================

def is_japanese_card(card: Card) -> bool:
    """Return True when the supplied Card belongs to a Japanese deck."""
    return card.language.strip().lower() == "japanese"


def japanese_script_html(card: Card) -> str:
    """
    Build the Japanese learning display in the requested order:

        Kanji -> Hiragana -> Romaji -> Katakana (when applicable)
    """
    kanji = html.escape(card.kanji or "—")
    hiragana = html.escape(card.hiragana or "—")
    romaji = html.escape(card.romaji or "—")
    katakana = html.escape(card.katakana)

    rows = [
        (
            '<div class="script-row">'
            '<span class="script-label">Kanji</span>'
            f'<span class="script-value">{kanji}</span>'
            "</div>"
        ),
        (
            '<div class="script-row">'
            '<span class="script-label">Hiragana</span>'
            f'<span class="script-value">{hiragana}</span>'
            "</div>"
        ),
        (
            '<div class="script-row">'
            '<span class="script-label">Romaji</span>'
            f'<span class="script-value romaji">{romaji}</span>'
            "</div>"
        ),
    ]

    if card.katakana:
        rows.append(
            (
                '<div class="script-row">'
                '<span class="script-label">Katakana</span>'
                f'<span class="script-value katakana">{katakana}</span>'
                "</div>"
            )
        )

    return '<div class="script-stack">' + "".join(rows) + "</div>"


def render_html(markup: str) -> None:
    """Render custom HTML directly, bypassing Markdown code-block parsing."""
    cleaned = textwrap.dedent(markup).strip()
    if not cleaned:
        return
    st.html(cleaned, width="stretch")


def render_gap() -> None:
    """Render theme-safe vertical spacing without Markdown HTML."""
    st.html('<div class="section-gap" aria-hidden="true"></div>', width="stretch")


def render_example(card: Card) -> str:
    """Render a clean example panel for every supported language."""
    example = html.escape(card.example.strip() or "No example sentence available.")
    translation = html.escape(
        card.translation.strip() or "No English translation available."
    )
    language_label = html.escape(card.language)

    return (
        '<div class="example-box">'
        f'<div class="example-label">EXAMPLE • {language_label.upper()}</div>'
        f'<div class="example-text">{example}</div>'
        '<div class="translation-label">ENGLISH</div>'
        f'<div class="translation">{translation}</div>'
        "</div>"
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(f"## 🧠 {APP_NAME}")
    st.caption("Language • Spaced Repetition • Practice")
    st.divider()

    pages = ["Home", "Study", "Progress", "About", "Summary"]

    # Keep navigation safe even if a previous session state contains an
    # obsolete or unknown page value.
    if st.session_state.page not in pages:
        st.session_state.page = "Home"

    st.session_state.page = st.radio(
        "Navigate",
        pages,
        index=pages.index(st.session_state.page),
    )

    st.divider()

    selected_theme = st.selectbox(
        "Theme",
        list(THEMES.keys()),
        index=list(THEMES.keys()).index(st.session_state.theme),
    )

    if selected_theme != st.session_state.theme:
        st.session_state.theme = selected_theme
        st.rerun()

    st.divider()

    st.write("**Current deck**")
    st.write(
        f'{DECK_CONFIG[st.session_state.language]["flag"]} '
        f'{st.session_state.language} • {st.session_state.level}'
    )

    if st.button(
        "↻ Reset study session",
        width="stretch",
    ):
        reset_study_session()
        st.session_state.page = "Home"
        st.rerun()


# ============================================================
# HERO
# ============================================================

render_html(
"""
    <div class="hero">
        <div class="kicker">ZENKI • Think → Reveal → Remember</div>
        <div class="hero-title">
            Learn languages with spaced repetition.
        </div>
        <div class="muted">
            Build recall first, reveal the context second, then rate the card.
            ZenKi uses a Leitner-based review flow and keeps learner progress
            in JSON so the next session can use it again.
        </div>
        <div style="margin-top:16px;">
            <span class="pill">🇯🇵 Japanese N5 / N4</span>
            <span class="pill">🇪🇸 Spanish A1</span>
            <span class="pill">🇫🇷 French A1</span>
            <span class="pill">10 / 20 / 25 cards</span>
            <span class="pill">Leitner</span>
        </div>
    </div>
    """
)


# ============================================================
# HOME
# ============================================================

def render_home() -> None:
    """Render language, level, deck and practice-size selection."""
    st.subheader("Choose your learning path")

    left, right = st.columns(2)

    with left:
        languages = list(DECK_CONFIG.keys())

        language = st.selectbox(
            "Language",
            languages,
            index=languages.index(st.session_state.language),
            format_func=lambda value: (
                f'{DECK_CONFIG[value]["flag"]}  {value}'
            ),
        )

        if language != st.session_state.language:
            st.session_state.language = language
            st.session_state.level = list(
                DECK_CONFIG[language]["levels"].keys()
            )[0]
            st.session_state.current_deck = None
            st.session_state.deck_key = None
            reset_study_session()
            st.rerun()

    with right:
        levels = list(
            DECK_CONFIG[st.session_state.language]["levels"].keys()
        )

        current_index = levels.index(st.session_state.level)

        level = st.selectbox(
            "Level",
            levels,
            index=current_index,
            format_func=lambda value: (
                DECK_CONFIG[
                    st.session_state.language
                ]["levels"][value]["label"]
            ),
        )

        if level != st.session_state.level:
            st.session_state.level = level
            st.session_state.current_deck = None
            st.session_state.deck_key = None
            reset_study_session()
            st.rerun()

    if not validate_current_selection():
        return

    deck = load_selected_deck()

    if deck is None:
        if st.session_state.last_error:
            st.error(st.session_state.last_error)
        return

    deck_description = DECK_CONFIG[
        st.session_state.language
    ]["levels"][
        st.session_state.level
    ]["description"]

    summary = deck_summary(deck)

    render_gap()

    c1, c2, c3, c4 = st.columns(4)

    metrics = [
        (c1, "Cards in deck", summary["total_cards"]),
        (c2, "New cards", summary["new_cards"]),
        (c3, "Weak cards", summary["weak_cards"]),
        (c4, "Saved accuracy", f'{summary["accuracy"]}%'),
    ]

    for column, label, value in metrics:
        with column:
            render_html(
f"""
                <div class="stat">
                    <div class="stat-label">{html.escape(str(label))}</div>
                    <div class="stat-value">{html.escape(str(value))}</div>
                </div>
                """
)

    render_gap()

    a, b = st.columns(2)

    with a:
        render_html(
f"""
            <div class="panel">
                <h3>
                    {DECK_CONFIG[st.session_state.language]["flag"]}
                    {html.escape(st.session_state.language)}
                    {html.escape(st.session_state.level)}
                </h3>
                <p class="muted">
                    {html.escape(deck_description)}
                </p>
            </div>
            """
)

    with b:
        render_html(
"""
            <div class="panel">
                <h3>Practice selection</h3>
                <p class="muted">
                    The source deck contains 50 cards. Choose 10, 20 or
                    25 for the current session. New cards are randomized;
                    saved weak cards are prioritized for review.
                </p>
            </div>
            """
)

    render_gap()
    st.subheader("How many cards do you want to practice?")

    st.session_state.size = st.radio(
        "Practice size",
        ALLOWED_SESSION_SIZES,
        horizontal=True,
        index=ALLOWED_SESSION_SIZES.index(st.session_state.size),
        format_func=lambda value: f"{value} cards",
    )

    if deck.card_count < st.session_state.size:
        st.error(
            f"This deck has only {deck.card_count} cards, so "
            f"{st.session_state.size} cannot be selected."
        )
        return

    if st.button(
        f"Start {st.session_state.size}-card session →",
        type="primary",
        width="stretch",
    ):
        if start_session():
            st.rerun()


# ============================================================
# STUDY
# ============================================================

def render_study() -> None:
    """Render the current flashcard and rating controls."""
    study_session = st.session_state.study_session

    if not isinstance(study_session, Session):
        st.subheader("No active session")
        st.write("Start a study session from Home.")
        return

    if study_session.is_complete:
        record_completed_session(study_session)
        st.session_state.revealed = False
        st.session_state.page = "Summary"
        st.rerun()

    card = study_session.current_card
    if card is None:
        record_completed_session(study_session)
        st.session_state.revealed = False
        st.session_state.page = "Summary"
        st.rerun()

    completed = len(study_session.completed_cards)
    total = study_session.practice_size

    st.markdown(
        f"### {DECK_CONFIG[card.language]['flag']} "
        f"{html.escape(card.language)} • {html.escape(card.level)}"
    )

    p1, p2 = st.columns([4, 1])
    with p1:
        st.progress(min(1.0, completed / total) if total else 0.0)
    with p2:
        st.markdown(f"**{min(completed + 1, total)} / {total}**")

    render_gap()

    if is_japanese_card(card):
        front_details = japanese_script_html(card)
        front_prompt = (
            "Read the writing forms first. Try to remember the meaning "
            "before revealing the answer."
        )
    else:
        front_details = f'<div class="front">{html.escape(card.front)}</div>'
        front_prompt = (
            "Think about the meaning and context before revealing the answer."
        )

    front_html = f"""
    <div class="flashcard">
        <div class="card-label">Think first</div>
        {front_details}
        <div class="muted" style="margin-top:16px;">
            {html.escape(front_prompt)}
        </div>
    </div>
    """
    render_html(front_html)

    if not st.session_state.revealed:
        if st.button("Reveal Answer", type="primary", width="stretch"):
            st.session_state.revealed = True
            st.rerun()
        return

    meaning = html.escape(card.meaning)
    reading = (
        f'<div class="reading">{html.escape(card.reading)}</div>'
        if card.reading
        else ""
    )
    answer_support = japanese_script_html(card) if is_japanese_card(card) else ""

    answer_html = f"""
    <div class="answer">
        <div class="muted">MEANING</div>
        <div class="meaning">{meaning}</div>
        {reading}
        {answer_support}
        {render_example(card)}
    </div>
    """
    render_html(answer_html)

    render_gap()
    st.subheader("How well did you remember it?")

    again, good, easy = st.columns(3)

    with again:
        if st.button("↻ Again", width="stretch"):
            if rate_current_card("again"):
                st.rerun()

    with good:
        if st.button("✓ Good", type="primary", width="stretch"):
            if rate_current_card("good"):
                st.rerun()

    with easy:
        if st.button("⚡ Easy", width="stretch"):
            if rate_current_card("easy"):
                st.rerun()

    if st.session_state.last_save_message:
        st.caption(st.session_state.last_save_message)
    if st.session_state.last_error:
        st.error(st.session_state.last_error)


# ============================================================
# SUMMARY
# ============================================================

def render_summary() -> None:
    """Render separate Good/Easy/Again counts and calculated accuracy."""
    study_session = st.session_state.study_session

    if not isinstance(study_session, Session):
        st.subheader("No completed session")
        st.write("Start a study session from Home.")
        return

    summary = session_summary(study_session)

    st.subheader("Session complete 🎉")
    render_html(
'<p class="muted">Your rating breakdown for this session.</p>'
)

    top1, top2, top3 = st.columns(3)

    for column, icon, label, value in [
        (top1, "✓", "Good", summary["good"]),
        (top2, "⚡", "Easy", summary["easy"]),
        (top3, "↻", "Again", summary["again"]),
    ]:
        with column:
            render_html(
f"""
                <div class="stat">
                    <div class="stat-label">{icon} {label}</div>
                    <div class="stat-value">{value}</div>
                </div>
                """
)

    render_gap()

    b1, b2, b3 = st.columns(3)

    for column, icon, label, value in [
        (b1, "📚", "Cards selected", summary["cards_selected"]),
        (b2, "📝", "Ratings recorded", summary["total_ratings"]),
        (b3, "🎯", "Accuracy", f'{summary["accuracy"]}%'),
    ]:
        with column:
            render_html(
f"""
                <div class="stat">
                    <div class="stat-label">{icon} {label}</div>
                    <div class="stat-value">{value}</div>
                </div>
                """
)

    render_gap()

    render_html(
f"""
        <div class="panel">
            <h3>Accuracy calculation</h3>
            <p class="muted">
                Accuracy = (Good + Easy) ÷ Ratings recorded × 100
            </p>
            <p>
                <b>{summary["good"]}</b> Good +
                <b>{summary["easy"]}</b> Easy =
                <b>{summary["correct_ratings"]}</b> correct ratings
                out of <b>{summary["total_ratings"]}</b> total ratings.
            </p>
        </div>
        """
)

    render_gap()

    deck_stats = deck_summary(study_session.deck)

    c1, c2 = st.columns(2)

    with c1:
        render_html(
            f"""
            <div class="panel">
                <h3>Saved deck progress</h3>
                <p class="muted">
                    Total cards: <b>{deck_stats["total_cards"]}</b><br>
                    Reviewed cards: <b>{deck_stats["reviewed_cards"]}</b><br>
                    Weak cards: <b>{deck_stats["weak_cards"]}</b><br>
                    Saved accuracy: <b>{deck_stats["accuracy"]}%</b>
                </p>
            </div>
            """
        )

    with c2:
        render_html(
"""
            <div class="panel">
                <h3>Review behavior</h3>
                <p class="muted">
                    Again sends the card back into the review queue and returns
                    it to Box 1. Good advances one Leitner box. Easy advances
                    two boxes, up to Box 5. The updated deck is saved to JSON
                    after every rating.
                </p>
            </div>
            """
)

    render_gap()

    history = load_history()
    if history:
        render_html(
"""
            <div class="panel">
                <h3>Recent session history</h3>
                <p class="muted">
                    Previous completed loops stay here when you restart. Your
                    saved card/Leitner progress is kept separately.
                </p>
            </div>
            """
)
        history_rows = []
        for item in reversed(history[-10:]):
            history_rows.append(
                {
                    "Date": item.get("timestamp", ""),
                    "Deck": f"{item.get('language', '')} {item.get('level', '')}",
                    "Cards": item.get("cards_selected", 0),
                    "Good": item.get("good", 0),
                    "Easy": item.get("easy", 0),
                    "Again": item.get("again", 0),
                    "Accuracy": f"{item.get('accuracy', 0)}%",
                }
            )
        if history_rows:
            st.dataframe(
                pd.DataFrame(history_rows),
                width="stretch",
                hide_index=True,
            )

    render_gap()

    with st.expander("Cards from this session"):
        completed_df = cards_to_dataframe(
            study_session.completed_cards
        )

        if completed_df.empty:
            st.info("No completed cards to display.")
        else:
            display_columns = [
                "front",
                "meaning",
                "box",
                "last_rating",
                "accuracy",
            ]
            st.dataframe(
                completed_df[display_columns],
                width="stretch",
                hide_index=True,
            )

    render_gap()

    left, right = st.columns(2)

    with left:
        if st.button(
            "Practice this deck again",
            type="primary",
            width="stretch",
        ):
            reset_study_session()
            if start_session():
                st.rerun()

    with right:
        if st.button(
            "Back to Home",
            width="stretch",
        ):
            reset_study_session()
            st.session_state.page = "Home"
            st.rerun()


# ============================================================
# PROGRESS
# ============================================================

def render_progress() -> None:
    """Render persistent deck analytics from analysis.py."""
    st.subheader("Progress")

    deck = load_selected_deck()

    if deck is None:
        if st.session_state.last_error:
            st.error(st.session_state.last_error)
        return

    summary = deck_summary(deck)
    box_df = box_distribution_dataframe(deck.cards)

    c1, c2, c3, c4 = st.columns(4)

    for column, label, value in [
        (c1, "Total cards", summary["total_cards"]),
        (c2, "Reviewed", summary["reviewed_cards"]),
        (c3, "Weak cards", summary["weak_cards"]),
        (c4, "Accuracy", f'{summary["accuracy"]}%'),
    ]:
        with column:
            render_html(
f"""
                <div class="stat">
                    <div class="stat-label">{label}</div>
                    <div class="stat-value">{value}</div>
                </div>
                """
)

    render_gap()

    render_html(
"""
        <div class="panel">
            <h3>Leitner box distribution</h3>
            <p class="muted">
                Cards move through Boxes 1 to 5 as their review ratings change.
                Lower boxes represent cards that currently need more attention.
            </p>
        </div>
        """
)

    max_cards = max(int(box_df["cards"].max()), 1)
    box_parts = []

    for _, row in box_df.iterrows():
        box_number = int(row["box"])
        card_count = int(row["cards"])
        fill = round((card_count / max_cards) * 100) if card_count else 0
        note = "New / needs attention" if box_number == 1 else f"Leitner Box {box_number}"
        box_parts.append(
            f"""
            <div class="leitner-box">
                <div class="leitner-box-label">BOX {box_number}</div>
                <div class="leitner-box-count">{card_count}</div>
                <div class="leitner-box-note">{note}</div>
                <div class="leitner-track">
                    <div class="leitner-fill" style="width:{fill}%;"></div>
                </div>
            </div>
            """
        )

    render_html(
        '<div class="leitner-grid">' + "".join(box_parts) + '</div>'
    )
    render_gap()

    weak_cards = get_weak_cards(deck.cards, limit=10)

    st.subheader("Cards needing more attention")

    if weak_cards:
        weak_df = weak_cards_dataframe(
            deck.cards,
            limit=10,
        )

        display_columns = [
            "front",
            "meaning",
            "box",
            "review_count",
            "again_count",
            "accuracy",
        ]

        st.dataframe(
            weak_df[display_columns],
            width="stretch",
            hide_index=True,
        )
    else:
        st.info(
            "No previously reviewed weak cards were found in this deck."
        )

    render_gap()

    with st.expander("All deck cards"):
        all_df = cards_to_dataframe(deck.cards)

        display_columns = [
            "front",
            "meaning",
            "box",
            "review_count",
            "last_rating",
            "accuracy",
        ]

        st.dataframe(
            all_df[display_columns],
            width="stretch",
            hide_index=True,
        )


# ============================================================
# ABOUT
# ============================================================

def render_about() -> None:
    """Explain how the ZenKi application flows from input to saved results."""
    st.subheader("About ZenKi")

    render_html(
        """
        <div class="panel">
            <h3>How ZenKi works</h3>
            <p class="muted">
                ZenKi takes one learning session through a simple pipeline:
                choose a deck, validate the request, load the saved cards,
                apply Leitner learning rules, calculate analytics, and save the
                updated progress and completed-session history.
            </p>
        </div>
        """
    )

    flow_cards = [
        ("01", "Choose", "main.py", "Language, level and session size"),
        ("02", "Validate", "validators.py", "Check selections and card data"),
        ("03", "Load + Save", "storage.py", "Read decks and persist progress/history"),
        ("04", "Learn", "models.py", "Run cards, Session and Leitner rules"),
        ("05", "Analyse", "analysis.py", "Turn results into NumPy/Pandas insights"),
    ]

    pieces = []
    for index, (number, title, module, note) in enumerate(flow_cards):
        arrow = '<div class="flow-arrow">→</div>' if index < len(flow_cards) - 1 else ''
        pieces.append(
            f"""
            <div class="flow-card">
                <div class="flow-number">STEP {number}</div>
                <div class="flow-title">{html.escape(title)}</div>
                <div class="flow-module">{html.escape(module)}</div>
                <div class="flow-note">{html.escape(note)}</div>
                {arrow}
            </div>
            """
        )

    render_html('<div class="flow-grid">' + ''.join(pieces) + '</div>')

    render_gap()

    left, right = st.columns(2)
    with left:
        render_html(
            """
            <div class="panel">
                <h3>During a study session</h3>
                <p class="muted">
                    Think first → reveal the answer → rate the card. Good moves
                    a card one box, Easy moves it two boxes, and Again returns
                    it to Box 1 with a limited retry queue.
                </p>
            </div>
            """
        )
    with right:
        render_html(
            """
            <div class="panel">
                <h3>After the session</h3>
                <p class="muted">
                    ZenKi stores updated card progress in the deck JSON and
                    keeps the finished session summary separately. This lets
                    you start another loop without losing previous results.
                </p>
            </div>
            """
        )

    render_gap()

    render_html(
        """
        <div class="panel">
            <h3>The learning data flow</h3>
            <p class="muted">
                <b>Deck JSON</b> → validated card objects → active Session →
                rating history → NumPy/Pandas analytics → updated deck JSON +
                session history → ZenKi result screens.
            </p>
        </div>
        """
    )


# ============================================================
# ROUTER
# ============================================================

VALID_PAGES = {"Home", "Study", "Progress", "About", "Summary"}

if st.session_state.page not in VALID_PAGES:
    st.session_state.page = "Home"

if st.session_state.page == "Home":
    render_home()
elif st.session_state.page == "Study":
    render_study()
elif st.session_state.page == "Progress":
    render_progress()
elif st.session_state.page == "About":
    render_about()
elif st.session_state.page == "Summary":
    render_summary()


render_html(
'<div class="footer">ZenKi • Language Learning • Spaced Repetition</div>'
)
