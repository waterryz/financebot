from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates



import os
from webapp.db import get_goals, delete_goal, update_goal

from webapp.db import (
    # init
    init_db,
    init_admin_table,

    # users
    create_user,
    check_user,
    get_user_id,
    generate_token,
    get_user_id_from_token,
    get_username_by_id,
    update_username,
    update_password,
    delete_user,

    # финансы
    add_category,
    get_categories,
    add_transaction,
    get_transactions,
    get_stats,          # пользовательская статистика (по user_id)
    get_balance,
    get_month_summary,
    get_top_categories,
    get_last_transaction,
    add_goal,
    get_current_goal,
    add_to_goal,

    # отложенные покупки
    get_wishes,
    add_wish,
    cancel_wish,
    postpone_wish,

    # админка
    get_admin,
    check_admin_password,
    get_all_users,
    get_all_transactions,
    get_admin_stats,    # общая статистика для админа
    read_logs,
)
from webapp.db import get_conn
app = FastAPI()

# ========================
#   С Т А Т И К А  /  Ш А Б Л О Н Ы
# ========================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="webapp/templates")


# ========================
#   С Т А Р Т А П
# ========================

@app.on_event("startup")
def startup():
    init_db()
    init_admin_table()   # создаст таблицу admins и дефолтного админа admin/admin
    print("✅ DB и админка инициализированы")


# ========================
#   Р О О Т
# ========================

@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/login")


# ========================
#   Р Е Г И С Т Р А Ц И Я
# ========================

@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.post("/register", response_class=HTMLResponse)
def register_user(request: Request, username: str = Form(...), password: str = Form(...)):
    ok = create_user(username, password)
    if not ok:
        return templates.TemplateResponse("register.html", {
            "request": request,
            "error": "Логин уже занят"
        })
    return RedirectResponse("/login", status_code=302)


# ========================
#   Л О Г И Н  П О Л Ь З О В А Т Е Л Я
# ========================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login", response_class=HTMLResponse)
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    ok = check_user(username, password)
    if not ok:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": "Неверный логин или пароль"
        })

    user_id = get_user_id(username)
    token = generate_token(user_id)

    return RedirectResponse(f"/home?token={token}", status_code=302)


# ========================
#   Г Л А В Н А Я
# ========================

@app.get("/home", response_class=HTMLResponse)
def home(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    username = get_username_by_id(user_id)
    balance = get_balance(user_id)

    # Блок 1
    month_income, month_expense, month_balance = get_month_summary(user_id)

    # Блок 2
    top_categories = get_top_categories(user_id)

    # Блок 3
    last_transaction = get_last_transaction(user_id)

    # Блок 4 — цель
    goal = get_current_goal(user_id)

    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username,
        "balance": balance,
        "token": token,

        # блок 1
        "month_income": month_income,
        "month_expense": month_expense,
        "month_balance": month_balance,

        # блок 2
        "top_categories": top_categories,

        # блок 3
        "last_transaction": last_transaction,

        # блок 4
        "goal": goal
    })


# ========================
#       П Р О Ф И Л Ь
# ========================

@app.get("/profile", response_class=HTMLResponse)
def profile(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    username = get_username_by_id(user_id)

    return templates.TemplateResponse("profile.html", {
        "request": request,
        "username": username,
        "token": token
    })


# ========================
#    Н А С Т Р О Й К И
# ========================

@app.get("/settings", response_class=HTMLResponse)
def settings(request: Request, token: str):
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "token": token
    })


# ========================
#   С М Е Н А  Л О Г И Н А
# ========================

@app.get("/change_username", response_class=HTMLResponse)
def change_username_page(request: Request, token: str):
    return templates.TemplateResponse("change_username.html", {
        "request": request,
        "token": token
    })


@app.post("/change_username", response_class=HTMLResponse)
def change_username(request: Request, token: str, new_username: str = Form(...)):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    ok = update_username(user_id, new_username)
    if not ok:
        return templates.TemplateResponse("change_username.html", {
            "request": request,
            "token": token,
            "error": "Логин уже используется"
        })

    return RedirectResponse(f"/profile?token={token}", status_code=302)


# ========================
#   С М Е Н А  П А Р О Л Я
# ========================

@app.get("/change_password", response_class=HTMLResponse)
def change_password_page(request: Request, token: str):
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "token": token
    })


