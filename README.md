# Number Guessing Game 🎯

A number guessing game written in Python. The computer picks a number
from 1 to 10 and you try to guess it.

## Files
- `number_guessing.py` is the terminal version of the game
- `guessing_game_ui.py` is a Tkinter window that runs the terminal game
  behind the scenes, so you play with buttons and an input box instead

## Features
- Too high / too low hints after every guess
- Attempt counter and guess history
- Input validation (whole numbers from 1 to 10 only)
- Play again button

## How to run
Keep both files in the same folder, then run:

    python guessing_game_ui.py

Or play the plain terminal version:

    python number_guessing.py

## Built with
Python (Tkinter, subprocess)
