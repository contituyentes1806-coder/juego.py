from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import jwt
import datetime
from typing import Optional, Dict

app = FastAPI(title="Game Backend API", version="1.0.0")

# Permitir CORS para desarrollo local e integración con el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "super_secret_jwt_key_change_in_production"
ALGORITHM = "HS256"

# Base de datos simulada en memoria
db_users: Dict[str, dict] = {}
db_daily_attempts: Dict[str, dict] = {}  # {user_id: {date_str: attempt_count}}

class ScoreSubmit(BaseModel):
    user_id: str
    score: int
    validation_hash: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

def verify_jwt_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Header de autorización inválido o faltante")
    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="El token ha expirado")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Token inválido")

@app.get("/")
def read_root():
    return {"message": "Game Backend API funcionando correctamente"}

@app.post("/generate-access-token", response_model=TokenResponse)
def generate_access_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=2),
        "iat": datetime.datetime.utcnow()
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return {"access_token": token, "token_type": "bearer"}

@app.post("/submit-score")
def submit_score(data: ScoreSubmit, token_payload: dict = Depends(verify_jwt_token)):
    if token_payload.get("sub") != data.user_id:
        raise HTTPException(status_code=403, detail="El ID de usuario no coincide con el token")
    
    today_str = datetime.date.today().isoformat()
    user_attempts = db_daily_attempts.setdefault(data.user_id, {})
    current_attempts = user_attempts.get(today_str, 0)
    
    if current_attempts >= 3:
        raise HTTPException(status_code=429, detail="Límite de intentos diarios alcanzado (Máx 3)")
    
    # Simulación de validación anti-trampas
    expected_hash_pattern = f"{data.user_id}_{data.score}"
    if not data.validation_hash or len(data.validation_hash) < 8:
        raise HTTPException(status_code=400, detail="Hash de validación anti-trampas inválido")
    
    user_attempts[today_str] = current_attempts + 1
    
    return {
        "status": "success",
        "message": "Puntuación registrada con éxito",
        "user_id": data.user_id,
        "score": data.score,
        "attempts_today": user_attempts[today_str]
    }