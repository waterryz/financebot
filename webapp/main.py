from fastapi import FastAPI, Request, Form, APIRouter
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import os
from dotenv import load_dotenv
load_dotenv()
from openai import OpenAI
import webapp.db as db
def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY not set")
    return OpenAI(api_key=api_key)
from webapp.db import get_conn, init_db
from webapp.db import (
    create_user,
    check_user,
    get_user_id,
    generate_token,
    get_user_id_from_token,
    get_username_by_id,
    update_username,
    update_password,
    delete_user,
    get_wallets,
    add_wallet,
)

from webapp.db import (
    add_category,
    get_categories,
    add_transaction,
    get_transactions,
    get_stats,
    get_balance,
    get_month_summary,
    get_top_categories,
    get_last_transaction,
    add_goal,
    get_current_goal,
    add_to_goal,
    get_daily_expenses,
    get_category
)

from webapp.db import get_goals, delete_goal, update_goal

from webapp.db import (
    get_wishes,
    add_wish,
    cancel_wish,
    postpone_wish,
)

from webapp.db import (
    get_admin,
    check_admin_password,
    get_all_users,
    get_all_transactions,
    get_admin_stats,
    read_logs,
    get_user_role,
    get_weekly_money_stats,
    get_user_activity_week,
    get_top_expense_categories,
)

app = FastAPI()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory="webapp/templates")

@app.on_event("startup")
def startup():
    init_db()
    print("✅ DB инициализирована")

@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/login")


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

    role = get_user_role(user_id)
    if role == "admin":
        return RedirectResponse(f"/admin?token={token}", status_code=302)

    return RedirectResponse(f"/home?token={token}", status_code=302)


@app.get("/home", response_class=HTMLResponse)
def home(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    username = get_username_by_id(user_id)
    wallets = get_wallets(user_id)

    total_balance = sum(w["balance"] for w in wallets)

    wallets = get_wallets(user_id)
    income_categories = get_categories("income", user_id)
    expense_categories = get_categories("expense", user_id)

    month_income, month_expense, month_balance = get_month_summary(user_id)
    top_categories = get_top_categories(user_id)
    last_transaction = get_last_transaction(user_id)
    goal = get_current_goal(user_id)

    return templates.TemplateResponse(
        "home.html",
        {
            "request": request,
            "username": username,
            "token": token,
            "wallets": wallets,
            "income_categories": income_categories,
            "expense_categories": expense_categories,

            # ⬇️ ВАЖНО
            "total_balance": total_balance,

            "month_income": month_income,
            "month_expense": month_expense,
            "month_balance": month_balance,
            "top_categories": top_categories,
            "last_transaction": last_transaction,
            "goal": goal,
        }
    )


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


@app.get("/settings")
def settings_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    username = get_username_by_id(user_id)
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "token": token,
        "username": username
    })


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

@app.get("/change_password", response_class=HTMLResponse)
def change_password_page(request: Request, token: str):
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "token": token
    })


@app.post("/change_password", response_class=HTMLResponse)
def change_password(request: Request, token: str, old_password: str = Form(...), new_password: str = Form(...)):
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


@app.get("/add_expense", response_class=HTMLResponse)
def add_expense_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    cats = get_categories("expense", user_id)

    return templates.TemplateResponse("add_expense.html", {
        "request": request,
        "token": token,
        "categories": cats,
        "current_page": "add_expense"
    })


@app.post("/add_expense", response_class=HTMLResponse)
def add_expense(request: Request, token: str, amount: float = Form(...),
                category_id: int = Form(...), description: str = Form("")):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    add_transaction(user_id, amount, "expense", category_id, description)
    return RedirectResponse(f"/home?token={token}", status_code=302)

@app.get("/add_income", response_class=HTMLResponse)
def add_income_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    cats = get_categories("income", user_id)

    return templates.TemplateResponse("add_income.html", {
        "request": request,
        "token": token,
        "categories": cats,
        "current_page": "add_income"
    })


