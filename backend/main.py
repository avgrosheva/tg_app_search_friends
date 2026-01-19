from typing import Optional, List
 
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
 
from .db import init_db, get_connection
 
app = FastAPI()
templates = Jinja2Templates(directory="backend/templates")
 
 
@app.on_event("startup")
def on_startup():
    init_db()
 
 
class ProfileIn(BaseModel):
    tg_id: int
    first_name: str
    last_name: Optional[str] = None
    middle_name: Optional[str] = None
    age: Optional[int] = None
    about: Optional[str] = None
    drinks: Optional[str] = None
    topics: Optional[str] = None
    location: Optional[str] = None
 
 
class ProfileOut(ProfileIn):
    id: int
    balance: float = 0
    is_subscribed: bool = False
 
 
class InviteIn(BaseModel):
    from_tg_id: int
    to_tg_id: int
 
 
class InviteOut(BaseModel):
    id: int
    from_tg_id: int
    to_tg_id: int
    status: str
    created_at: str
 
 
class MessageIn(BaseModel):
    from_tg_id: int
    to_tg_id: int
    text: str
 
 
class MessageOut(BaseModel):
    id: int
    from_tg_id: int
    to_tg_id: int
    text: str
    created_at: str
 
 
class BalanceChange(BaseModel):
    tg_id: int
    amount: float
 
 
class BalanceResponse(BaseModel):
    tg_id: int
    balance: float
    is_subscribed: bool
 
 
class SubscriptionChange(BaseModel):
    tg_id: int
    active: bool = True
 
 
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})
 
 
@app.get("/health")
async def health():
    return {"status": "ok"}
 
 
@app.post("/api/profile", response_model=ProfileOut)
def create_or_update_profile(profile: ProfileIn):
    conn = get_connection()
    cur = conn.cursor()
 
    cur.execute("SELECT id FROM users WHERE tg_id = ?", (profile.tg_id,))
    row = cur.fetchone()
 
    if row:
        cur.execute(
            """
            UPDATE users
            SET first_name = ?, last_name = ?, middle_name = ?, age = ?,
                about = ?, drinks = ?, topics = ?, location = ?
            WHERE tg_id = ?
            """,
            (
                profile.first_name,
                profile.last_name,
                profile.middle_name,
                profile.age,
                profile.about,
                profile.drinks,
                profile.topics,
                profile.location,
                profile.tg_id,
            ),
        )
        user_id = row["id"]
    else:
        cur.execute(
            """
            INSERT INTO users (
                tg_id, first_name, last_name, middle_name, age,
                about, drinks, topics, location
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                profile.tg_id,
                profile.first_name,
                profile.last_name,
                profile.middle_name,
                profile.age,
                profile.about,
                profile.drinks,
                profile.topics,
                profile.location,
            ),
        )
        user_id = cur.lastrowid
 
    conn.commit()
 
    cur.execute("SELECT * FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    conn.close()
 
    return ProfileOut(**row)
 
 
@app.get("/api/users", response_model=List[ProfileOut])
def list_users():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM users ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return [ProfileOut(**row) for row in rows]
 
 
@app.post("/api/invite", response_model=InviteOut)
def create_invite(invite: InviteIn):
    conn = get_connection()
    cur = conn.cursor()
 
    if invite.from_tg_id == invite.to_tg_id:
        conn.close()
        raise HTTPException(status_code=400, detail="Нельзя отправить приглашение самому себе")
 
    cur.execute(
        """
        SELECT * FROM invites
        WHERE from_tg_id = ? AND to_tg_id = ? AND status = 'pending'
        """,
        (invite.from_tg_id, invite.to_tg_id),
    )
    row = cur.fetchone()
    if row:
        conn.close()
        return InviteOut(**row)
 
    cur.execute(
        """
        INSERT INTO invites (from_tg_id, to_tg_id, status)
        VALUES (?, ?, 'pending')
        """,
        (invite.from_tg_id, invite.to_tg_id),
    )
    conn.commit()
 
    invite_id = cur.lastrowid
    cur.execute("SELECT * FROM invites WHERE id = ?", (invite_id,))
    row = cur.fetchone()
    conn.close()
 
    return InviteOut(**row)
 
 
@app.get("/api/invites", response_model=List[InviteOut])
def list_invites(tg_id: int):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT * FROM invites
        WHERE from_tg_id = ? OR to_tg_id = ?
        ORDER BY created_at DESC
        """,
        (tg_id, tg_id),
    )
    rows = cur.fetchall()
    conn.close()
    return [InviteOut(**row) for row in rows]
 
 
