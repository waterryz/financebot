from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from webapp.db import (
    init_db,
    create_user,
    check_user,
    get_user_id,
    generate_token,
    get_user_id_from_token,
    get_username_by_id,
    update_username,
    update_password,
    delete_user
)

app = FastAPI()

# Статика и шаблоны
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

templates = Jinja2Templates(directory="webapp/templates")

@app.get("/", response_class=RedirectResponse)
def root():
    return RedirectResponse("/login")

@app.on_event("startup")
def startup():
    init_db()


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


# ================
#     Л О Г И Н
# ================
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


# =========================
#     Г Л А В Н А Я
# =========================
@app.get("/home", response_class=HTMLResponse)
def home(request: Request, token: str):
    from webapp.db import get_balance
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    username = get_username_by_id(user_id)
    balance = get_balance(user_id)

    return templates.TemplateResponse("home.html", {
        "request": request,
        "username": username,
        "balance": balance,
        "token": token
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
#   СМЕНА ЛОГИНА
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
#   СМЕНА ПАРОЛЯ
# ========================
@app.get("/change_password", response_class=HTMLResponse)
def change_password_page(request: Request, token: str):
    return templates.TemplateResponse("change_password.html", {
        "request": request,
        "token": token
    })


@app.post("/change_password", response_class=HTMLResponse)
def change_password(request: Request, token: str,
                    old_password: str = Form(...),
                    new_password: str = Form(...)):

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
#  УДАЛЕНИЕ АККАУНТА
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
from webapp.db import add_category, get_categories, add_transaction

# Добавить расход
@app.get("/add_expense", response_class=HTMLResponse)
def add_expense_page(request: Request, token: str):
    cats = get_categories("expense")


    return templates.TemplateResponse("add_expense.html", {
        "request": request,
        "token": token,
        "categories": cats
    })


@app.post("/add_expense", response_class=HTMLResponse)
def add_expense(request: Request, token: str,
                amount: float = Form(...),
                category_id: int = Form(...),
                description: str = Form("")):

    user_id = get_user_id_from_token(token)
    add_transaction(user_id, amount, "expense", category_id, description)

    return RedirectResponse(f"/home?token={token}", status_code=302)


# Добавить доход
@app.get("/add_income", response_class=HTMLResponse)
def add_income_page(request: Request, token: str):
    cats = get_categories("income")

    return templates.TemplateResponse("add_income.html", {
        "request": request,
        "token": token,
        "categories": cats
    })


@app.post("/add_income", response_class=HTMLResponse)
def add_income(request: Request, token: str,
                amount: float = Form(...),
                category_id: int = Form(...),
                description: str = Form("")):

    user_id = get_user_id_from_token(token)
    add_transaction(user_id, amount, "income", category_id, description)

    return RedirectResponse(f"/home?token={token}", status_code=302)

from webapp.db import get_transactions

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

from webapp.db import get_stats

@app.get("/stats", response_class=HTMLResponse)
def stats_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    income, expense, cat_stats = get_stats(user_id)

    labels = [row[0] for row in cat_stats]
    values = [float(row[1]) for row in cat_stats]  # <--- ВАЖНО

    return templates.TemplateResponse("stats.html", {
        "request": request,
        "token": token,
        "income": float(income),
        "expense": float(expense),
        "labels": labels,
        "values": values
    })

from webapp.db import get_wishes, add_wish, cancel_wish, postpone_wish

@app.get("/wishlist", response_class=HTMLResponse)
def wishlist_page(request: Request, token: str):
    user_id = get_user_id_from_token(token)
    if not user_id:
        return RedirectResponse("/login")

    wishes = get_wishes(user_id)

    return templates.TemplateResponse("wishlist.html", {
        "request": request,
        "token": token,
        "items": wishes   # <---- ВОТ ЭТО ДОЛЖНО БЫТЬ
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

from webapp.db import save_telegram_id, get_user_id


