# schemas.py
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# --- Jugadores ---
class JugadorBase(BaseModel):
    nombre: str

class JugadorCreate(JugadorBase):
    pass

class JugadorOut(JugadorBase):
    id: int
    ganadas: int
    perdidas: int
    puntaje: int
    class Config:
        orm_mode = True


# --- Movimientos ---
class MovimientoBase(BaseModel):
    posicion: int
    turno: int

class MovimientoOut(MovimientoBase):
    id: int
    jugador_id: int
    timestamp: datetime
    class Config:
        orm_mode = True


# --- Partidas ---
class PartidaBase(BaseModel):
    jugador1_id: int
    jugador2_id: int

class PartidaCreate(PartidaBase):
    pass

class PartidaOut(PartidaBase):
    id: int
    fecha: datetime
    ganador_id: Optional[int]
    duracion_seg: Optional[int]
    movimientos: List[MovimientoOut] = []
    class Config:
        orm_mode = True