import os
import json
import random
import string
import time
from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect('users.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password_hash TEXT NOT NULL,
                     skin TEXT DEFAULT '@',
                     skin_color TEXT DEFAULT '0,255,200',
                     coins INTEGER DEFAULT 0,
                     achievements TEXT DEFAULT '[]',
                     unlocked_skins TEXT DEFAULT '["@"]',
                     unlocked_colors TEXT DEFAULT '["Неоновый"]',
                     total_coins_earned INTEGER DEFAULT 0,
                     total_symbols_collected INTEGER DEFAULT 0,
                     games_won INTEGER DEFAULT 0,
                     enemies_escaped INTEGER DEFAULT 0,
                     games_played INTEGER DEFAULT 0,
                     time_played INTEGER DEFAULT 0)''')
    conn.commit()
    conn.close()
    print("База данных готова")

init_db()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

def generate_maze(w, h):
    maze = [[1 for _ in range(w)] for _ in range(h)]
    stack = [(1, 1)]
    maze[1][1] = 0
    
    while stack:
        x, y = stack[-1]
        neighbors = []
        for dx, dy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            nx, ny = x + dx, y + dy
            if 0 < nx < w - 1 and 0 < ny < h - 1 and maze[ny][nx] == 1:
                neighbors.append((nx, ny))
        
        if neighbors:
            nx, ny = random.choice(neighbors)
            maze[(y + ny) // 2][(x + nx) // 2] = 0
            maze[ny][nx] = 0
            stack.append((nx, ny))
        else:
            stack.pop()
    
    maze[1][1] = 0
    maze[h - 2][w - 2] = 0
    return maze

def place_symbols(maze, count):
    symbols = []
    free_cells = []
    for y in range(len(maze)):
        for x in range(len(maze[0])):
            if maze[y][x] == 0:
                free_cells.append((x, y))
    random.shuffle(free_cells)
    for i in range(min(count, len(free_cells))):
        x, y = free_cells[i]
        symbols.append({"x": x, "y": y, "active": True})
    return symbols

# ==================== ГЛАВНАЯ ====================
@app.route('/')
def home():
    return jsonify({
        "status": "online",
        "message": "Labyrinth of Symbols Server",
        "version": "2.0.0",
        "features": ["accounts", "achievements", "multiplayer"]
    })

# ==================== АККАУНТЫ ====================
@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400
        
        if len(username) < 3:
            return jsonify({'success': False, 'error': 'Ник должен быть минимум 3 символа'}), 400
        
        if len(password) < 3:
            return jsonify({'success': False, 'error': 'Пароль должен быть минимум 3 символа'}), 400

        conn = sqlite3.connect('users.db')
        password_hash = generate_password_hash(password)
        
        conn.execute('''INSERT INTO users 
                        (username, password_hash, coins, achievements, unlocked_skins, unlocked_colors) 
                        VALUES (?, ?, 0, '[]', '["@"]', '["Неоновый"]')''',
                    (username, password_hash))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True, 'message': 'Регистрация успешна'})
        
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Пользователь уже существует'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT password_hash, coins, achievements, unlocked_skins, unlocked_colors,
                                      skin, skin_color
                               FROM users WHERE username = ?''', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            return jsonify({
                'success': True,
                'coins': user[1],
                'achievements': json.loads(user[2]),
                'unlocked_skins': json.loads(user[3]),
                'unlocked_colors': json.loads(user[4]),
                'skin': user[5],
                'skin_color': user[6]
            })
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user-data', methods=['GET'])
def user_data():
    try:
        username = request.args.get('username')
        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT skin, skin_color, coins, achievements, unlocked_skins, unlocked_colors,
                                      total_coins_earned, total_symbols_collected, games_won, games_played
                               FROM users WHERE username=?''', (username,)).fetchone()
        conn.close()
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        return jsonify({
            'success': True,
            'skin': user[0],
            'skin_color': user[1],
            'coins': user[2],
            'achievements': json.loads(user[3]),
            'unlocked_skins': json.loads(user[4]),
            'unlocked_colors': json.loads(user[5]),
            'total_coins_earned': user[6],
            'total_symbols_collected': user[7],
            'games_won': user[8],
            'games_played': user[9]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/sync-data', methods=['POST'])
def sync_data():
    try:
        data = request.get_json()
        username = data.get('username')
        
        conn = sqlite3.connect('users.db')
        
        conn.execute('''UPDATE users SET 
                        coins = ?,
                        skin = ?,
                        skin_color = ?,
                        unlocked_skins = ?,
                        unlocked_colors = ?,
                        total_coins_earned = ?,
                        total_symbols_collected = ?,
                        games_won = ?,
                        games_played = ?
                        WHERE username = ?''',
                    (data.get('coins', 0),
                     data.get('skin', '@'),
                     data.get('skin_color', '0,255,200'),
                     json.dumps(data.get('unlocked_skins', ['@'])),
                     json.dumps(data.get('unlocked_colors', ['Неоновый'])),
                     data.get('total_coins_earned', 0),
                     data.get('total_symbols_collected', 0),
                     data.get('games_won', 0),
                     data.get('games_played', 0),
                     username))
        
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add-coins', methods=['POST'])
def add_coins():
    try:
        data = request.get_json()
        username = data.get('username')
        amount = data.get('amount', 0)
        
        conn = sqlite3.connect('users.db')
        conn.execute('UPDATE users SET coins = coins + ?, total_coins_earned = total_coins_earned + ? WHERE username=?',
                    (amount, amount, username))
        conn.commit()
        new_coins = conn.execute('SELECT coins FROM users WHERE username=?', (username,)).fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'coins': new_coins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/buy-skin', methods=['POST'])
def buy_skin():
    try:
        data = request.get_json()
        username = data.get('username')
        skin = data.get('skin')
        price = data.get('price', 0)
        
        conn = sqlite3.connect('users.db')
        user = conn.execute('SELECT coins, unlocked_skins FROM users WHERE username=?', (username,)).fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        unlocked_skins = json.loads(user[1])
        
        if skin in unlocked_skins:
            return jsonify({'success': False, 'error': 'Скин уже куплен'}), 400
        
        if user[0] < price:
            return jsonify({'success': False, 'error': 'Не хватает монет'}), 400
        
        unlocked_skins.append(skin)
        conn.execute('UPDATE users SET coins = coins - ?, unlocked_skins = ? WHERE username=?',
                    (price, json.dumps(unlocked_skins), username))
        conn.commit()
        new_coins = conn.execute('SELECT coins FROM users WHERE username=?', (username,)).fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'coins': new_coins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/buy-color', methods=['POST'])
def buy_color():
    try:
        data = request.get_json()
        username = data.get('username')
        color = data.get('color')
        price = data.get('price', 0)
        
        conn = sqlite3.connect('users.db')
        user = conn.execute('SELECT coins, unlocked_colors FROM users WHERE username=?', (username,)).fetchone()
        
        if not user:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        unlocked_colors = json.loads(user[1])
        
        if color in unlocked_colors:
            return jsonify({'success': False, 'error': 'Цвет уже куплен'}), 400
        
        if user[0] < price:
            return jsonify({'success': False, 'error': 'Не хватает монет'}), 400
        
        unlocked_colors.append(color)
        conn.execute('UPDATE users SET coins = coins - ?, unlocked_colors = ? WHERE username=?',
                    (price, json.dumps(unlocked_colors), username))
        conn.commit()
        new_coins = conn.execute('SELECT coins FROM users WHERE username=?', (username,)).fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'coins': new_coins})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ДОСТИЖЕНИЯ ====================
@app.route('/save-achievements', methods=['POST'])
def save_achievements():
    try:
        data = request.get_json()
        username = data.get('username')
        achievements = data.get('achievements', {})
        
        conn = sqlite3.connect('users.db')
        conn.execute('UPDATE users SET achievements = ? WHERE username=?',
                    (json.dumps(achievements), username))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/load-achievements', methods=['GET'])
def load_achievements():
    try:
        username = request.args.get('username')
        
        conn = sqlite3.connect('users.db')
        achievements = conn.execute('SELECT achievements FROM users WHERE username=?', (username,)).fetchone()
        conn.close()
        
        if not achievements:
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
        
        return jsonify({
            'success': True,
            'achievements': json.loads(achievements[0])
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== МУЛЬТИПЛЕЕР (КОМНАТЫ) ====================
rooms = {}

@app.route('/create-room', methods=['POST'])
def create_room():
    try:
        data = request.get_json()
        creator = data.get('creator')
        room_name = data.get('room_name', f"Комната {creator}")
        max_players = data.get('max_players', 4)
        difficulty = data.get('difficulty', 'easy')
        
        if not creator:
            return jsonify({'success': False, 'error': 'Укажи создателя'}), 400
        
        symbols_needed = {'easy': 10, 'medium': 15, 'hard': 20}.get(difficulty, 10)
        room_id = generate_room_id()
        
        # Генерируем карту
        maze = generate_maze(20, 15)
        symbols = place_symbols(maze, symbols_needed)
        
        rooms[room_id] = {
            'room_id': room_id,
            'name': room_name,
            'creator': creator,
            'players': [creator],
            'players_data': {creator: {"x": 5, "y": 5, "collected": 0}},
            'max_players': max_players,
            'difficulty': difficulty,
            'symbols_needed': symbols_needed,
            'total_collected': 0,
            'status': 'waiting',
            'created': time.time(),
            'maze': maze,
            'symbols': symbols,
            'game_started': False
        }
        
        print(f"Комната '{room_name}' ({room_id}) создана игроком {creator}")
        return jsonify({
            'success': True,
            'room_id': room_id,
            'room': {
                'id': room_id,
                'name': room_name,
                'host': creator,
                'players': [creator],
                'max': max_players,
                'difficulty': difficulty
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/join-room', methods=['POST'])
def join_room():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if room['status'] != 'waiting':
            return jsonify({'success': False, 'error': 'Игра уже началась'}), 400
        
        if len(room['players']) >= room['max_players']:
            return jsonify({'success': False, 'error': 'Комната полная'}), 400
        
        if username in room['players']:
            return jsonify({'success': False, 'error': 'Ты уже в комнате'}), 400
        
        # Назначаем стартовую позицию
        free_cells = []
        for y in range(len(room['maze'])):
            for x in range(len(room['maze'][0])):
                if room['maze'][y][x] == 0:
                    free_cells.append((x, y))
        
        if free_cells:
            x, y = random.choice(free_cells)
        else:
            x, y = 5, 5
        
        room['players'].append(username)
        room['players_data'][username] = {"x": x, "y": y, "collected": 0}
        
        print(f"{username} зашёл в комнату '{room['name']}' ({room_id})")
        
        if len(room['players']) == room['max_players']:
            room['status'] = 'playing'
            room['game_started'] = True
            print(f"Игра началась в комнате '{room['name']}'")
        
        return jsonify({
            'success': True,
            'room': {
                'id': room_id,
                'name': room['name'],
                'host': room['creator'],
                'players': room['players'],
                'max': room['max_players'],
                'started': room['game_started']
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/leave-room', methods=['POST'])
def leave_room():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if username in room['players']:
            room['players'].remove(username)
            if username in room['players_data']:
                del room['players_data'][username]
            print(f"{username} вышел из комнаты '{room.get('name', room_id)}'")
        
        if not room['players']:
            del rooms[room_id]
            print(f"Комната удалена")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/list-rooms', methods=['GET'])
def list_rooms():
    try:
        available = []
        for rid, r in rooms.items():
            if r['status'] == 'waiting' and len(r['players']) < r['max_players']:
                available.append({
                    'room_id': rid,
                    'name': r.get('name', f"Комната {r['creator']}"),
                    'creator': r['creator'],
                    'players': len(r['players']),
                    'max_players': r['max_players'],
                    'difficulty': r['difficulty']
                })
        return jsonify({'success': True, 'rooms': available})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/room-status', methods=['GET'])
def room_status():
    try:
        room_id = request.args.get('room_id')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        return jsonify({
            'success': True,
            'room_id': room_id,
            'name': room.get('name', 'Комната'),
            'creator': room['creator'],
            'players': room['players'],
            'players_count': len(room['players']),
            'max_players': room['max_players'],
            'status': room['status'],
            'game_started': room.get('game_started', False),
            'total_collected': room['total_collected'],
            'symbols_needed': room['symbols_needed']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/game-state', methods=['GET'])
def game_state():
    try:
        room_id = request.args.get('room_id')
        username = request.args.get('username')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if not room.get('game_started'):
            return jsonify({'success': True, 'game_started': False})
        
        # Собираем данные для игрока
        player_data = room['players_data'].get(username, {})
        
        # Список других игроков
        other_players = []
        for name, data in room['players_data'].items():
            if name != username:
                other_players.append({
                    'name': name,
                    'x': data.get('x', 0),
                    'y': data.get('y', 0),
                    'collected': data.get('collected', 0)
                })
        
        # Активные символы
        active_symbols = [s for s in room['symbols'] if s.get('active', True)]
        
        return jsonify({
            'success': True,
            'game_started': True,
            'maze': room['maze'],
            'symbols': active_symbols,
            'player_x': player_data.get('x', 0),
            'player_y': player_data.get('y', 0),
            'player_collected': player_data.get('collected', 0),
            'other_players': other_players,
            'total_collected': room['total_collected'],
            'symbols_needed': room['symbols_needed']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/move', methods=['POST'])
def move():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        x = data.get('x')
        y = data.get('y')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if not room.get('game_started'):
            return jsonify({'success': False, 'error': 'Игра не началась'}), 400
        
        if username not in room['players_data']:
            return jsonify({'success': False, 'error': 'Ты не в этой комнате'}), 400
        
        # Проверяем, можно ли двигаться (не в стену)
        if 0 <= int(y) < len(room['maze']) and 0 <= int(x) < len(room['maze'][0]):
            if room['maze'][int(y)][int(x)] == 0:
                room['players_data'][username]['x'] = x
                room['players_data'][username]['y'] = y
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/collect', methods=['POST'])
def collect():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        username = data.get('username')
        x = data.get('x')
        y = data.get('y')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if not room.get('game_started'):
            return jsonify({'success': False, 'error': 'Игра не началась'}), 400
        
        if username not in room['players_data']:
            return jsonify({'success': False, 'error': 'Ты не в этой комнате'}), 400
        
        for sym in room['symbols']:
            if sym.get('active') and sym['x'] == x and sym['y'] == y:
                sym['active'] = False
                room['total_collected'] += 1
                room['players_data'][username]['collected'] += 1
                
                # Проверка победы
                game_over = room['total_collected'] >= room['symbols_needed']
                
                if game_over:
                    room['status'] = 'finished'
                    room['game_started'] = False
                    
                    # Начисляем монеты победителю
                    conn = sqlite3.connect('users.db')
                    conn.execute('UPDATE users SET coins = coins + 100, games_won = games_won + 1 WHERE username=?',
                                (username,))
                    conn.commit()
                    conn.close()
                    
                    print(f"Победа в комнате '{room['name']}'! Победитель: {username}")
                    
                    return jsonify({
                        'success': True,
                        'game_over': True,
                        'winner': username,
                        'total_collected': room['total_collected'],
                        'symbols_needed': room['symbols_needed']
                    })
                
                break
        
        return jsonify({
            'success': True,
            'game_over': False,
            'total_collected': room['total_collected'],
            'symbols_needed': room['symbols_needed'],
            'player_collected': room['players_data'][username]['collected']
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/start-game', methods=['POST'])
def start_game():
    try:
        data = request.get_json()
        room_id = data.get('room_id')
        host = data.get('host')
        
        if room_id not in rooms:
            return jsonify({'success': False, 'error': 'Комната не найдена'}), 404
        
        room = rooms[room_id]
        
        if room['creator'] != host:
            return jsonify({'success': False, 'error': 'Только создатель может начать игру'}), 400
        
        if len(room['players']) < 2:
            return jsonify({'success': False, 'error': 'Нужно минимум 2 игрока'}), 400
        
        room['status'] = 'playing'
        room['game_started'] = True
        
        print(f"Игра началась в комнате '{room['name']}'")
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
