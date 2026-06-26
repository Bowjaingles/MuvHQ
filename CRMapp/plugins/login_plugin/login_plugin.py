from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import LoginManager, login_user, logout_user, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3, os

login_bp = Blueprint('login_plugin', __name__, template_folder='templates')

DB_FILE = os.path.join(os.path.dirname(__file__), "login_plugin.db")

login_manager = LoginManager()
login_manager.login_view = 'login_plugin.login'

class User(UserMixin):
    def __init__(self, id_, username):
        self.id = id_
        self.username = username

@login_manager.user_loader
def load_user(user_id):
    with sqlite3.connect(DB_FILE) as conn:
        user = conn.execute("SELECT id, username FROM users WHERE id=?", (user_id,)).fetchone()
        if user:
            return User(user[0], user[1])
    return None

def init_db():
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT
            )
        ''')

@login_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        with sqlite3.connect(DB_FILE) as conn:
            user = conn.execute("SELECT id, password FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user[1], password):
            login_user(User(user[0], username))
            return redirect(url_for('leads_central.index'))
        return "Invalid login", 401
    return render_template('login.html')

@login_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login_plugin.login'))

@login_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        hashed_password = generate_password_hash(password)

        try:
            with sqlite3.connect(DB_FILE) as conn:
                conn.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                             (username, hashed_password))
            return redirect(url_for('login_plugin.login'))
        except sqlite3.IntegrityError:
            return "Username already taken", 409

    return render_template('signup.html')


def init_plugin(app):
    init_db()

    app.secret_key = 'christiskinginfinity'  # Set the secret key here
    login_manager.init_app(app)
    app.register_blueprint(login_bp)