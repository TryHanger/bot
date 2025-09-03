import sqlite3
from datetime import datetime, timedelta
from config import DB_PATH

def connect():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = connect()
    cursor = conn.cursor()
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY,
        stars FLOAT DEFAULT 0,
        refs INTEGER DEFAULT 0,
        inviter_id INTEGER,
        ref_counted INTEGER DEFAULT 0,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        earned FLOAT DEFAULT 0,
        withdrawn FLOAT DEFAULT 0,
        last_daily_bonus DATE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS subscriptions (
        user_id INTEGER PRIMARY KEY,       -- ID пользователя
        plan TEXT NOT NULL,                -- lite / pro / ultra
        start_date TIMESTAMP NOT NULL,     -- дата старта
        end_date TIMESTAMP NOT NULL,       -- дата окончания
        last_autoclicker_claim DATE
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clicks (
        user_id INTEGER,
        date DATE,
        clicks INTEGER DEFAULT 0,
        PRIMARY KEY (user_id, date)
    )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            reward REAL NOT NULL,
            status TEXT DEFAULT 'active'
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS task_submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id INTEGER,
            user_id INTEGER,
            status TEXT DEFAULT 'pending', -- pending, approved, rejected
            UNIQUE(task_id, user_id)
        )
    """)

    conn.commit()
    return conn, cursor

def add_user(user_id: int, username: str = None, inviter_id: int = None):
    conn = connect()
    cursor = conn.cursor()
    
    # Проверяем, есть ли уже пользователь
    cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
    if cursor.fetchone() is None:
        # Добавляем нового пользователя с текущим временем
        cursor.execute(
            "INSERT INTO users (user_id, username, inviter_id, created_at) VALUES (?, ?, ?, ?)",
            (user_id, username, inviter_id, datetime.now().replace(microsecond=0))
        )
        cursor.execute("""
            INSERT OR IGNORE INTO subscriptions (user_id, plan, start_date, end_date)
            VALUES (?, 'basic', datetime('now'), NULL)
        """, (user_id,))
    else:
        # Если пользователь есть — обновляем username (на случай, если он поменялся)
        cursor.execute(
            "UPDATE users SET username = ? WHERE user_id = ?",
            (username, user_id)
        )

    conn.commit()
    conn.close()

def add_star_referral(user_id, reward):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET stars = stars + ?, refs = refs + 1, earned = earned + ? WHERE user_id = ?", (reward, reward, user_id,))
    conn.commit()
    conn.close()

def get_user(user_id):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user

def is_referral_counted(user_id: int) -> bool:
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('SELECT ref_counted FROM users WHERE user_id = ?', (user_id,))
    row = cursor.fetchone()
    conn.close()
    return row is not None and row[0] == 1

def mark_referral_counted(user_id: int):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET ref_counted = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def get_referrals(user_id: int):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, username, created_at FROM users WHERE inviter_id = ?",
        (user_id,)
    )
    referrals = cursor.fetchall()
    conn.close()
    return referrals  # список кортежей: [(user_id, username, created_at), ...]

def get_referrals_paginated(user_id: int, offset: int = 0, limit: int = 10):
    conn = connect()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT user_id, username, created_at FROM users WHERE inviter_id = ? ORDER BY created_at LIMIT ? OFFSET ?",
        (user_id, limit, offset)
    )
    referrals = cursor.fetchall()

    cursor.execute(
        "SELECT COUNT(*) FROM users WHERE inviter_id = ?",
        (user_id,)
    )
    total = cursor.fetchone()[0]

    conn.close()
    return referrals, total

def earned_update(user_id: int, star):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET earned = earned + ? WHERE user_id = ?", (star, user_id,))
    conn.commit()
    conn.close()
    
def update_user_balance(user_id: int, amount):
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET withdrawn = withdrawn + ?, stars = stars - ? WHERE user_id = ?", (amount, amount, user_id,))
    conn.commit()
    conn.close()
    
    
def add_subscription(user_id: int, plan: str):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    start = datetime.now()
    if plan == "lite":
        end = start + timedelta(days=7)
    elif plan == "pro":
        end = start + timedelta(days=14)
    elif plan == "ultra":
        end = start + timedelta(days=30)
    else:
        raise ValueError("Неизвестный план!")

    cursor.execute("""
        INSERT OR REPLACE INTO subscriptions (user_id, plan, start_date, end_date)
        VALUES (?, ?, ?, ?)
    """, (user_id, plan, start, end))

    conn.commit()
    conn.close()
    
    
    
def activate_vip(user_id: int, days: int, pack: str):
    from datetime import datetime, timedelta
    vip_end_date = datetime.now() + timedelta(days=days)

    # Пример обновления данных пользователя
    conn = sqlite3.connect("users.db")
    cur = conn.cursor()
    # cur.execute(
    #     "UPDATE users SET vip_pack=?, vip_until=? WHERE user_id=?",
    #     (pack, vip_end_date.strftime("%Y-%m-%d %H:%M:%S"), user_id)
    # )
    # conn.commit()
    conn.close()
    
    
def is_subscription_active(user_id: int) -> bool:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT end_date FROM subscriptions WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()

    conn.close()

    if row:
        end_date = datetime.fromisoformat(row[0])
        return datetime.now() < end_date
    return False

def get_user_multiplier(user_id: int) -> float:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        SELECT plan, end_date FROM subscriptions WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return 1.0  # по умолчанию базовый множитель

    plan, end_date = row
    now = datetime.now()

    # Если подписка истекла → вернуть basic
    if end_date and now > datetime.fromisoformat(end_date):
        update_to_basic(user_id)
        return 1.0

    multipliers = {
        "basic": 1.0,
        "lite": 2.5,
        "pro": 3.0,
        "ultra": 4.0
    }
    return multipliers.get(plan, 1.0)

def update_to_basic(user_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE subscriptions
        SET plan = 'basic', start_date = datetime('now'), end_date = NULL
        WHERE user_id = ?
    """, (user_id,))
    conn.commit()
    conn.close()
    



