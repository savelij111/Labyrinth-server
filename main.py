import os
import logging
from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json

# Настройка логирования
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    try:
        logger.info("🔄 Инициализация базы данных...")
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

# ==================== МАРШРУТЫ ====================
@app.route('/')
def home():
    logger.info("🏠 Главная страница запрошена")
    return 'Сервер работает! Используй /register, /login, /user-data, /add-coins'

@app.route('/register', methods=['POST'])
def register():
    logger.info("🔥 REGISTER: запрос получен")
    try:
        data = request.get_json()
        logger.info(f"📦 REGISTER data: {data}")
        
        if not data:
            logger.error("❌ REGISTER: нет JSON данных")
            return jsonify({'success': False, 'error': 'Нет данных'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"👤 REGISTER username: {username}")
        logger.info(f"🔑 REGISTER password length: {len(password) if password else 0}")
        
        if not username or not password:
            logger.error("❌ REGISTER: пустые поля")
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400
        
        conn = sqlite3.connect('users.db')
        logger.info("💾 REGISTER: соединение с БД успешно")
        
        password_hash = generate_password_hash(password)
        conn.execute('''INSERT INTO users 
                        (username, password_hash, coins, achievements, unlocked_colors) 
                        VALUES (?, ?, 0, '[]', '[]')''',
                    (username, password_hash))
        conn.commit()
        conn.close()
        
        logger.info(f"✅ REGISTER: пользователь {username} создан")
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
        logger.info(f"📦 LOGIN data: {data}")
        
        if not data:
            logger.error("❌ LOGIN: нет JSON данных")
            return jsonify({'success': False, 'error': 'Нет данных'}), 400
        
        username = data.get('username')
        password = data.get('password')
        
        logger.info(f"👤 LOGIN username: {username}")
        
        if not username or not password:
            logger.error("❌ LOGIN: пустые поля")
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400
        
        conn = sqlite3.connect('users.db')
        logger.info("💾 LOGIN: соединение с БД успешно")
        
        user = conn.execute('''SELECT password_hash, coins, achievements, unlocked_colors 
                               FROM users WHERE username = ?''', (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            logger.info(f"✅ LOGIN: успешный вход {username}")
            return jsonify({
                'success': True,
                'coins': user[1],
                'achievements': json.loads(user[2]),
                'unlocked_colors': json.loads(user[3])
            })
        
        logger.error("❌ LOGIN: неверный пароль или пользователь не найден")
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 400
        
    except Exception as e:
        logger.error(f"❌ LOGIN ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user-data', methods=['GET'])
def user_data():
    try:
        username = request.args.get('username')
        logger.info(f"📊 USER-DATA для {username}")
        
        if not username:
            return jsonify({'success': False, 'error': 'Нет username'}), 400
        
        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT skin, skin_color, coins, achievements, unlocked_colors 
                               FROM users WHERE username=?''', (username,)).fetchone()
        conn.close()
        
        if not user:
            logger.error(f"❌ USER-DATA: пользователь {username} не найден")
            return jsonify({'success': False, 'error': 'Не найден'}), 404
        
        logger.info(f"✅ USER-DATA: данные для {username} получены")
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
        
        logger.info(f"💰 ADD-COINS: {username} +{amount}")
        
        conn = sqlite3.connect('users.db')
        conn.execute('UPDATE users SET coins = coins + ? WHERE username=?',
                    (amount, username))
        conn.commit()
        new_coins = conn.execute('SELECT coins FROM users WHERE username=?',
                                (username,)).fetchone()[0]
        conn.close()
        
        logger.info(f"✅ ADD-COINS: новый баланс {new_coins}")
        return jsonify({'success': True, 'coins': new_coins})
    except Exception as e:
        logger.error(f"❌ ADD-COINS ошибка: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    logger.info("🚀 Запуск сервера...")
    if init_db():
        port = int(os.environ.get('PORT', 10000))
        logger.info(f"🔌 Сервер слушает порт {port}")
        app.run(host='0.0.0.0', port=port)
    else:
        logger.error("❌ Ошибка базы данных")
