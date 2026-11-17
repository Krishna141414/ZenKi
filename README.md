# ZenKi 🧠

ZenKi is a spaced-repetition flashcard trainer for language learning, built with Streamlit. It uses the Leitner system to schedule card reviews.

## 🎥 Demo Video

Watch the full walkthrough of ZenKi here:
**[ZenKi Demo Recording (Google Drive)](https://drive.google.com/file/d/1WajtgKqv99XY9jofVFgU31_WidY5DSAv/view?usp=sharing)**

## Features

- Language decks: Japanese (JLPT N5, N4), Spanish (A1), French (A1)
- Leitner box progression across 5 boxes (Again / Good / Easy ratings)
- Practice sessions of 10, 20 or 25 cards
- Progress page with box distribution and the cards that need more practice
- Session history saved to JSON
- Validation and error handling for missing, empty or corrupt deck files

## Project Structure

```
ZenKi/
├── main.py              # Streamlit UI
├── trainer/
│   ├── models.py        # Card, Deck, Session and Leitner logic
│   ├── storage.py       # JSON loading and saving
│   ├── validators.py    # Input and data validation
│   └── analysis.py      # NumPy/Pandas analytics
├── data/                # Language decks and session history (JSON)
├── tests/               # Pytest test suite
└── screenshots_task1/   # Screenshots of the app running
```

## Getting Started

```bash
git clone https://github.com/Krishna141414/ZenKi.git
cd ZenKi
pip install -r requirements.txt
streamlit run main.py
```

## Running Tests

```bash
pytest tests/
```

## Tech Stack

Python, Streamlit, NumPy, Pandas, Pytest