@app.post("/change_password", response_class=HTMLResponse)
def change_password(
    request: Request,
    token: str,
    old_password: str = Form(...),
    new_password: str = Form(...)
):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    ok = update_password(user_id, old_password, new_password)
    if not ok:
        return templates.TemplateResponse("change_password.html", {
            "request": request,
            "token": token,
            "error": "Старый пароль неверный"
        })

    return RedirectResponse(f"/profile?token={token}", status_code=302)


# ========================
#  У Д А Л Е Н И Е  А К К А У Н Т А
# ========================

@app.get("/delete_account", response_class=HTMLResponse)
def delete_page(request: Request, token: str):
    return templates.TemplateResponse("delete_account.html", {
        "request": request,
        "token": token
    })


@app.get("/delete_confirm")
def delete_confirm(token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    delete_user(user_id)

    return RedirectResponse("/register", status_code=302)


# ========================
#   Д О Б А В И Т Ь  Р А С Х О Д
# ========================

@app.get("/add_expense", response_class=HTMLResponse)
def add_expense_page(request: Request, token: str):
    cats = get_categories("expense")

    return templates.TemplateResponse("add_expense.html", {
        "request": request,
        "token": token,
        "categories": cats
    })


@app.post("/add_expense", response_class=HTMLResponse)
def add_expense(
    request: Request,
    token: str,
    amount: float = Form(...),
    category_id: int = Form(...),
    description: str = Form("")
):
    user_id = get_user_id_from_token(token)
    add_transaction(user_id, amount, "expense", category_id, description)

    return RedirectResponse(f"/home?token={token}", status_code=302)


# ========================
#   Д О Б А В И Т Ь  Д О Х О Д
# ========================

@app.get("/add_income", response_class=HTMLResponse)
def add_income_page(request: Request, token: str):
    cats = get_categories("income")

    return templates.TemplateResponse("add_income.html", {
        "request": request,
        "token": token,
        "categories": cats
    })


@app.post("/add_income", response_class=HTMLResponse)
def add_income(
    request: Request,
    token: str,
    amount: float = Form(...),
    category_id: int = Form(...),
    description: str = Form("")
):
    user_id = get_user_id_from_token(token)

    add_transaction(user_id, amount, "income", category_id, description)

    # NEW: Добавляем в текущую цель
    add_to_goal(user_id, amount)

    return RedirectResponse(f"/home?token={token}", status_code=302)



# ========================
#   И С Т О Р И Я
# ========================

@app.get("/history", response_class=HTMLResponse)
def history(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    items = get_transactions(user_id)

    return templates.TemplateResponse("history.html", {
        "request": request,
        "token": token,
        "items": items
    })


# ========================
#   С Т А Т И С Т И К А  (П О Л Ь З О В А Т Е Л Ь)
# ========================

@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    income, expense, cat_stats = get_stats(user_id)

    labels = [row[0] for row in cat_stats]
    values = [float(row[1]) for row in cat_stats]

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "token": token,
        "income": float(income),
        "expense": float(expense),
        "labels": labels,
        "values": values
    })


# ========================
#   О Т Л О Ж Е Н Н Ы Е  П О К У П К И
# ========================

@app.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    wishes = get_wishes(user_id)

    return templates.TemplateResponse("wishlist.html", {
        "request": request,
        "token": token,
        "items": wishes
    })


@app.get("/add_wish", response_class=HTMLResponse)
def add_wish_page(request: Request, token: str):
    return templates.TemplateResponse("add_wish.html", {
        "request": request,
        "token": token
    })


@app.post("/add_wish", response_class=HTMLResponse)
def add_wish_post(
    request: Request,
    token: str,
    item: str = Form(...),
    price: float = Form(0),
    amount: int = Form(...),
    unit: str = Form(...)
):
    user_id = get_user_id_from_token(token)
    add_wish(user_id, item, price, amount, unit)

    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


@app.get("/cancel_wish")
def cancel_wish_route(token: str, id: int):
    user_id = get_user_id_from_token(token)
    cancel_wish(id, user_id)
    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


@app.get("/postpone_wish")
def postpone_wish_route(token: str, id: int, days: int):
    user_id = get_user_id_from_token(token)
    postpone_wish(id, user_id, days)
    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


# ========================
#   А Д М И Н К А  —  Л О Г И Н
# ========================

@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request):
    return templates.TemplateResponse("admin_login.html", {
        "request": request
    })


