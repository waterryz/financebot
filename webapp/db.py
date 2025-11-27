import psycopg2
import uuid
import bcrypt
from datetime import datetime


# ======================
# CONNECT
# ======================
def get_conn():
    return psycopg2.connect(
        host="localhost",
        database="finance_bot",
        user="postgres",
        password="Twolfsasha1",
        port=5432
    )


# ======================
# USERS
# ======================

def create_user(username, password):
    conn = get_conn()
    cur = conn.cursor()

    # хэшируем пароль
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        cur.execute("""
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
        """, (username, hashed))
    except Exception:
        conn.rollback()
        cur.close()
        conn.close()
        return False

    conn.commit()
    cur.close()
    conn.close()
    return True


def check_user(username, password):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT password_hash FROM users WHERE username=%s", (username,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return False

    hashed = row[0].encode()
    return bcrypt.checkpw(password.encode(), hashed)


def get_user_id(username):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id FROM users WHERE username=%s", (username,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row[0] if row else None


def get_username_by_id(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT username FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row[0] if row else None


# ======================
# TOKENS
# ======================

def generate_token(user_id):
    conn = get_conn()
    cur = conn.cursor()

    token = uuid.uuid4().hex
    cur.execute("INSERT INTO tokens (user_id, token) VALUES (%s, %s)", (user_id, token))

    conn.commit()
    cur.close()
    conn.close()
    return token


def get_user_id_from_token(token):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT user_id FROM tokens WHERE token=%s", (token,))
    row = cur.fetchone()

    cur.close()
    conn.close()
    return row[0] if row else None


# ======================
# PROFILE SETTINGS
# ======================

def update_username(user_id, new_username):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute("UPDATE users SET username=%s WHERE id=%s", (new_username, user_id))
    except psycopg2.errors.UniqueViolation:
        conn.rollback()
        cur.close()
        conn.close()
        return False

    conn.commit()
    cur.close()
    conn.close()
    return True


def update_password(user_id, old_password, new_password):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT password_hash FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    if not row:
        return False

    current_hash = row[0].encode()
    if not bcrypt.checkpw(old_password.encode(), current_hash):
        return False

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()

    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
    conn.commit()

    cur.close()
    conn.close()
    return True


def delete_user(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM tokens WHERE user_id=%s", (user_id,))
    cur.execute("DELETE FROM transactions WHERE user_id=%s", (user_id,))
    cur.execute("DELETE FROM categories WHERE user_id=%s", (user_id,))
    cur.execute("DELETE FROM users WHERE id=%s", (user_id,))

    conn.commit()
    cur.close()
    conn.close()


# ======================
# CATEGORIES
# ======================

def add_category(name, op_type):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO categories (name, type)
        VALUES (%s, %s)
    """, (name, op_type))

    conn.commit()
    cur.close()
    conn.close()



def get_categories(op_type):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name FROM categories
        WHERE type=%s
    """, (op_type,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



# ======================
# TRANSACTIONS
# ======================

def add_transaction(user_id, amount, op_type, category_id, description):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions (user_id, amount, type, category_id, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (user_id, amount, op_type, category_id, description))

    conn.commit()
    cur.close()
    conn.close()


def get_transactions(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.amount, t.type, c.name, t.description, t.created_at
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id=%s
        ORDER BY t.created_at DESC
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



# ======================
# BALANCE & STATS
# ======================

def get_balance(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT
        COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) -
        COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0)
        FROM transactions
        WHERE user_id=%s
    """, (user_id,))

    balance = cur.fetchone()[0]
    cur.close()
    conn.close()

    return float(balance)


def get_stats(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id=%s AND type='income'
    """, (user_id,))
    income = float(cur.fetchone()[0])

    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id=%s AND type='expense'
    """, (user_id,))
    expense = float(cur.fetchone()[0])

    cur.execute("""
        SELECT c.name, COALESCE(SUM(t.amount), 0)
        FROM transactions t
        JOIN categories c ON t.category_id=c.id
        WHERE t.user_id=%s AND t.type='expense'
        GROUP BY c.name
        ORDER BY SUM(t.amount) DESC
    """, (user_id,))
    cats = cur.fetchall()

    cur.close()
    conn.close()
    return income, expense, [(r[0], float(r[1])) for r in cats]

from datetime import timedelta

def add_wish(user_id, item, price, amount, unit):
    conn = get_conn()
    cur = conn.cursor()

    interval = f"{amount} {unit}"

    cur.execute("""
        INSERT INTO wish_timers (user_id, item, price, remind_at)
        VALUES (%s, %s, %s, NOW() + (%s)::interval)
    """, (user_id, item, price, interval))

    conn.commit()
    cur.close()
    conn.close()



def get_wishes(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, item, price, remind_at, cancelled
        FROM wish_timers
        WHERE user_id=%s AND cancelled = FALSE
        ORDER BY remind_at
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



def cancel_wish(wish_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM wish_timers
        WHERE id=%s AND user_id=%s
    """, (wish_id, user_id))

    conn.commit()
    cur.close()
    conn.close()



def postpone_wish(wish_id, user_id, days):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE wish_timers
        SET remind_at = NOW() + (%s || ' days')::interval
        WHERE id=%s AND user_id=%s
    """, (days, wish_id, user_id))

    conn.commit()
    cur.close()
    conn.close()


def get_due_wishes():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, user_id, item
        FROM wish_timers
        WHERE cancelled=FALSE AND remind_at <= NOW()
    """)

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows



# ======================
# INIT DB
# ======================
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            telegram_id BIGINT NOT NULL
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            token TEXT UNIQUE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            type VARCHAR(10) NOT NULL,
            user_id INTEGER REFERENCES users(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            amount NUMERIC(12,2),
            type VARCHAR(10),
            category_id INTEGER REFERENCES categories(id),
            description TEXT,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)
    # таблица отложенных покупок
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wish_timers (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            item TEXT NOT NULL,
            price NUMERIC(12,2),
            remind_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            cancelled BOOLEAN DEFAULT FALSE
        );
    """)


    conn.commit()
    cur.close()
    conn.close()



def get_telegram_chat_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT telegram_id FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None
def save_telegram_id(user_id, telegram_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE users SET telegram_id=%s WHERE id=%s",
        (telegram_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()


def get_telegram_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT telegram_id FROM users WHERE id=%s",
        (user_id,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