PLAN_CONFIG_DAILY_BONUS = {
    "basic": {"amount": 0.5},
    "lite": {"amount": 1},
    "pro": {"amount": 2},
    "ultra": {"amount": 3}
}

def get_daily_bonus(user_id: int) -> tuple[bool, float]:
    """
    Возвращает (успех, сумма бонуса)
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    today = datetime.now().date().isoformat()

    # Проверяем, получал ли пользователь бонус сегодня
    cursor.execute("SELECT last_daily_bonus FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    last_bonus_date = row[0] if row else None

    if last_bonus_date == today:
        conn.close()
        return False, 0

    # Получаем текущий план пользователя
    cursor.execute("SELECT plan, end_date FROM subscriptions WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()

    if row:
        plan, end_date = row
        if end_date and datetime.now() > datetime.fromisoformat(end_date):
            plan = "basic"  # если подписка истекла
            cursor.execute(
                "UPDATE subscriptions SET plan = ?, end_date = NULL WHERE user_id = ?",
                ("basic", user_id)
            )
    else:
        plan = "basic"

    # Определяем сумму бонуса по плану
    amount = PLAN_CONFIG_DAILY_BONUS.get(plan, PLAN_CONFIG_DAILY_BONUS["basic"])["amount"]

    # Начисляем бонус
    cursor.execute("""
        UPDATE users
        SET stars = stars + ?, earned = earned + ?, last_daily_bonus = ?
        WHERE user_id = ?
    """, (amount, amount, today, user_id))

    conn.commit()
    conn.close()
    return True, amount

def game_dice(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if amount < 0:
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id,))
    else:
        cursor.execute("UPDATE users SET stars = stars + ?, earned = earned + ? WHERE user_id = ?", (amount, amount, user_id,))
    conn.commit()
    conn.close()

def game_coin(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if amount < 0:
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id,))
    else:
        cursor.execute("UPDATE users SET stars = stars + ?, earned = earned + ? WHERE user_id = ?", (amount, amount, user_id,))
    conn.commit()
    conn.close()

def game_rps(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if amount < 0:
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id,))
    else:
        cursor.execute("UPDATE users SET stars = stars + ?, earned = earned + ? WHERE user_id = ?", (amount, amount, user_id,))
    conn.commit()
    conn.close()

def game_21(user_id, amount):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    if amount < 0:
        cursor.execute("UPDATE users SET stars = stars + ? WHERE user_id = ?", (amount, user_id,))
    else:
        cursor.execute("UPDATE users SET stars = stars + ?, earned = earned + ? WHERE user_id = ?", (amount, amount, user_id,))
    conn.commit()
    conn.close()
    
AUTOCLICKER_REWARD_PER_HOUR = 1

def get_autoclicker_reward(user_id):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Проверяем подписку
    cursor.execute("""
        SELECT plan, last_autoclicker_claim 
        FROM subscriptions 
        WHERE user_id = ?
    """, (user_id,))
    row = cursor.fetchone()

    if not row:
        conn.close()
        # Нет подписки — отправляем уведомление
        return False, "У вас нет активной подписки. Перейдите в раздел подписок, чтобы подключить автокликер."

    plan, last_claim = row
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # Если подписка есть, но план = basic, автокликер недоступен
    if plan == "basic":
        conn.close()
        return False, "Автокликер доступен только для подписчиков с донатом. Оформите подписку."

    # Если забирает впервые
    if not last_claim:
        last_claim_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    else:
        last_claim_dt = datetime.strptime(last_claim, "%Y-%m-%d %H:%M:%S")
        # Если последний сбор был вчера — сбрасываем на начало нового дня
        if last_claim_dt.date() < now.date():
            last_claim_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # Считаем часы с момента последнего сбора
    delta_hours = int((now - last_claim_dt).total_seconds() // 3600)

    if delta_hours <= 0:
        conn.close()
        return False, "Награды пока нет. Подождите хотя бы час."

    reward = delta_hours * AUTOCLICKER_REWARD_PER_HOUR

    # Обновляем звезды в таблице users
    cursor.execute("""
        UPDATE users
        SET stars = stars + ?
        WHERE user_id = ?
    """, (reward, user_id))

    # Обновляем время последнего забора в subscriptions
    cursor.execute("""
        UPDATE subscriptions
        SET last_autoclicker_claim = ?
        WHERE user_id = ?
    """, (now_str, user_id))

    conn.commit()
    conn.close()

    return True, f"Вы забрали автокликер: +{reward}⭐ за {delta_hours} часов."