from flask import Flask, request, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

def init_db():
    conn = sqlite3.connect('users.db')
    conn.execute('''CREATE TABLE IF NOT EXISTS users
                    (id INTEGER PRIMARY KEY AUTOINCREMENT,
                     username TEXT UNIQUE NOT NULL,
                     password_hash TEXT NOT NULL)''')
    conn.close()

@app.route('/')
def home():
    return 'Сервер работает!'

@app.route('/register', methods=['POST'])
def register():
    try:
        data = request.get_json()
        username = data.get('username')
        password = data.get('password')
        
        conn = sqlite3.connect('users.db')
        password_hash = generate_password_hash(password)
        conn.execute('INSERT INTO users (username, password_hash) VALUES (?, ?)',
                    (username, password_hash))
        conn.commit()
        conn.close()
        return jsonify({'success': True})
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
            return jsonify({'success': True})
        return jsonify({'success': False, 'error': 'Неверный логин или пароль'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    init_db()
    app.run()