@app.post("/add_income", response_class=HTMLResponse)
def add_income(request: Request, token: str, amount: float = Form(...),
               category_id: int = Form(...), description: str = Form("")):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    add_transaction(user_id, amount, "income", category_id, description)
    return RedirectResponse(f"/home?token={token}", status_code=302)


@app.get("/history", response_class=HTMLResponse)
def history_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    transactions = get_transactions(user_id)

    return templates.TemplateResponse("history.html", {
        "request": request,
        "token": token,
        "transactions": transactions,
        "current_page": "history"
    })


@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    income, expense, balance = get_month_summary(user_id)
    top_categories = get_top_categories(user_id)
    last_transaction = get_last_transaction(user_id)
    daily_expenses = get_daily_expenses(user_id)

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "token": token,
        "current_page": "stats",
        "stats": {
            "total_income": income,
            "total_expense": expense,
            "balance": balance,
            "top_categories": top_categories,
            "last_transaction": last_transaction,
            "daily_expenses": daily_expenses
        }
    })


@app.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    wishes = get_wishes(user_id)

    return templates.TemplateResponse("wishlist.html", {
        "request": request,
        "token": token,
        "wishes": wishes,
        "current_page": "wishlist"
    })


@app.get("/add_wish", response_class=HTMLResponse)
def add_wish_page(request: Request, token: str):
    return templates.TemplateResponse("add_wish.html", {
        "request": request,
        "token": token,
        "current_page": "add_wish"
    })


@app.post("/add_wish", response_class=HTMLResponse)
def add_wish_post(request: Request, token: str,
                  item: str = Form(...), price: float = Form(0),
                  amount: int = Form(...), unit: str = Form(...)):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    add_wish(user_id, item, price, amount, unit)
    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


@app.get("/cancel_wish")
def cancel_wish_route(token: str, id: int):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    cancel_wish(id, user_id)
    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


@app.get("/postpone_wish")
def postpone_wish_route(token: str, id: int, days: int):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    postpone_wish(id, user_id, days)
    return RedirectResponse(f"/wishlist?token={token}", status_code=302)


def admin_required(token: str):
    user_id = get_user_id_from_token(token)
    return user_id and get_user_role(user_id) == "admin"


