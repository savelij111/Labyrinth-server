import os
from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
import json

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
                     unlocked_colors TEXT DEFAULT '[]')''')
    conn.commit()
    conn.close()
    print("✅ База данных готова")

init_db()

# ==================== МАРШРУТЫ ====================
@app.route('/')
def home():
    return 'Сервер работает! Используй /register, /login, /user-data, /add-coins'

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        if not username or not password:
            return jsonify({'success': False, 'error': 'Заполни все поля'}), 400

        conn = sqlite3.connect('users.db')
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, password_hash))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'Логин уже существует'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')

        conn = sqlite3.connect('users.db')
        user = conn.execute('''SELECT password_hash, coins, achievements, unlocked_colors 
                               FROM users WHERE username = ?''', (username,)).fetchone()
        conn.close()

        if user and check_password_hash(user[0], password):
            return jsonify({
                'success': True,
                'coins': user[1],
                'achievements': json.loads(user[2]),
                'unlocked_colors': json.loads(user[3])
            })
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/user-data', methods=['GET'])
def user_data():
    try:
        username = request.args.get('username')
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
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10000))
    print(f"🚀 Сервер запущен на порту {port}")
    app.run(host='0.0.0.0', port=port)
