import psycopg2
import uuid
import bcrypt
from datetime import datetime, timedelta


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
        cur.close()
        conn.close()
        return False

    current_hash = row[0].encode()
    if not bcrypt.checkpw(old_password.encode(), current_hash):
        cur.close()
        conn.close()
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
# BALANCE & USER STATS
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


# ======================
# WISHLIST
# ======================

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
            telegram_id BIGINT
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
    cur.execute("""
        CREATE TABLE IF NOT EXISTS goals (
            id SERIAL PRIMARY KEY,
            user_id INT NOT NULL,
            name TEXT NOT NULL,
            target NUMERIC NOT NULL,
            saved NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
        );
    """)

    conn.commit()
    cur.close()
    conn.close()


# ======================
# TELEGRAM HELPERS
# ======================

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


# ======================
# ADMIN STUFF (LISTS, STATS, LOGS)
# ======================

def get_all_users():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT id, username FROM users ORDER BY id")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [dict(id=r[0], username=r[1]) for r in rows]


def get_all_transactions():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT t.id, t.amount, t.type, t.description, t.created_at, u.username
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        dict(id=r[0], amount=r[1], type=r[2],
             description=r[3], created_at=r[4], username=r[5])
        for r in rows
    ]


def get_admin_stats():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions")
    tx = cur.fetchone()[0]

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense'")
    expenses = cur.fetchone()[0] or 0

    cur.execute("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income'")
    income = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    return dict(
        total_users=users,
        total_transactions=tx,
        total_expenses=expenses,
        total_income=income
    )


def read_logs():
    try:
        with open("bot.log", "r", encoding="utf8") as f:
            return f.readlines()[-100:]
    except:
        return ["Лог-файл не найден"]


# ======================
# ADMINS TABLE
# ======================

def init_admin_table():
    conn = get_conn()
    cur = conn.cursor()

    # создаём таблицу, если нет
    cur.execute("""
        CREATE TABLE IF NOT EXISTS admins (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        );
    """)

    # всегда делаем (или обновляем) админа admin/admin
    pwd_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()

    cur.execute("""
        INSERT INTO admins (username, password_hash)
        VALUES (%s, %s)
        ON CONFLICT (username)
        DO UPDATE SET password_hash = EXCLUDED.password_hash
    """, ("admin", pwd_hash))

    print("⚙️ Админ admin/admin гарантированно создан/обновлён")

    conn.commit()
    cur.close()
    conn.close()


def get_admin(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash FROM admins WHERE username=%s",
        (username,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2]
    }


def check_admin_password(password, hash_):
    return bcrypt.checkpw(password.encode(), hash_.encode())
def get_month_summary(user_id):
    conn = get_conn()
    cur = conn.cursor()

    # доходы за месяц
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s
          AND type = 'income'
          AND created_at >= date_trunc('month', CURRENT_DATE);
    """, (user_id,))
    income = cur.fetchone()[0]

    # расходы за месяц
    cur.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s
          AND type = 'expense'
          AND created_at >= date_trunc('month', CURRENT_DATE);
    """, (user_id,))
    expense = cur.fetchone()[0]

    cur.close()
    conn.close()

    balance = income - expense
    return income, expense, balance
def get_top_categories(user_id, limit=3):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.name, SUM(t.amount) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
          AND t.type = 'expense'
          AND t.created_at >= date_trunc('month', CURRENT_DATE)
        GROUP BY c.name
        ORDER BY total DESC
        LIMIT %s;
    """, (user_id, limit))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows  # список: [("Еда", 5800), ("Авто", 3200), ...]
def get_last_transaction(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT t.amount, t.type, t.description, t.created_at, c.name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.created_at DESC
        LIMIT 1;
    """, (user_id,))

    row = cur.fetchone()

    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "amount": row[0],
        "type": row[1],
        "description": row[2],
        "date": row[3],
        "category": row[4],
    }

def add_goal(user_id, name, target):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO goals (user_id, name, target)
        VALUES (%s, %s, %s)
    """, (user_id, name, target))
    conn.commit()
    cur.close()
    conn.close()


def get_current_goal(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, target, saved
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """, (user_id,))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    id, name, target, saved = row
    percent = int((saved / target) * 100) if target > 0 else 0

    return {
        "id": id,
        "name": name,
        "target": target,
        "saved": saved,
        "percent": percent
    }
def add_to_goal(user_id, amount):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE goals
        SET saved = saved + %s
        WHERE id = (
            SELECT id FROM goals
            WHERE user_id = %s
            ORDER BY created_at DESC
            LIMIT 1
        );
    """, (amount, user_id))

    conn.commit()
    cur.close()
    conn.close()

def get_goals(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, target, saved, created_at
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC
    """, (user_id,))

    rows = cur.fetchall()

    cur.close()
    conn.close()

    goals = []
    for row in rows:
        goal_id, name, target, saved, created_at = row
        percent = int((saved / target) * 100) if target > 0 else 0

        goals.append({
            "id": goal_id,
            "name": name,
            "target": target,
            "saved": saved,
            "percent": percent,
            "date": created_at
        })

    return goals
def delete_goal(goal_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM goals
        WHERE id = %s AND user_id = %s
    """, (goal_id, user_id))

    conn.commit()
    cur.close()
    conn.close()
def update_goal(goal_id, user_id, name, target):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        UPDATE goals
        SET name = %s, target = %s
        WHERE id = %s AND user_id = %s
    """, (name, target, goal_id, user_id))

    conn.commit()
    cur.close()
    conn.close()

