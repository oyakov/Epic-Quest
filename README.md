# Epic Quest

Epic Quest is a lightweight 2D tactical RPG prototype inspired by classic fantasy adventures.
It features a global map with multiple locations, turn-based tactical battles, loot, and a
simple talent system.

## Requirements

- Python 3.10–3.13 (validated on Windows, macOS, and Linux)
- pygame 2.6.1 (installed via `requirements.txt`)
- Platform prerequisites:
  - **Windows**: Visual C++ 2015–2022 redistributable (bundled with recent Visual Studio Build Tools).
  - **Linux**: SDL2, SDL2_image, SDL2_mixer, and SDL2_ttf development packages from your distribution.
  - **macOS**: SDL2 libraries via Homebrew (`brew install sdl2 sdl2_image sdl2_mixer sdl2_ttf`).

Install dependencies with:

```bash
pip install -r requirements.txt
```

## Running the game

```bash
python main.py
```

## Controls

### Global Map
- **Arrow Keys**: Cycle between discovered locations
- **Enter**: Travel to the highlighted location (starts a tactical battle)
- **I**: Toggle inventory overview
- **T**: Toggle talent tree
- **Esc**: Quit the game

### Tactical Map
- **Arrow Keys**: Move the hero one tile
- **Space**: Attack an adjacent enemy (orthogonal)
- **Tab**: End hero turn without acting
- **I**: Toggle inventory overview
- **T**: Toggle talent tree

Victory in a tactical battle returns you to the global map with the earned loot and
experience. Spend talent points in the talent tree window.