@app.post("/admin/login", response_class=HTMLResponse)
def admin_login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...)
):
    admin = get_admin(username)
    if not admin or not check_admin_password(password, admin["password_hash"]):
        return templates.TemplateResponse("admin_login.html", {
            "request": request,
            "error": "Неверный логин или пароль"
        })

    # Простейший вариант "сессии" — передаём имя админа в query-параметре
    return RedirectResponse(f"/admin?admin={username}", status_code=302)


def is_admin_name(admin_name: str) -> bool:
    if not admin_name:
        return False
    return get_admin(admin_name) is not None


# ========================
#   А Д М И Н К А  —  С Т Р А Н И Ц Ы
# ========================

@app.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, admin: str):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    return templates.TemplateResponse("admin_home.html", {
        "request": request,
        "admin_name": admin
    })


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, admin: str):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    users = get_all_users()

    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "admin_name": admin,
        "users": users
    })


@app.get("/admin/transactions", response_class=HTMLResponse)
def admin_transactions_page(request: Request, admin: str):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    tx = get_all_transactions()

    return templates.TemplateResponse("admin_transactions.html", {
        "request": request,
        "admin_name": admin,
        "transactions": tx
    })


@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats_page(request: Request, admin: str):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    st = get_admin_stats()

    # соберём данные для графиков
    conn = get_conn()
    cur = conn.cursor()

    # категории расходов
    cur.execute("""
        SELECT c.name, SUM(t.amount)
        FROM transactions t
        JOIN categories c ON t.category_id = c.id
        WHERE t.type='expense'
        GROUP BY c.name
    """)
    cat_rows = cur.fetchall()

    category_names = [r[0] for r in cat_rows]
    category_values = [float(r[1]) for r in cat_rows]

    # Динамика доходов и расходов по дням
    cur.execute("""
        SELECT DATE(created_at), 
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END) AS expense
        FROM transactions
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """)
    timeline = cur.fetchall()

    timeline_dates = [str(r[0]) for r in timeline]
    timeline_income = [float(r[1]) for r in timeline]
    timeline_expense = [float(r[2]) for r in timeline]

    cur.close()
    conn.close()

    return templates.TemplateResponse("admin_stats.html", {
        "request": request,
        "admin_name": admin,
        **st,
        "category_names": category_names,
        "category_values": category_values,
        "timeline_dates": timeline_dates,
        "timeline_income": timeline_income,
        "timeline_expense": timeline_expense
    })



@app.get("/admin/logs", response_class=HTMLResponse)
def admin_logs_page(request: Request, admin: str):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    logs = read_logs()

    return templates.TemplateResponse("admin_logs.html", {
        "request": request,
        "admin_name": admin,
        "logs": logs
    })
@app.get("/add_goal", response_class=HTMLResponse)
def add_goal_page(request: Request, token: str):
    return templates.TemplateResponse("add_goal.html", {
        "request": request,
        "token": token
    })
@app.post("/add_goal", response_class=HTMLResponse)
def add_goal_post(request: Request, token: str, name: str = Form(...), target: float = Form(...)):
    user_id = get_user_id_from_token(token)
    add_goal(user_id, name, target)
    return RedirectResponse(f"/home?token={token}", status_code=302)
@app.get("/goals", response_class=HTMLResponse)
def goals_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    goals = get_goals(user_id)

    return templates.TemplateResponse("goals.html", {
        "request": request,
        "token": token,
        "goals": goals
    })
@app.get("/goal_delete")
def goal_delete(token: str, id: int):
    user_id = get_user_id_from_token(token)
    delete_goal(id, user_id)
    return RedirectResponse(f"/goals?token={token}", status_code=302)
@app.get("/goal_edit", response_class=HTMLResponse)
def goal_edit_page(request: Request, token: str, id: int):
    user_id = get_user_id_from_token(token)
    goals = get_goals(user_id)

    goal = next((g for g in goals if g["id"] == id), None)

    return templates.TemplateResponse("goal_edit.html", {
        "request": request,
        "token": token,
        "goal": goal
    })
@app.post("/goal_edit", response_class=HTMLResponse)
def goal_edit(request: Request, token: str, id: int, name: str = Form(...), target: float = Form(...)):
    user_id = get_user_id_from_token(token)
    update_goal(id, user_id, name, target)
    return RedirectResponse(f"/goals?token={token}", status_code=302)

from webapp.db import get_username_by_id, get_transactions, get_conn, delete_user