@app.post("/api/messages", response_model=MessageOut)
def send_message(msg: MessageIn):
    conn = get_connection()
    cur = conn.cursor()
 
    # проверяем отправителя
    cur.execute("SELECT is_subscribed FROM users WHERE tg_id = ?", (msg.from_tg_id,))
    sender = cur.fetchone()
    if not sender:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
 
    is_sub = bool(sender["is_subscribed"])
 
    is_sub = bool(sender["is_subscribed"])

    if not is_sub:
        cur.execute(
            """
            SELECT 1 FROM invites
            WHERE from_tg_id = ? AND to_tg_id = ? AND status = 'pending'
            """,
            (msg.from_tg_id, msg.to_tg_id),
        )
        sent = cur.fetchone()

        cur.execute(
            """
            SELECT 1 FROM invites
            WHERE from_tg_id = ? AND to_tg_id = ? AND status = 'pending'
            """,
            (msg.to_tg_id, msg.from_tg_id),
        )
        received = cur.fetchone()

        # если нет ОБОИХ инвайтов — чата нет
        if not (sent and received):
            conn.close()
            raise HTTPException(
                status_code=403,
                detail="Чат доступен после взаимного инвайта или с активной подпиской."
            )
 
    cur.execute(
        """
        INSERT INTO messages (from_tg_id, to_tg_id, text)
        VALUES (?, ?, ?)
        """,
        (msg.from_tg_id, msg.to_tg_id, msg.text),
    )
    conn.commit()
    msg_id = cur.lastrowid
 
    cur.execute("SELECT * FROM messages WHERE id = ?", (msg_id,))
    row = cur.fetchone()
    conn.close()
 
    return MessageOut(**row)
 
 
@app.get("/api/chat", response_model=List[MessageOut])
def get_chat(user1: int, user2: int):
    conn = get_connection()
    cur = conn.cursor()
 
    cur.execute(
        """
        SELECT * FROM messages
        WHERE (from_tg_id = ? AND to_tg_id = ?)
           OR (from_tg_id = ? AND to_tg_id = ?)
        ORDER BY created_at ASC
        """,
        (user1, user2, user2, user1),
    )
 
    rows = cur.fetchall()
    conn.close()
 
    return [MessageOut(**row) for row in rows]
 
 
@app.post("/api/balance/add", response_model=BalanceResponse)
def add_balance(change: BalanceChange):
    conn = get_connection()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (change.tg_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
 
    cur.execute(
        """
        UPDATE users
        SET balance = COALESCE(balance, 0) + ?
        WHERE tg_id = ?
        """,
        (change.amount, change.tg_id),
    )
    conn.commit()
 
    cur.execute(
        "SELECT tg_id, balance, is_subscribed FROM users WHERE tg_id = ?",
        (change.tg_id,),
    )
    row = cur.fetchone()
    conn.close()
 
    return BalanceResponse(
        tg_id=row["tg_id"],
        balance=row["balance"],
        is_subscribed=bool(row["is_subscribed"]),
    )
 
 
@app.post("/api/subscribe", response_model=BalanceResponse)
def set_subscription(sub: SubscriptionChange):
    conn = get_connection()
    cur = conn.cursor()
 
    cur.execute("SELECT * FROM users WHERE tg_id = ?", (sub.tg_id,))
    row = cur.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Пользователь не найден")
 
    cur.execute(
        "UPDATE users SET is_subscribed = ? WHERE tg_id = ?",
        (1 if sub.active else 0, sub.tg_id),
    )
    conn.commit()
 
    cur.execute(
        "SELECT tg_id, balance, is_subscribed FROM users WHERE tg_id = ?",
        (sub.tg_id,),
    )
    row = cur.fetchone()
    conn.close()
 
    return BalanceResponse(
        tg_id=row["tg_id"],
        balance=row["balance"],
        is_subscribed=bool(row["is_subscribed"]),
    )