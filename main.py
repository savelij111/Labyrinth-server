import os
import logging
from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json
import random
import string
import time

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Логирование всех запросов (чтобы видеть 400)
@app.before_request
def log_request_info():
    logger.debug("="*50)
    logger.debug(f"📨 {request.method} {request.path}")
    logger.debug(f"📦 Headers: {dict(request.headers)}")
    logger.debug(f"📦 Raw data: {request.get_data(as_text=True)}")
    try:
        logger.debug(f"🔍 JSON: {request.get_json(silent=True)}")
    except:
        logger.debug("🔍 JSON: невалидный JSON")

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    try:
        conn = sqlite3.connect('users.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT UNIQUE NOT NULL,
                         password_hash TEXT NOT NULL,
                         skin TEXT DEFAULT '@',
                         skin_color TEXT DEFAULT '0,255,200',
                         coins INTEGER DEFAULT 0,
                         achievements TEXT DEFAULT '[]',
                         unlocked_colors TEXT DEFAULT '[]')''')
        conn.commit()
        conn.close()
        logger.info("✅ База данных готова")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка БД: {e}")
        return False

init_db()

# ==================== ОБРАБОТКА ОШИБОК ====================
@app.errorhandler(400)
def bad_request(e):
    logger.error(f"❌ 400 Ошибка: {e}")
    logger.error(f"📦 Request data: {request.get_data(as_text=True)}")
    return jsonify({'success': False, 'error': 'Bad request', 'details': str(e)}), 400

@app.errorhandler(500)
def internal_error(e):
    logger.error(f"❌ 500 Ошибка: {e}")
    return jsonify({'success': False, 'error': 'Internal server error'}), 500

# ==================== СТАРЫЕ МАРШРУТЫ ====================
@app.route('/')
def home():
    logger.info("🏠 Главная страница")
    return 'Сервер работает! Используй /register, /login, /user-data, /add-coins, /create-room, /join-room, /list-rooms'

@app.route('/register', methods=['POST'])
def register():
    logger.info("🔥 REGISTER: запрос получен")
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ REGISTER: нет JSON данных")
            return jsonify({'success': False, 'error': 'Нет JSON данных'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"👤 Username: {username}")
        logger.info(f"🔑 Password length: {len(password) if password else 0}")
        
        if not username or not password:
            logger.error("❌ REGISTER: пустые поля")
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400

        conn = sqlite3.connect('users.db')
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash, coins, achievements, unlocked_colors) VALUES (?, ?, 0, '[]', '[]')',
                    (username, password_hash))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ Регистрация успешна: {username}")
        return jsonify({'success': True})
        
    except sqlite3.IntegrityError:
        logger.error("❌ REGISTER: логин уже существует")
        return jsonify({'success': False, 'error': 'Логин уже существует'}), 400
    except Exception as e:
        logger.error(f"❌ REGISTER ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    logger.info("🔥 LOGIN: запрос получен")
    try:
        data = request.get_json()
        if not data:
            logger.error("❌ LOGIN: нет JSON данных")
            return jsonify({'success': False, 'error': 'Нет JSON данных'}), 400
            
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"👤 Username: {username}")
        
        if not username or not password:
            logger.error("❌ LOGIN: пустые поля")
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400

        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT password_hash, coins, achievements, unlocked_colors 
                               FROM users WHERE username = ?''', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            logger.info(f"✅ Вход успешен: {username}")
            return jsonify({
                'success': True,
                'coins': user[1],
                'achievements': json.loads(user[2]),
                'unlocked_colors': json.loads(user[3])
            })
        
        logger.error("❌ LOGIN: неверный пароль")
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 400
        
    except Exception as e:
        logger.error(f"❌ LOGIN ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ОСТАЛЬНЫЕ МАРШРУТЫ ====================
@app.route('/user-data', methods=['GET'])
def user_data():
    try:
        username = request.args.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'Нет username'}), 400
            
        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT skin, skin_color, coins, achievements, unlocked_colors 
                               FROM users WHERE username=?''', (username,)).fetchone()
        conn.close()
        if not user:
            return jsonify({'success': False, 'error': 'Не найден'}), 404
            
        return jsonify({
            'success': True,
            'skin': user[0],
            'skin_color': user[1],
            'coins': user[2],
            'achievements': json.loads(user[3]),
            'unlocked_colors': json.loads(user[4])
        })
    except Exception as e:
        logger.error(f"❌ USER-DATA ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/add-coins', methods=['POST'])
def add_coins():
    try:
        data = request.get_json()
        username = data.get('username')
        amount = data.get('amount', 0)
        
        conn = sqlite3.connect('users.db')
        conn.execute('UPDATE users SET coins = coins + ? WHERE username=?',
                    (amount, username))
        conn.commit()
        new_coins = conn.execute('SELECT coins FROM users WHERE username=?',
                                (username,)).fetchone()[0]
        conn.close()
        
        return jsonify({'success': True, 'coins': new_coins})
    except Exception as e:
        logger.error(f"❌ ADD-COINS ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== КОМНАТЫ ====================
rooms = {}

def generate_room_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

@app.route('/create-room', methods=['POST'])
def create_room():
    try:
        data = request.get_json()
        creator = data.get('creator')
        max_players = data.get('max_players', 2)
        difficulty = data.get('difficulty', 'easy')
        
        if not creator:
            return jsonify({'success': False, 'error': 'Укажи создателя'}), 400
        
        symbols_needed = {'easy': 5, 'medium': 8, 'hard': 12}.get(difficulty, 5)
        room_id = generate_room_id()
        
        rooms[room_id] = {
            'players': [creator],
            'max_players': max_players,
            'difficulty': difficulty,
            'symbols_needed': symbols_needed,
            'total_collected': 0,
            'status': 'waiting',
            'created': time.time()
        }
        
        logger.info(f"✅ Комната {room_id} создана игроком {creator}")
        return jsonify({
            'success': True,
            'room_id': room_id,
            'room': rooms[room_id]
        })
    except Exception as e:
        logger.error(f"❌ CREATE-ROOM ошибка: {e}")
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
        
        room['players'].append(username)
        logger.info(f"✅ {username} зашёл в комнату {room_id}")
        
        if len(room['players']) == room['max_players']:
            room['status'] = 'playing'
            logger.info(f"🎮 Игра началась в комнате {room_id}")
        
        return jsonify({'success': True, 'room': room})
    except Exception as e:
        logger.error(f"❌ JOIN-ROOM ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/list-rooms', methods=['GET'])
def list_rooms():
    try:
        available = [
            {
                'room_id': rid,
                'players': r['players'],
                'max_players': r['max_players'],
                'difficulty': r['difficulty'],
                'players_count': len(r['players'])
            }
            for rid, r in rooms.items()
            if r['status'] == 'waiting' and len(r['players']) < r['max_players']
        ]
        return jsonify({'success': True, 'rooms': available})
    except Exception as e:
        logger.error(f"❌ LIST-ROOMS ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    logger.info(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
