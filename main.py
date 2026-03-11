import os
from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    try:
        conn = sqlite3.connect('users.db')
        conn.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                         username TEXT UNIQUE NOT NULL,
                         password_hash TEXT NOT NULL,
                         skin TEXT DEFAULT '@',
                         skin_color TEXT DEFAULT '0,255,200')''')
        conn.commit()
        conn.close()
        print("✅ База данных готова")
        return True
    except Exception as e:
        print(f"❌ Ошибка БД: {e}")
        return False

# ==================== МАРШРУТЫ ====================
@app.route('/')
def home():
    return 'Сервер работает! Используй /register, /login, /save-skin, /get-skin'

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
        
        print(f"✅ Новый пользователь: {username}")
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
        user = conn.execute('SELECT password_hash FROM users WHERE username = ?',
                           (username,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user[0], password):
            print(f"✅ Вход: {username}")
            return jsonify({'success': True})
        
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'}), 400
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/save-skin', methods=['POST'])
def save_skin():
    try:
        data = request.get_json()
        username = data.get('username')
        skin = data.get('skin')
        skin_color = data.get('skin_color')
        
        conn = sqlite3.connect('users.db')
        conn.execute('UPDATE users SET skin=?, skin_color=? WHERE username=?',
                    (skin, skin_color, username))
        conn.commit()
        conn.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-skin', methods=['GET'])
def get_skin():
    try:
        username = request.args.get('username')
        conn = sqlite3.connect('users.db')
        user = conn.execute('SELECT skin, skin_color FROM users WHERE username=?',
                           (username,)).fetchone()
        conn.close()
        if user:
            return jsonify({
                'success': True,
                'skin': user[0] or '@',
                'skin_color': user[1] or '0,255,200'
            })
        return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== ЗАПУСК ====================
if __name__ == '__main__':
    print("🚀 Запуск сервера...")
    if init_db():
        port = int(os.environ.get('PORT', 10000))
        print(f"🔌 Сервер слушает порт {port}")
        app.run(host='0.0.0.0', port=port)
    else:
        print("❌ Ошибка базы данных")
