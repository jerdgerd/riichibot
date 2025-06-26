# Riichi Mahjong Engine

A complete, dockerized implementation of Riichi Mahjong with proper game rules, scoring, and web interface.

## Features

- **Complete Rule Implementation:** All standard Riichi Mahjong rules including furiten, riichi, dora, and proper winning conditions
- **Scoring System:** Accurate han/fu calculation with comprehensive yaku detection
- **Web Interface:** REST API and WebSocket support for real-time gameplay
- **Docker Support:** Full containerization for easy deployment and development
- **Type Safety:** Complete MyPy type checking throughout the codebase
- **Testing:** Comprehensive test suite covering all game mechanics
- **Code Quality:** Black formatting, Flake8 linting, and pre-commit hooks

## Quick Start

### Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd riichi-mahjong

# Build and run
docker-compose up --build

# Access the game
# Engine: http://localhost:8000
# Web Interface: http://localhost:8080
```

## LOCAL DEVELOPMENT
```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/ -v

# Start game engine
python src/main.py

# Start web server
python src/web_server.py
```

## DEVELOPMENT SETUP
# Using VS Code Dev Containers (Recommended)
Prerequisites:

VS Code with Dev Containers extension
Docker Desktop

Quick Start:

git clone <repository-url>
cd riichi-mahjong
code .

Open in Container:

VS Code will prompt to "Reopen in Container"
Or use Command Palette: Dev Containers: Reopen in Container

Ready to Code:

All dependencies pre-installed
Python environment configured
Extensions loaded
Pre-commit hooks enabled

## DEVELOPMENT COMMANDS
# In VS Code
Ctrl+Shift+P → "Tasks: Run Task" for quick actions
F5 to debug current file
Ctrl+Shift+ ` to open integrated terminal

# In Terminal:

```bash
# Run tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Format code
black src/ tests/

# Lint code
flake8 src/

# Type check
mypy src/

# Run pre-commit hooks
pre-commit run --all-files

# Start game engine
python src/main.py

# Start web server
python src/web_server.py
```

## USING MAKE COMMANDS
```bash
# Build Docker images
make build

# Run game engine
make run

# Run web server
make web

# Run tests
make test

# Run tests with coverage
make test-coverage

# Lint and format code
make lint
make format

# Clean up containers
make clean

# Interactive shell
make shell

# Quick demo
make demo
```

## PROJECT STRUCTURE
```bash
riichi-mahjong/
├── .devcontainer/          # Dev container configuration
│   ├── devcontainer.json   # Container settings
│   ├── docker-compose.dev.yml
│   └── Dockerfile          # Development image
├── .vscode/               # VS Code settings and tasks
│   ├── launch.json        # Debug configurations
│   ├── settings.json      # Editor settings
│   └── tasks.json         # Task definitions
├── src/                   # Source code
│   ├── game/             # Game engine
│   │   ├── engine.py     # Main game engine
│   │   ├── player.py     # Player management
│   │   ├── hand.py       # Hand and meld logic
│   │   ├── rules.py      # Yaku detection
│   │   └── scoring.py    # Score calculation
│   ├── tiles/            # Tile and wall management
│   │   ├── tile.py       # Tile definitions
│   │   └── wall.py       # Wall and dora management
│   ├── utils/            # Utilities and constants
│   │   └── constants.py  # Game constants
│   ├── main.py           # CLI entry point
│   └── web_server.py     # Web interface
├── tests/                # Unit tests
│   └── test_game.py      # Comprehensive test suite
├── docker-compose.yml    # Production containers
├── Dockerfile           # Production image
├── Makefile            # Development commands
├── requirements.txt    # Production dependencies
├── requirements-dev.txt # Development dependencies
├── setup.py           # Package configuration
└── README.md         # This file
```

## GAME RULES IMPLEMENTATION
# CORE MECHANICS