@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
def admin_user_page(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    conn = get_conn()
    cur = conn.cursor()

    # Информация о пользователе
    cur.execute("SELECT id, username, created_at FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()

    if not row:
        return HTMLResponse("<h1>Пользователь не найден</h1>", status_code=404)

    user = {
        "id": row[0],
        "username": row[1],
        "created_at": row[2]
    }

    # Количество транзакций
    cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id=%s", (user_id,))
    tx_count = cur.fetchone()[0]

    conn.close()

    return templates.TemplateResponse("admin_user_settings.html", {
        "request": request,
        "admin_name": admin,
        "user": user,
        "transactions_count": tx_count
    })
@app.get("/admin/user/{user_id}/edit", response_class=HTMLResponse)
def admin_edit_user_page(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    username = get_username_by_id(user_id)

    return templates.TemplateResponse("admin_edit_user.html", {
        "request": request,
        "admin_name": admin,
        "user_id": user_id,
        "username": username
    })


@app.post("/admin/user/{user_id}/edit")
def admin_edit_user(request: Request, admin: str, user_id: int, new_username: str = Form(...)):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    ok = update_username(user_id, new_username)

    if not ok:
        return HTMLResponse("<h1>Ошибка: логин уже занят</h1>")

    return RedirectResponse(f"/admin/user/{user_id}?admin={admin}", status_code=302)
@app.get("/admin/user/{user_id}/delete")
def admin_delete_user(admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    delete_user(user_id)

    return RedirectResponse(f"/admin/users?admin={admin}", status_code=302)
@app.get("/admin/user/{user_id}/transactions", response_class=HTMLResponse)
def admin_user_transactions(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    tx = get_transactions(user_id)

    return templates.TemplateResponse("admin_user_transactions.html", {
        "request": request,
        "admin_name": admin,
        "transactions": tx,
        "user_id": user_id
    })
@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
def admin_user_page(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, username, created_at FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()

    if not row:
        return HTMLResponse("<h1>Пользователь не найден</h1>", status_code=404)

    user = {"id": row[0], "username": row[1], "created_at": row[2]}

    cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id=%s", (user_id,))
    tx_count = cur.fetchone()[0]

    conn.close()

    return templates.TemplateResponse(
        "admin_user_settings.html",
        {
            "request": request,
            "admin_name": admin,
            "user": user,
            "transactions_count": tx_count
        }
    )
@app.get("/admin/user/{user_id}/edit", response_class=HTMLResponse)
def admin_edit_user_page(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    username = get_username_by_id(user_id)

    return templates.TemplateResponse("admin_edit_user.html", {
        "request": request,
        "admin_name": admin,
        "user_id": user_id,
        "username": username
    })


@app.post("/admin/user/{user_id}/edit")
def admin_edit_user(request: Request, admin: str, user_id: int, new_username: str = Form(...)):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    ok = update_username(user_id, new_username)

    if not ok:
        return HTMLResponse("<h1>Ошибка: логин уже занят</h1>")

    return RedirectResponse(f"/admin/user/{user_id}?admin={admin}", status_code=302)
@app.get("/admin/user/{user_id}/reset_password", response_class=HTMLResponse)
def admin_reset_pass(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    new_password = "123456"

    conn = get_conn()
    cur = conn.cursor()
    import bcrypt

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))
    conn.commit()
    cur.close()
    conn.close()

    username = get_username_by_id(user_id)

    return templates.TemplateResponse("admin_password_reset.html", {
        "request": request,
        "admin_name": admin,
        "user_id": user_id,
        "username": username,
        "new_password": new_password
    })


    return HTMLResponse(f"<h1>Пароль сброшен. Новый пароль: {new_password}</h1>")
@app.get("/admin/user/{user_id}/transactions", response_class=HTMLResponse)
def admin_user_transactions(request: Request, admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    tx = get_transactions(user_id)  # список ТРАНЗАКЦИЙ из db.py

    return templates.TemplateResponse("admin_user_transactions.html", {
        "request": request,
        "admin_name": admin,
        "transactions": tx,
        "user_id": user_id
    })
@app.get("/admin/user/{user_id}/delete")
def admin_delete_user(admin: str, user_id: int):
    if not is_admin_name(admin):
        return RedirectResponse("/admin/login")

    delete_user(user_id)

    return RedirectResponse(f"/admin/users?admin={admin}", status_code=302)
