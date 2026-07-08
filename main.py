from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from typing import Optional
import httpx
import jwt
import time
import uvicorn

app = FastAPI(title="Free Agents API", version="2.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DISCORD_CLIENT_ID = "1524526940155941076"
DISCORD_CLIENT_SECRET = "zGLLZ1xBWZtZvCAPycGXAkz1HgLawPGc"
DISCORD_REDIRECT_URI = "http://194.62.248.55:30047/auth/discord/callback"
DISCORD_API_URL = "https://discord.com/api/v10"
JWT_SECRET = "free-agents-secret-key-2026"

players_db = [
    {"id": 1, "name": "Lucas Martins", "position": "Atacante", "age": 23, "overall": 88, "nationality": "Brasil", "height": "1.80m", "foot": "Direito", "last_club": "Flamengo", "initials": "LM", "pos": "ST", "available": True},
    {"id": 2, "name": "Rafael Souza", "position": "Meio-campo", "age": 21, "overall": 85, "nationality": "Argentina", "height": "1.75m", "foot": "Esquerdo", "last_club": "River Plate", "initials": "RS", "pos": "CM", "available": True},
    {"id": 3, "name": "Gabriel Pires", "position": "Zagueiro", "age": 25, "overall": 86, "nationality": "Portugal", "height": "1.90m", "foot": "Direito", "last_club": "Porto", "initials": "GP", "pos": "CB", "available": True},
    {"id": 4, "name": "David De Gea", "position": "Goleiro", "age": 33, "overall": 87, "nationality": "Espanha", "height": "1.92m", "foot": "Direito", "last_club": "Manchester United", "initials": "DD", "pos": "GK", "available": True},
    {"id": 5, "name": "Sergio Ramos", "position": "Zagueiro", "age": 38, "overall": 85, "nationality": "Espanha", "height": "1.84m", "foot": "Direito", "last_club": "Sevilla", "initials": "SR", "pos": "CB", "available": True},
    {"id": 6, "name": "Mario Balotelli", "position": "Atacante", "age": 34, "overall": 82, "nationality": "Itália", "height": "1.89m", "foot": "Direito", "last_club": "Adana Demirspor", "initials": "MB", "pos": "ST", "available": True},
    {"id": 7, "name": "Adrien Rabiot", "position": "Meio-campo", "age": 29, "overall": 84, "nationality": "França", "height": "1.88m", "foot": "Esquerdo", "last_club": "Juventus", "initials": "AR", "pos": "CM", "available": True},
    {"id": 8, "name": "Carlos Vela", "position": "Atacante", "age": 35, "overall": 81, "nationality": "México", "height": "1.78m", "foot": "Esquerdo", "last_club": "LAFC", "initials": "CV", "pos": "ST", "available": True},
]
users_db = {}
next_id = 9

class PlayerCreate(BaseModel):
    name: str
    position: str
    age: int
    overall: int
    nationality: str
    height: str
    foot: str
    last_club: str
    initials: str
    pos: str

def create_jwt(user_data):
    payload = {**user_data, "exp": int(time.time()) + 86400 * 7}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

def decode_jwt(token):
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.get("/")
def root():
    return {"message": "Free Agents API", "status": "online"}

@app.get("/players")
def get_players(position: Optional[str] = None, nationality: Optional[str] = None):
    result = players_db
    if position:
        result = [p for p in result if p["position"].lower() == position.lower()]
    if nationality:
        result = [p for p in result if p["nationality"].lower() == nationality.lower()]
    return {"total": len(result), "players": result}

@app.get("/players/{player_id}")
def get_player(player_id: int):
    for p in players_db:
        if p["id"] == player_id:
            return p
    raise HTTPException(status_code=404, detail="Jogador não encontrado")

@app.post("/players", status_code=201)
def create_player(data: PlayerCreate):
    global next_id
    new_player = data.model_dump()
    new_player["id"] = next_id
    new_player["available"] = True
    next_id += 1
    players_db.append(new_player)
    return new_player

@app.get("/auth/discord/login")
def discord_login():
    auth_url = (
        f"https://discord.com/api/oauth2/authorize"
        f"?client_id={DISCORD_CLIENT_ID}"
        f"&redirect_uri={DISCORD_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=identify+email+guilds"
    )
    return {"url": auth_url}

@app.get("/auth/discord/callback")
async def discord_callback(code: str = Query(...)):
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://discord.com/api/v10/oauth2/token",
            data={
                "client_id": DISCORD_CLIENT_ID,
                "client_secret": DISCORD_CLIENT_SECRET,
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": DISCORD_REDIRECT_URI,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Erro na autenticação Discord")
    
    token_data = token_response.json()
    access_token = token_data["access_token"]
    
    async with httpx.AsyncClient() as client:
        user_response = await client.get(
            f"{DISCORD_API_URL}/users/@me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    
    if user_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Erro ao buscar dados do usuário")
    
    discord_user = user_response.json()
    
    discord_id = str(discord_user["id"])
    if discord_id not in users_db:
        users_db[discord_id] = {
            "discord_id": discord_id,
            "username": discord_user["username"],
            "discriminator": discord_user.get("discriminator", "0"),
            "avatar": discord_user.get("avatar", ""),
            "email": discord_user.get("email", ""),
            "global_name": discord_user.get("global_name", discord_user["username"]),
            "created_at": int(time.time()),
        }
    
    user_data = users_db[discord_id]
    jwt_token = create_jwt(user_data)
    
    return RedirectResponse(f"http://176.100.37.91:30064/?token={jwt_token}")

@app.get("/auth/user")
def get_user(authorization: str = ""):
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token não fornecido")
    token = authorization.replace("Bearer ", "")
    return decode_jwt(token)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