@app.get("/admin")
def admin_home(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    db = get_conn()
    stats = get_admin_stats()
    week_labels, income_data, expense_data = get_weekly_money_stats(db)
    activity_labels, activity_data = get_user_activity_week(db)
    top_cat_labels, top_cat_values = get_top_expense_categories(db)
    db.close()

    return templates.TemplateResponse("admin_home.html", {
        "request": request,
        "token": token,
        "current_page": "admin_home",
        "stats": stats,
        "week_labels": week_labels,
        "income_data": income_data,
        "expense_data": expense_data,
        "activity_labels": activity_labels,
        "activity_data": activity_data,
        "top_cat_labels": top_cat_labels,
        "top_cat_values": top_cat_values,
    })


@app.get("/admin/users", response_class=HTMLResponse)
def admin_users(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    users = get_all_users()
    return templates.TemplateResponse("admin_users.html", {
        "request": request,
        "token": token,
        "users": users,
        "current_page": "admin_users"
    })


@app.get("/admin/user/{user_id}", response_class=HTMLResponse)
def admin_user_page(request: Request, token: str, user_id: int):
    if not admin_required(token):
        return RedirectResponse("/home")

    conn = get_conn()
    cur = conn.cursor()

    cur.execute("SELECT id, username, created_at FROM users WHERE id=%s", (user_id,))
    row = cur.fetchone()

    if not row:
        cur.close()
        conn.close()
        return HTMLResponse("<h1>Пользователь не найден</h1>", status_code=404)

    user = {"id": row[0], "username": row[1], "created_at": row[2]}

    cur.execute("SELECT COUNT(*) FROM transactions WHERE user_id=%s", (user_id,))
    tx_count = cur.fetchone()[0]

    cur.close()
    conn.close()

    return templates.TemplateResponse("admin_user_settings.html", {
        "request": request,
        "token": token,
        "user": user,
        "transactions_count": tx_count,
        "current_page": "admin_users"
    })


@app.get("/admin/user/{user_id}/transactions", response_class=HTMLResponse)
def admin_user_transactions(request: Request, token: str, user_id: int):
    if not admin_required(token):
        return RedirectResponse("/home")

    tx = get_transactions(user_id)

    return templates.TemplateResponse("admin_user_transactions.html", {
        "request": request,
        "token": token,
        "user_id": user_id,
        "transactions": tx,
        "current_page": "admin_users"
    })


@app.get("/admin/user/{user_id}/edit", response_class=HTMLResponse)
def admin_edit_user_page(request: Request, token: str, user_id: int):
    if not admin_required(token):
        return RedirectResponse("/home")

    username = get_username_by_id(user_id)
    return templates.TemplateResponse("admin_edit_user.html", {
        "request": request,
        "token": token,
        "user_id": user_id,
        "username": username,
        "current_page": "admin_users"
    })


@app.post("/admin/user/{user_id}/edit")
def admin_edit_user(request: Request, token: str, user_id: int, new_username: str = Form(...)):
    if not admin_required(token):
        return RedirectResponse("/home")

    ok = update_username(user_id, new_username)
    if not ok:
        return HTMLResponse("<h1>Ошибка: логин уже занят</h1>")

    return RedirectResponse(f"/admin/user/{user_id}?token={token}", status_code=302)


@app.get("/admin/user/{user_id}/reset_password", response_class=HTMLResponse)
def admin_reset_pass(request: Request, token: str, user_id: int):
    if not admin_required(token):
        return RedirectResponse("/home")

    new_password = "123456"

    import bcrypt
    conn = get_conn()
    cur = conn.cursor()

    new_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    cur.execute("UPDATE users SET password_hash=%s WHERE id=%s", (new_hash, user_id))

    conn.commit()
    conn.close()

    username = get_username_by_id(user_id)
    return templates.TemplateResponse("admin_password_reset.html", {
        "request": request,
        "token": token,
        "username": username,
        "new_password": new_password,
        "current_page": "admin_users"
    })


@app.get("/admin/user/{user_id}/delete")
def admin_delete_user(request: Request, token: str, user_id: int):
    if not admin_required(token):
        return RedirectResponse("/home")

    delete_user(user_id)
    return RedirectResponse(f"/admin/users?token={token}", status_code=302)


@app.get("/admin/create_user", response_class=HTMLResponse)
def admin_create_user_page(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    return templates.TemplateResponse("admin_create_user.html", {
        "request": request,
        "token": token,
        "current_page": "admin_users"
    })


@app.post("/admin/create_user")
def admin_create_user(request: Request, token: str,
                      username: str = Form(...), password: str = Form(...)):
    if not admin_required(token):
        return RedirectResponse("/home")

    create_user(username, password)
    return RedirectResponse(f"/admin/users?token={token}", status_code=302)


@app.get("/admin/transactions", response_class=HTMLResponse)
def admin_transactions_page(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    tx = get_all_transactions()
    return templates.TemplateResponse("admin_transactions.html", {
        "request": request,
        "token": token,
        "transactions": tx,
        "current_page": "admin_transactions"
    })


@app.get("/admin/stats", response_class=HTMLResponse)
def admin_stats_page(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    st = get_admin_stats()

    conn = get_conn()
    cur = conn.cursor()

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

    cur.execute("""
        SELECT DATE(created_at),
               SUM(CASE WHEN type='income' THEN amount ELSE 0 END),
               SUM(CASE WHEN type='expense' THEN amount ELSE 0 END)
        FROM transactions
        GROUP BY DATE(created_at)
        ORDER BY DATE(created_at)
    """)
    timeline = cur.fetchall()

    timeline_dates = [str(r[0]) for r in timeline]
    timeline_income = [float(r[1]) for r in timeline]
    timeline_expense = [float(r[2]) for r in timeline]

    conn.close()

    return templates.TemplateResponse("admin_stats.html", {
        "request": request,
        "token": token,
        **st,
        "category_names": category_names,
        "category_values": category_values,
        "timeline_dates": timeline_dates,
        "timeline_income": timeline_income,
        "timeline_expense": timeline_expense,
        "current_page": "admin_stats"
    })



@app.get("/admin/logs", response_class=HTMLResponse)
def admin_logs_page(request: Request, token: str):
    if not admin_required(token):
        return RedirectResponse("/home")

    logs = read_logs()
    return templates.TemplateResponse("admin_logs.html", {
        "request": request,
        "token": token,
        "logs": logs,
        "current_page": "admin_logs"
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
    if not user_id:
        return RedirectResponse("/login")

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
    if not user_id:
        return RedirectResponse("/login")

    delete_goal(id, user_id)
    return RedirectResponse(f"/goals?token={token}", status_code=302)


@app.get("/goal_edit", response_class=HTMLResponse)
def goal_edit_page(request: Request, token: str, id: int):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    goals = get_goals(user_id)
    goal = next((g for g in goals if g["id"] == id), None)
    return templates.TemplateResponse("goal_edit.html", {
        "request": request,
        "token": token,
        "goal": goal
    })


@app.post("/goal_edit", response_class=HTMLResponse)
def goal_edit(request: Request, token: str, id: int,
              name: str = Form(...), target: float = Form(...)):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    update_goal(id, user_id, name, target)
    return RedirectResponse(f"/goals?token={token}", status_code=302)


@app.get("/add_goal_money", response_class=HTMLResponse)
def add_goal_money_page(request: Request, token: str, id: int):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    wallets = get_wallets(user_id)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, saved, target FROM goals WHERE id=%s AND user_id=%s",
        (id, user_id)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return RedirectResponse(f"/goals?token={token}", status_code=302)

    goal = {
        "id": row[0],
        "name": row[1],
        "saved": row[2],
        "target": row[3],
        "percent": round(row[2] / row[3] * 100, 1) if row[3] else 0
    }

    return templates.TemplateResponse(
        "goal_add_money.html",
        {
            "request": request,
            "token": token,
            "goal": goal,
            "wallets": wallets
        }
    )


# Открыть страницу
@app.get("/goal_withdraw", response_class=HTMLResponse)
def goal_withdraw_page(request: Request, token: str, id: int):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT id, name, saved, target FROM goals WHERE id=%s AND user_id=%s",
        (id, user_id)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return RedirectResponse(f"/goals?token={token}")

    goal = {
        "id": row[0],
        "name": row[1],
        "saved": row[2],
        "target": row[3],
    }

    wallets = get_wallets(user_id)

    return templates.TemplateResponse(
        "goal_withdraw.html",
        {
            "request": request,
            "token": token,
            "goal": goal,
            "wallets": wallets
        }
    )

@app.post("/goal_withdraw")
def goal_withdraw_post(
    token: str = Form(...),
    id: int = Form(...),
    wallet_id: int = Form(...),
    amount: float = Form(...)
):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT saved FROM goals WHERE id=%s AND user_id=%s",
        (id, user_id)
    )
    saved = cur.fetchone()[0]

    if amount > saved:
        cur.close()
        conn.close()
        return RedirectResponse(f"/goal_withdraw?token={token}&id={id}")

    cur.execute(
        "UPDATE goals SET saved = saved - %s WHERE id=%s AND user_id=%s",
        (amount, id, user_id)
    )

    db.add_income(
        user_id,
        amount,
        1,
        wallet_id,
        f"Вывод из цели #{id}"
    )

    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(f"/goals?token={token}", status_code=303)

@app.post("/add_goal_money/save")
def add_goal_money_save(
    token: str = Form(...),
    id: int = Form(...),
    wallet_id: int = Form(...),
    amount: float = Form(...)
):
    user_id = get_user_id_from_token(token)

    db.add_expense(user_id, amount, 1, wallet_id, f"Пополнение цели #{id}")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "UPDATE goals SET saved = saved + %s WHERE id=%s AND user_id=%s",
        (amount, id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return RedirectResponse(f"/goals?token={token}", status_code=303)


chat_router = APIRouter()


class ChatRequest(BaseModel):
    message: str


@chat_router.post("/api/support_chat")
async def support_chat(data: ChatRequest):
    import openai
    print("OPENAI FILE:", openai.__file__)
    print("OPENAI VERSION:", openai.__version__)

    try:
        client = get_openai_client()

        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": "Ты поддержка FinanceBot."},
                {"role": "user", "content": data.message}
            ]
        )

        return {"reply": response.output_text}

    except Exception as e:
        import traceback
        traceback.print_exc()
        return {"reply": f"AI ERROR: {str(e)}"}



app.include_router(chat_router)
@app.get("/operation/{category_id}")
async def operation_page(category_id: int, token: str, request: Request):
    user_id = get_user_id_from_token(token)
    category = get_category(category_id, user_id)
    wallets = get_wallets(user_id)

    return templates.TemplateResponse("operation.html", {
        "request": request,
        "category": category,
        "wallets": wallets,
        "token": token
    })
@app.post("/add_wallet")
async def add_wallet_post(
    token: str = Form(...),
    name: str = Form(...),
    icon: str = Form(...)
):
    user_id = get_user_id_from_token(token)
    add_wallet(user_id, name, icon)
    return RedirectResponse(f"/home?token={token}", status_code=303)

@app.get("/add_wallet")
def add_wallet_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    return templates.TemplateResponse("add_wallet.html", {
        "request": request,
        "token": token
    })

@app.post("/add_category")
def add_category_post(
    token: str = Form(...),
    name: str = Form(...),
    type: str = Form(...),
    icon: str = Form(...)
):
    user_id = get_user_id_from_token(token)
    add_category(user_id, name, type, icon)
    return RedirectResponse(f"/home?token={token}", status_code=303)

@app.get("/add_category")
def add_category_page(
    token: str,
    type: str,
    request: Request
):
    return templates.TemplateResponse(
        "add_category.html",
        {
            "request": request,
            "token": token,
            "type": type
        }
    )

@app.post("/delete_category/{cat_id}")
async def delete_category(cat_id: int, token: str):
    user_id = get_user_id_from_token(token)

    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM categories WHERE id=%s AND user_id=%s",
        (cat_id, user_id)
    )
    conn.commit()
    cur.close()
    conn.close()

    return {"ok": True}


from fastapi.responses import JSONResponse

@app.post("/add_operation")
async def add_operation(
    token: str = Form(...),
    category_id: int = Form(...),
    wallet_id: int = Form(...),
    amount: float = Form(...),
    type: str = Form(...),
    description: str = Form("")
):
    user_id = get_user_id_from_token(token)

    try:
        if type == "income":
            db.add_income(user_id, amount, category_id, wallet_id, description)
        else:
            db.add_expense(user_id, amount, category_id, wallet_id, description)

        return JSONResponse({"success": True})

    except Exception as e:
        return JSONResponse(
            {"success": False, "error": str(e)},
            status_code=400
        )
@app.post("/delete_category")
def delete_category(
    token: str = Form(...),
    category_id: int = Form(...)
):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return {"success": False}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM categories WHERE id=%s AND user_id=%s",
        (category_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"success": True}
@app.post("/delete_wallet")
def delete_wallet(
    token: str = Form(...),
    wallet_id: int = Form(...)
):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return {"success": False}

    conn = get_conn()
    cur = conn.cursor()

    cur.execute(
        "DELETE FROM wallets WHERE id=%s AND user_id=%s",
        (wallet_id, user_id)
    )

    conn.commit()
    cur.close()
    conn.close()

    return {"success": True}
