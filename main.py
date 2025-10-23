# main.py
import json
import uuid
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from database import Base, engine, get_db
from models import Jugador, Partida, Movimiento
from fastapi.responses import RedirectResponse

app = FastAPI(title="Triki Multijugador 🎮")

Base.metadata.create_all(bind=engine)

app.mount("/static", StaticFiles(directory="static"), name="static")

partidas = {}

# ======================
#   FUNCIONES AUXILIARES
# ======================

def check_winner(board):
    combos = [(0,1,2), (3,4,5), (6,7,8),
              (0,3,6), (1,4,7), (2,5,8),
              (0,4,8), (2,4,6)]
    for a,b,c in combos:
        if board[a] and board[a] == board[b] == board[c]:
            return board[a]
    if "" not in board:
        return "Empate"
    return None

def get_or_create_jugador(db: Session, nombre: str):
    jugador = db.query(Jugador).filter_by(nombre=nombre).first()
    if not jugador:
        jugador = Jugador(nombre=nombre)
        db.add(jugador)
        db.commit()
        db.refresh(jugador)
    return jugador

# ======================
#   ENDPOINTS PRINCIPALES
# ======================

@app.get("/", response_class=HTMLResponse)
def index():
    with open("static/index.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

from fastapi import status
from fastapi.responses import JSONResponse

@app.post("/api/create_partida")
def api_create_partida():
    """Crea partida vía API POST (compatibilidad con front)."""
    partida_id = str(uuid.uuid4())[:8]
    partidas[partida_id] = {
        "jugadores": {},
        "board": ["" for _ in range(9)],
        "turn": "X",
        "ganador": None,
        "timestamp": datetime.utcnow()
    }
    return JSONResponse(status_code=status.HTTP_201_CREATED, content={"partida_id": partida_id})


@app.get("/api/estadisticas")
def get_estadisticas(db: Session = Depends(get_db)):
    jugadores = (
        db.query(Jugador)
        .order_by(Jugador.ganadas.desc(), Jugador.puntaje.desc())
        .all()
    )
    return [
        {
            "nombre": j.nombre,
            "ganadas": j.ganadas,
            "perdidas": j.perdidas,
            "puntaje": j.puntaje,
        }
        for j in jugadores
    ]



@app.get("/estadisticas")
def redirect_estadisticas():
    """Redirige al archivo HTML de estadísticas dentro de /static"""
    return RedirectResponse(url="/static/estadisticas.html")


@app.get("/historico", response_class=HTMLResponse)
def ver_historico():
    with open("static/historico.html", "r", encoding="utf-8") as f:
        return HTMLResponse(f.read())

# ======================
#   API JSON
# ======================

@app.get("/api/jugadores")
def api_jugadores(db: Session = Depends(get_db)):
    jugadores = db.query(Jugador).all()
    data = []
    for j in jugadores:
        puntaje = j.ganadas * 3 - j.perdidas
        data.append({
            "nombre": j.nombre,
            "ganadas": j.ganadas,
            "perdidas": j.perdidas,
            "puntaje": puntaje
        })
    return data

@app.get("/api/historico")
def api_historico(db: Session = Depends(get_db)):
    partidas = db.query(Partida).all()
    data = []
    for p in partidas:
        ganador = None
        if p.ganador_id:
            ganador = db.query(Jugador).filter(Jugador.id == p.ganador_id).first().nombre
        j1 = db.query(Jugador).filter(Jugador.id == p.jugador1_id).first().nombre
        j2 = db.query(Jugador).filter(Jugador.id == p.jugador2_id).first().nombre
        data.append({
            "jugador1": j1,
            "jugador2": j2,
            "ganador": ganador or "Empate",
            "fecha": p.fecha.strftime("%Y-%m-%d %H:%M:%S")
        })
    return data

# ======================
#   WEBSOCKET
# ======================

@app.websocket("/ws/{partida_id}")
async def websocket_endpoint(websocket: WebSocket, partida_id: str, db: Session = Depends(get_db)):
    await websocket.accept()

    if partida_id not in partidas:
        partidas[partida_id] = {
            "jugadores": {},
            "board": ["" for _ in range(9)],
            "turn": "X",
            "ganador": None
        }

    partida = partidas[partida_id]
    jugador_nombre = None
    simbolo = None

    try:
        while True:
            msg = await websocket.receive_text()
            data = json.loads(msg)
            action = data.get("action")

            if action == "join":
                jugador_nombre = data.get("name")
                if not jugador_nombre:
                    await websocket.send_json({"type": "error", "message": "Falta nombre."})
                    continue

                if "X" not in [j["symbol"] for j in partida["jugadores"].values()]:
                    simbolo = "X"
                elif "O" not in [j["symbol"] for j in partida["jugadores"].values()]:
                    simbolo = "O"
                else:
                    simbolo = None  # espectador

                partida["jugadores"][jugador_nombre] = {"ws": websocket, "symbol": simbolo}

                await websocket.send_json({
                    "type": "info",
                    "message": f"Conectado como {simbolo or 'Espectador'}",
                    "symbol": simbolo
                })
                for j, info in partida["jugadores"].items():
                    await info["ws"].send_json({
                        "type": "state",
                        "board": partida["board"],
                        "turn": partida["turn"],
                        "winner": partida["ganador"]
                    })

            elif action == "move":
                if not simbolo or simbolo != partida["turn"]:
                    await websocket.send_json({"type": "error", "message": "No es tu turno"})
                    continue

                pos = data.get("position")
                if pos is None or partida["board"][pos] != "" or partida["ganador"]:
                    continue

                partida["board"][pos] = simbolo
                partida["turn"] = "O" if partida["turn"] == "X" else "X"
                ganador = check_winner(partida["board"])
                partida["ganador"] = ganador

                for j, info in partida["jugadores"].items():
                    await info["ws"].send_json({
                        "type": "move_result",
                        "board": partida["board"],
                        "turn": partida["turn"],
                        "winner": ganador
                    })

                j_db = get_or_create_jugador(db, jugador_nombre)
                db.add(Movimiento(
                    partida_id=None,
                    jugador_id=j_db.id,
                    posicion=pos,
                    turno=len([c for c in partida["board"] if c])
                ))
                db.commit()

                if ganador:
                    nombres = list(partida["jugadores"].keys())
                    if len(nombres) == 2:
                        j1 = get_or_create_jugador(db, nombres[0])
                        j2 = get_or_create_jugador(db, nombres[1])
                        p_db = Partida(
                            jugador1_id=j1.id,
                            jugador2_id=j2.id,
                            fecha=datetime.utcnow()
                        )
                        if ganador == "Empate":
                            p_db.ganador_id = None
                        elif partida["jugadores"][nombres[0]]["symbol"] == ganador:
                            p_db.ganador_id = j1.id
                            j1.ganadas += 1
                            j2.perdidas += 1
                        else:
                            p_db.ganador_id = j2.id
                            j2.ganadas += 1
                            j1.perdidas += 1
                        db.add(p_db)
                        db.commit()

            elif action == "reset":
                partida["board"] = ["" for _ in range(9)]
                partida["turn"] = "X"
                partida["ganador"] = None
                for j, info in partida["jugadores"].items():
                    await info["ws"].send_json({
                        "type": "state",
                        "board": partida["board"],
                        "turn": partida["turn"],
                        "winner": None
                    })

    except WebSocketDisconnect:
        if jugador_nombre and jugador_nombre in partida["jugadores"]:
            del partida["jugadores"][jugador_nombre]
