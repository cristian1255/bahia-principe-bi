"""
backend/auth.py
================
Módulo de Autenticación y Autorización para la API REST del Backend Bahía Príncipe.
Implementa autenticación mediante PIN + JWT con soporte de roles:
  - ADMIN:   Acceso total al sistema, configuración y auditoría.
  - DIRECTOR: KPIs globales del complejo, reportes PDF y chat IA.
  - GERENTE:  KPIs del hotel asignado y gestión de reservas.

Seguridad implementada:
  - PINs almacenados como hash bcrypt (nunca en texto plano).
  - Tokens JWT con expiración configurable (default: 8 horas).
  - Middleware FastAPI para protección de rutas.
  - Ningún endpoint expone datos PII de huéspedes.
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# =====================================================================
# CONFIGURACIÓN JWT
# =====================================================================

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "bahia-principe-bi-secret-key-cambiar-en-produccion")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "8"))

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer(auto_error=False)


# =====================================================================
# USUARIOS PRE-CONFIGURADOS (en producción usar base de datos)
# =====================================================================

# PINs hasheados con bcrypt. Para regenerar: pwd_context.hash("123456")
USERS_DB: Dict[str, Dict[str, Any]] = {
    "director.general": {
        "username": "director.general",
        "pin_hash": pwd_context.hash("123456"),  # PIN de demo
        "nombre_completo": "Director General A&B",
        "rol": "ADMIN",
        "hotel_asignado": "ALL",
        "activo": True,
    },
    "gol.tulum": {
        "username": "gol.tulum",
        "pin_hash": pwd_context.hash("111111"),
        "nombre_completo": "Gerente Operaciones Grand Tulum",
        "rol": "GERENTE",
        "hotel_asignado": "BPG",
        "activo": True,
    },
    "gol.akumal": {
        "username": "gol.akumal",
        "pin_hash": pwd_context.hash("222222"),
        "nombre_completo": "Gerente Operaciones Luxury Akumal",
        "rol": "GERENTE",
        "hotel_asignado": "AP3",
        "activo": True,
    },
    "gol.coba": {
        "username": "gol.coba",
        "pin_hash": pwd_context.hash("333333"),
        "nombre_completo": "Gerente Operaciones Grand Coba",
        "rol": "GERENTE",
        "hotel_asignado": "TOI",
        "activo": True,
    },
    "gol.siankan": {
        "username": "gol.siankan",
        "pin_hash": pwd_context.hash("444444"),
        "nombre_completo": "Gerente Operaciones Luxury Sian Ka'an",
        "rol": "GERENTE",
        "hotel_asignado": "BPS",
        "activo": True,
    },
    "gol.bouganville": {
        "username": "gol.bouganville",
        "pin_hash": pwd_context.hash("555555"),
        "nombre_completo": "Gerente Operaciones Grand Bouganville",
        "rol": "GERENTE",
        "hotel_asignado": "BPB",
        "activo": True,
    },
    "admin": {
        "username": "admin",
        "pin_hash": pwd_context.hash("000000"),
        "nombre_completo": "Administrador del Sistema",
        "rol": "ADMIN",
        "hotel_asignado": "ALL",
        "activo": True,
    },
}


# =====================================================================
# MODELOS PYDANTIC
# =====================================================================

class LoginRequest(BaseModel):
    username: str
    pin: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    usuario: Dict[str, Any]


class UserInfo(BaseModel):
    username: str
    nombre_completo: str
    rol: str
    hotel_asignado: str


# =====================================================================
# FUNCIONES DE AUTENTICACIÓN
# =====================================================================

def verify_pin(pin_plano: str, pin_hash: str) -> bool:
    """Verifica un PIN en texto plano contra su hash bcrypt."""
    return pwd_context.verify(pin_plano, pin_hash)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Genera un JWT firmado con el payload del usuario."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    )
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


def autenticar_usuario(username: str, pin: str) -> Optional[Dict[str, Any]]:
    """Autentica un usuario por username + PIN y retorna su perfil si es válido."""
    user = USERS_DB.get(username.lower())
    if not user or not user.get("activo"):
        return None
    if not verify_pin(pin, user["pin_hash"]):
        return None
    return user


def login_handler(request: LoginRequest) -> TokenResponse:
    """Procesa el login y genera el JWT si las credenciales son correctas."""
    user = autenticar_usuario(request.username, request.pin)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o PIN incorrectos. Verifica tus credenciales.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = {
        "sub": user["username"],
        "rol": user["rol"],
        "hotel_asignado": user["hotel_asignado"],
        "nombre": user["nombre_completo"],
    }

    token = create_access_token(data=payload)
    expire_seconds = ACCESS_TOKEN_EXPIRE_HOURS * 3600

    return TokenResponse(
        access_token=token,
        expires_in=expire_seconds,
        usuario={
            "username": user["username"],
            "nombre_completo": user["nombre_completo"],
            "rol": user["rol"],
            "hotel_asignado": user["hotel_asignado"],
        },
    )


# =====================================================================
# DEPENDENCIAS DE FASTAPI (AUTORIZACIÓN)
# =====================================================================

async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Dict[str, Any]:
    """
    Dependencia FastAPI que valida el JWT y retorna el perfil del usuario.
    Inyectar con: user = Depends(get_current_user)
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Se requiere autenticación. Por favor inicia sesión desde la app.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if not username:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token inválido.")
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado o inválido. Por favor inicia sesión nuevamente.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "username": username,
        "rol": payload.get("rol", "GERENTE"),
        "hotel_asignado": payload.get("hotel_asignado", "ALL"),
        "nombre": payload.get("nombre", "Usuario"),
    }


def requiere_rol(*roles_permitidos: str):
    """
    Decorador de autorización por rol. Uso:
        user = Depends(requiere_rol("ADMIN", "DIRECTOR"))
    """
    async def verificar_rol(
        current_user: Dict[str, Any] = Depends(get_current_user),
    ) -> Dict[str, Any]:
        if current_user["rol"] not in roles_permitidos:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acceso denegado. Se requiere uno de los roles: {', '.join(roles_permitidos)}.",
            )
        return current_user

    return verificar_rol


def hotel_permitido(user: Dict[str, Any], hotel_codigo: Optional[str]) -> str:
    """
    Retorna el hotel correcto según el rol del usuario.
    Un GERENTE solo puede ver los datos de su hotel asignado.
    Un ADMIN/DIRECTOR puede ver cualquier hotel o el consolidado.
    """
    if user["rol"] == "GERENTE":
        return user["hotel_asignado"]
    return hotel_codigo or "ALL"
