#!/usr/bin/env python3
"""
Web server for Riichi Mahjong Engine
Provides REST API and WebSocket interface
"""

from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import json
import uuid
from typing import Dict, Any
from game.engine import MahjongEngine

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mahjong-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*")

# Store active games
games: Dict[str, MahjongEngine] = {}
player_sessions: Dict[str, str] = {}  # session_id -> game_id

@app.route('/api/create_game', methods=['POST'])
def create_game():
    """Create a new game"""
    data = request.json
    player_names = data.get('players', ['Player 1', 'Player 2', 'Player 3', 'Player 4'])
    
    if len(player_names) != 4:
        return jsonify({'error': 'Exactly 4 players required'}), 400
    
    game_id = str(uuid.uuid4())
    try:
        game = MahjongEngine(player_names)
        games[game_id] = game
        
        return jsonify({
            'game_id': game_id,
            'state': game.get_game_state()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/game/<game_id>/state', methods=['GET'])
def get_game_state(game_id: str):
    """Get current game state"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    return jsonify(game.get_game_state())

@app.route('/api/game/<game_id>/player/<int:player_index>/hand', methods=['GET'])
def get_player_hand(game_id: str, player_index: int):
    """Get player's hand"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    if not (0 <= player_index <= 3):
        return jsonify({'error': 'Invalid player index'}), 400
    
    game = games[game_id]
    return jsonify(game.get_player_hand(player_index))

@app.route('/api/game/<game_id>/player/<int:player_index>/actions', methods=['GET'])
def get_valid_actions(game_id: str, player_index: int):
    """Get valid actions for player"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    game = games[game_id]
    return jsonify({'actions': game.get_valid_actions(player_index)})

@app.route('/api/game/<game_id>/action', methods=['POST'])
def execute_action(game_id: str):
    """Execute a game action"""
    if game_id not in games:
        return jsonify({'error': 'Game not found'}), 404
    
    data = request.json
    player_index = data.get('player_index')
    action = data.get('action')
    kwargs = data.get('kwargs', {})
    
    if player_index is None or action is None:
        return jsonify({'error': 'Missing player_index or action'}), 400
    
    game = games[game_id]
    result = game.execute_action(player_index, action, **kwargs)
    
    # Emit update to all connected clients
    socketio.emit('game_update', {
        'game_id': game_id,
        'result': result,
        'state': game.get_game_state()
    }, room=game_id)
    
    return jsonify(result)

@socketio.on('join_game')
def on_join_game(data):
    """Join a game room"""
    game_id = data['game_id']
    player_index = data.get('player_index')
    
    if game_id not in games:
        emit('error', {'message': 'Game not found'})
        return
    
    join_room(game_id)
    player_sessions[request.sid] = game_id
    
    emit('joined_game', {
        'game_id': game_id,
        'player_index': player_index,
        'state': games[game_id].get_game_state()
    })

@socketio.on('leave_game')
def on_leave_game():
    """Leave a game room"""
    if request.sid in player_sessions:
        game_id = player_sessions[request.sid]
        leave_room(game_id)
        del player_sessions[request.sid]

@socketio.on('disconnect')
def on_disconnect():
    """Handle client disconnect"""
    if request.sid in player_sessions:
        game_id = player_sessions[request.sid]
        leave_room(game_id)
        del player_sessions[request.sid]

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8080, debug=True)
