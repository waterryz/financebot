import psycopg2
import uuid
import bcrypt
from datetime import datetime, timedelta


def get_conn():
    return psycopg2.connect(
        host="localhost",
        database="finance_bot",
        user="postgres",
        password="0120",
        port=5432,
    )


def create_user(username, password):
    conn = get_conn()
    cur = conn.cursor()

    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    try:
        cur.execute(
            """
            INSERT INTO users (username, password_hash)
            VALUES (%s, %s)
        """,
            (username, hashed),
        )
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


def generate_token(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("DELETE FROM tokens WHERE user_id = %s", (user_id,))

    token = uuid.uuid4().hex
    cur.execute(
        "INSERT INTO tokens (user_id, token) VALUES (%s, %s)", (user_id, token)
    )

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


def update_username(user_id, new_username):
    conn = get_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "UPDATE users SET username=%s WHERE id=%s", (new_username, user_id)
        )
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

    cur.execute(
        "UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id)
    )
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


def add_category(name, op_type):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO categories (name, type)
        VALUES (%s, %s)
    """,
        (name, op_type),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_categories(type, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, icon
        FROM categories
        WHERE type = %s AND user_id = %s
        ORDER BY id
    """, (type, user_id))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {"id": r[0], "name": r[1], "icon": r[2]}
        for r in rows
    ]


def add_category(user_id, name, type, icon):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO categories (name, type, icon, user_id)
        VALUES (%s, %s, %s, %s)
    """, (name, type, icon, user_id))

    conn.commit()
    cur.close()
    conn.close()


def add_transaction(user_id, amount, op_type, category_id, description):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        INSERT INTO transactions (user_id, amount, type, category_id, description)
        VALUES (%s, %s, %s, %s, %s)
    """,
        (user_id, amount, op_type, category_id, description),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_transactions(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT t.id,
               t.amount,
               t.type,
               t.description,
               t.created_at,
               c.name AS category
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.created_at DESC;
    """,
        (user_id,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    transactions = []

    for r in rows:
        dt = r[4]
        transactions.append(
            {
                "id": r[0],
                "amount": r[1],
                "type": r[2],
                "description": r[3] or "Без описания",
                "date": dt.strftime("%d.%m.%Y %H:%M"),
                "category": r[5] or "Без категории",
            }
        )

    return transactions


def get_balance(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT
        COALESCE(SUM(CASE WHEN type='income' THEN amount END), 0) -
        COALESCE(SUM(CASE WHEN type='expense' THEN amount END), 0)
        FROM transactions
        WHERE user_id=%s
    """,
        (user_id,),
    )

    balance = cur.fetchone()[0]
    cur.close()
    conn.close()

    return float(balance)


def get_stats(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id=%s AND type='income'
    """,
        (user_id,),
    )
    income = float(cur.fetchone()[0])

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id=%s AND type='expense'
    """,
        (user_id,),
    )
    expense = float(cur.fetchone()[0])

    cur.execute(
        """
        SELECT c.name, COALESCE(SUM(t.amount), 0)
        FROM transactions t
        JOIN categories c ON t.category_id=c.id
        WHERE t.user_id=%s AND t.type='expense'
        GROUP BY c.name
        ORDER BY SUM(t.amount) DESC
    """,
        (user_id,),
    )
    cats = cur.fetchall()

    cur.close()
    conn.close()
    return income, expense, [(r[0], float(r[1])) for r in cats]