Tiles: Complete 136-tile set with optional red fives
Hands: Proper 13+1 tile hand management
Melds: Sequences (chii), triplets (pon), and kans
Winning: 4 sets + 1 pair with valid yaku

# ADVANCED RULES
Riichi: Closed hand declaration with 1000-point bet
Dora: Bonus tiles with ura-dora for riichi hands
Furiten: Comprehensive furiten rule implementation
Scoring: Accurate han/fu calculation with dealer bonuses

# SUPPORTED YAKU
Basic: Riichi, Tanyao, Pinfu, Yakuhai, Menzen Tsumo
Intermediate: Iipeikou, Toitoi, Honitsu, Chinitsu
Advanced: Extensible system for additional yaku

## API USAGE
# PYTHON API
```bash
from game.engine import MahjongEngine

# Create a new game
game = MahjongEngine(["Alice", "Bob", "Charlie", "David"])

# Get current game state
state = game.get_game_state()
print(f"Current player: {state['current_player']}")
print(f"Round: {state['round_wind']} {state['round_number']}")

# Get player's hand
hand = game.get_player_hand(0)
print(f"Concealed tiles: {hand['concealed_tiles']}")
print(f"Can win with: {hand['winning_tiles']}")

# Execute actions
result = game.execute_action(0, "discard", tile="1sou")
if result["success"]:
    print("Tile discarded successfully")

# Check valid actions
actions = game.get_valid_actions(0)
print(f"Valid actions: {actions}")
```

# REST API
```bash
# Create a new game
curl -X POST http://localhost:8080/api/create_game \
  -H "Content-Type: application/json" \
  -d '{"players": ["Alice", "Bob", "Charlie", "David"]}'

# Get game state
curl http://localhost:8080/api/game/{game_id}/state

# Get player hand
curl http://localhost:8080/api/game/{game_id}/player/0/hand

# Execute action
curl -X POST http://localhost:8080/api/game/{game_id}/action \
  -H "Content-Type: application/json" \
  -d '{"player_index": 0, "action": "discard", "kwargs": {"tile": "1sou"}}'
```

# WEBSOCKET EVENTS
```javascript
// Connect to game
const socket = io('http://localhost:8080');

// Join game room
socket.emit('join_game', {
    game_id: 'your-game-id',
    player_index: 0
});

// Listen for game updates
socket.on('game_update', (data) => {
    console.log('Game updated:', data.state);
});

// Handle connection
socket.on('joined_game', (data) => {
    console.log('Joined game:', data.game_id);
});
```

## TESTING
# Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run with coverage
python -m pytest tests/ --cov=src --cov-report=html

# Run specific test
python -m pytest tests/test_game.py::TestMahjongEngine::test_game_initialization -v

# Run tests in parallel
python -m pytest tests/ -n auto
```

# TEST COVERAGE
The test suite covers:

Game initialization and setup
Tile and wall management
Hand completion detection
Meld formation and validation
Yaku detection and scoring
Player actions and game flow
Basic Rule implementations

## DEPLOYMENT
# DOCKER PRODUCTION
```bash
# Build production image
docker build -t riichi-mahjong .

# Run with docker-compose
docker-compose -f docker-compose.yml up -d

# Scale web servers
docker-compose up --scale mahjong-web=3
```

ENVIRONMENT VARIABLES
```bash
# Development
DEBUG=true
FLASK_ENV=development
PYTHONPATH=/app/src

# Production
DEBUG=false
FLASK_ENV=production
REDIS_URL=redis://redis:6379/0
```
## PRE-COMMIT HOOKS
```bash
# Install hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

## LICENSE
License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Roadmap
 Advanced Yaku: Implement remaining yakuman and rare yaku
 AI Players: Add computer opponents with different skill levels
 Tournament Mode: Multi-round tournament support
 Replay System: Game recording and playback
 Mobile App: React Native mobile interface
 Statistics: Player statistics and game analytics
## Support
    Issues: Report bugs and feature requests on GitHub Issues
