# models.py
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base

class Jugador(Base):
    __tablename__ = "jugadores"
    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String, unique=True, index=True)
    ganadas = Column(Integer, default=0)
    perdidas = Column(Integer, default=0)
    puntaje = Column(Integer, default=0)

    partidas = relationship("Partida", back_populates="jugador1", foreign_keys="Partida.jugador1_id")
    partidas2 = relationship("Partida", back_populates="jugador2", foreign_keys="Partida.jugador2_id")


class Partida(Base):
    __tablename__ = "partidas"
    id = Column(Integer, primary_key=True, index=True)
    jugador1_id = Column(Integer, ForeignKey("jugadores.id"))
    jugador2_id = Column(Integer, ForeignKey("jugadores.id"))
    ganador_id = Column(Integer, ForeignKey("jugadores.id"), nullable=True)
    fecha = Column(DateTime, default=datetime.utcnow)
    duracion_seg = Column(Integer, nullable=True)

    jugador1 = relationship("Jugador", foreign_keys=[jugador1_id], back_populates="partidas")
    jugador2 = relationship("Jugador", foreign_keys=[jugador2_id], back_populates="partidas2")
    ganador = relationship("Jugador", foreign_keys=[ganador_id])
    movimientos = relationship("Movimiento", back_populates="partida")


class Movimiento(Base):
    __tablename__ = "movimientos"
    id = Column(Integer, primary_key=True, index=True)
    partida_id = Column(Integer, ForeignKey("partidas.id"))
    jugador_id = Column(Integer, ForeignKey("jugadores.id"))
    posicion = Column(Integer)  # 0–8 (celda del tablero)
    turno = Column(Integer)
    timestamp = Column(DateTime, default=datetime.utcnow)

    partida = relationship("Partida", back_populates="movimientos")