def add_wish(user_id, item, price, amount, unit):
    conn = get_conn()
    cur = conn.cursor()

    interval = f"{amount} {unit}"

    cur.execute(
        """
        INSERT INTO wish_timers (user_id, item, price, remind_at)
        VALUES (%s, %s, %s, NOW() + (%s)::interval)
    """,
        (user_id, item, price, interval),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_wishes(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, item, price, remind_at, cancelled
        FROM wish_timers
        WHERE user_id=%s AND cancelled = FALSE
        ORDER BY remind_at
    """,
        (user_id,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "item": r[1],
            "price": float(r[2]) if r[2] else 0,
            "remind_at": r[3],
        }
        for r in rows
    ]


def cancel_wish(wish_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE wish_timers
        SET cancelled = TRUE
        WHERE id = %s AND user_id = %s
    """,
        (wish_id, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def postpone_wish(wish_id, user_id, days):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE wish_timers
        SET remind_at = NOW() + (%s || ' days')::interval
        WHERE id=%s AND user_id=%s
    """,
        (days, wish_id, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_due_wishes():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, user_id, item
        FROM wish_timers
        WHERE cancelled=FALSE AND remind_at <= NOW()
    """
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows


def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            telegram_id BIGINT,
            role VARCHAR(20) DEFAULT 'user'
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS tokens (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            token TEXT UNIQUE
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallets (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            name VARCHAR(50) NOT NULL,
            balance NUMERIC(12,2) DEFAULT 0,
            icon text
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id SERIAL PRIMARY KEY,
            name VARCHAR(50) NOT NULL,
            type VARCHAR(10) NOT NULL CHECK (type IN ('income','expense')),
            icon VARCHAR(10) NOT NULL,
            user_id INTEGER REFERENCES users(id)
        );
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            amount NUMERIC(12,2) NOT NULL,
            type VARCHAR(10) NOT NULL CHECK (type IN ('income','expense')),
            category_id INTEGER REFERENCES categories(id),
            wallet_id INTEGER REFERENCES wallets(id),
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
            user_id INTEGER REFERENCES users(id),
            name TEXT NOT NULL,
            target NUMERIC NOT NULL,
            saved NUMERIC DEFAULT 0,
            created_at TIMESTAMP DEFAULT NOW()
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
        (telegram_id, user_id),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_telegram_id(user_id):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT telegram_id FROM users WHERE id=%s",
        (user_id,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None


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
    cur.execute(
        """
        SELECT t.id, t.amount, t.type, t.description, t.created_at, u.username
        FROM transactions t
        JOIN users u ON t.user_id = u.id
        ORDER BY t.created_at DESC
    """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [
        dict(
            id=r[0],
            amount=float(r[1]),
            type=r[2],
            description=r[3],
            created_at=r[4].isoformat(),
            username=r[5],
        )
        for r in rows
    ]


def get_admin_stats():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) FROM users")
    users = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM transactions")
    tx = cur.fetchone()[0]

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='expense'"
    )
    expenses = cur.fetchone()[0] or 0

    cur.execute(
        "SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE type='income'"
    )
    income = cur.fetchone()[0] or 0

    cur.close()
    conn.close()

    return dict(
        total_users=users,
        total_transactions=tx,
        total_expenses=expenses,
        total_income=income,
    )


def read_logs():
    try:
        with open("bot.log", "r", encoding="utf8") as f:
            return f.readlines()[-100:]
    except Exception:
        return ["Лог-файл не найден"]


def get_admin(username):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, username, password_hash FROM admins WHERE username=%s",
        (username,),
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "username": row[1],
        "password_hash": row[2],
    }


def check_admin_password(password, hash_):
    return bcrypt.checkpw(password.encode(), hash_.encode())


def get_month_summary(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s AND type='income'
          AND created_at >= date_trunc('month', CURRENT_DATE)
    """,
        (user_id,),
    )
    income = float(cur.fetchone()[0] or 0)

    cur.execute(
        """
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE user_id = %s AND type='expense'
          AND created_at >= date_trunc('month', CURRENT_DATE)
    """,
        (user_id,),
    )
    expense = float(cur.fetchone()[0] or 0)

    balance = income - expense

    cur.close()
    conn.close()

    return income, expense, balance


def get_top_categories(user_id, limit=3):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT c.name, SUM(t.amount) AS total
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
          AND t.type = 'expense'
          AND t.created_at >= date_trunc('month', CURRENT_DATE)
        GROUP BY c.name
        ORDER BY total DESC
        LIMIT %s;
    """,
        (user_id, limit),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    return rows


def get_last_transaction(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT t.amount, t.type, t.description, t.created_at, c.name
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
        ORDER BY t.created_at DESC
        LIMIT 1;
    """,
        (user_id,),
    )

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
    cur.execute(
        """
        INSERT INTO goals (user_id, name, target)
        VALUES (%s, %s, %s)
    """,
        (user_id, name, target),
    )
    conn.commit()
    cur.close()
    conn.close()


def get_current_goal(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, target, saved
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1;
    """,
        (user_id,),
    )

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    goal_id, name, target, saved = row

    target = float(target)
    saved = float(saved)

    if target > 0:
        percent = round((saved / target) * 100, 1)
        if percent > 100:
            percent = 100
    else:
        percent = 0

    return {
        "id": goal_id,
        "name": name,
        "target": target,
        "saved": saved,
        "percent": percent,
    }


def add_to_goal(user_id, amount):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, saved, target
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC
        LIMIT 1
    """,
        (user_id,),
    )

    row = cur.fetchone()
    if not row:
        cur.close()
        conn.close()
        return

    goal_id, saved, target = row

    remaining = target - saved
    if remaining <= 0:
        cur.close()
        conn.close()
        return

    amount_to_add = min(amount, remaining)

    cur.execute(
        """
        UPDATE goals
        SET saved = saved + %s
        WHERE id = %s
    """,
        (amount_to_add, goal_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_goals(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT id, name, target, saved, created_at
        FROM goals
        WHERE user_id = %s
        ORDER BY created_at DESC
    """,
        (user_id,),
    )

    rows = cur.fetchall()

    cur.close()
    conn.close()

    goals = []
    for goal_id, name, target, saved, created_at in rows:
        if target > 0:
            percent = int((saved / target) * 100)
            if percent > 100:
                percent = 100
        else:
            percent = 0

        goals.append(
            {
                "id": goal_id,
                "name": name,
                "target": target,
                "saved": saved,
                "percent": percent,
                "date": created_at,
            }
        )

    return goals


def delete_goal(goal_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        DELETE FROM goals
        WHERE id = %s AND user_id = %s
    """,
        (goal_id, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def update_goal(goal_id, user_id, name, target):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE goals
        SET name = %s, target = %s
        WHERE id = %s AND user_id = %s
    """,
        (name, target, goal_id, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_daily_expenses(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        SELECT 
            TO_CHAR(created_at, 'DD') AS day,
            SUM(amount) 
        FROM transactions
        WHERE user_id = %s
          AND type = 'expense'
          AND created_at >= date_trunc('month', CURRENT_DATE)
        GROUP BY day
        ORDER BY day;
    """,
        (user_id,),
    )

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [(day, float(amount)) for day, amount in rows]


def set_user_role(user_id, role):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        """
        UPDATE users SET role=%s WHERE id=%s
    """,
        (role, user_id),
    )

    conn.commit()
    cur.close()
    conn.close()


def get_user_role(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT role FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()

    cur.close()
    conn.close()

    return row[0] if row else None


def get_weekly_money_stats(db):
    cur = db.cursor()
    cur.execute(
        """
        SELECT
            DATE(created_at),
            SUM(CASE WHEN type='income' THEN amount ELSE 0 END),
            SUM(CASE WHEN type='expense' THEN amount ELSE 0 END)
        FROM transactions
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """
    )

    rows = cur.fetchall()

    labels = [str(r[0]) for r in rows]
    income = [float(r[1]) for r in rows]
    expense = [float(r[2]) for r in rows]

    return labels, income, expense


def get_user_activity_week(db):
    cur = db.cursor()

    cur.execute(
        """
        SELECT DATE(created_at), COUNT(*)
        FROM transactions
        WHERE created_at >= NOW() - INTERVAL '7 days'
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """
    )

    rows = cur.fetchall()

    if not rows:
        return [], []

    labels = [r[0].isoformat() for r in rows]
    activity = [int(r[1]) for r in rows]

    return labels, activity


def get_top_expense_categories(db):
    cur = db.cursor()

    cur.execute(
        """
        SELECT c.name, SUM(t.amount)
        FROM transactions t
        JOIN categories c ON c.id = t.category_id
        WHERE t.type = 'expense'
        GROUP BY c.name
        ORDER BY SUM(t.amount) DESC
        LIMIT 5
    """
    )

    rows = cur.fetchall()

    if not rows:
        return [], []

    labels = [r[0] for r in rows]
    amounts = [float(r[1]) for r in rows]

    return labels, amounts


def add_income(user_id, amount, category_id, wallet_id, description):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO transactions (user_id, amount, type, category_id, wallet_id, description)
        VALUES (%s,%s,'income',%s,%s,%s)
    """, (user_id, amount, category_id, wallet_id, description))

    cur.execute("""
        UPDATE wallets SET balance = balance + %s
        WHERE id=%s AND user_id=%s
    """, (amount, wallet_id, user_id))

    conn.commit()
    cur.close()
    conn.close()


def add_expense(user_id, amount, category_id, wallet_id, description):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT balance FROM wallets WHERE id=%s AND user_id=%s", (wallet_id, user_id))
    balance = cur.fetchone()[0]

    if balance < amount:
        raise Exception("Недостаточно средств")

    cur.execute("""
        INSERT INTO transactions (user_id, amount, type, category_id, wallet_id, description)
        VALUES (%s,%s,'expense',%s,%s,%s)
    """, (user_id, amount, category_id, wallet_id, description))

    cur.execute("""
        UPDATE wallets SET balance = balance - %s
        WHERE id=%s AND user_id=%s
    """, (amount, wallet_id, user_id))

    conn.commit()
    cur.close()
    conn.close()


def get_wallets(user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, balance, icon
        FROM wallets
        WHERE user_id = %s
        ORDER BY id
    """, (user_id,))

    rows = cur.fetchall()
    cur.close()
    conn.close()

    return [
        {
            "id": r[0],
            "name": r[1],
            "balance": float(r[2]),
            "icon": r[3]
        }
        for r in rows
    ]


def get_category(category_id, user_id):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT id, name, type, icon
        FROM categories
        WHERE id = %s
          AND (user_id = %s OR user_id IS NULL)
    """, (category_id, user_id))

    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return None

    return {
        "id": row[0],
        "name": row[1],
        "type": row[2],
        "icon": row[3],
    }


def add_wallet(user_id, name, icon):
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
        INSERT INTO wallets (user_id, name, icon)
        VALUES (%s, %s, %s)
    """, (user_id, name, icon))

    conn.commit()
    cur.close()
    conn.close()

