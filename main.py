# main.py
import json
import uuid
import asyncio
from typing import Dict, List, Any
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from game_logic import TrikiGame
from database import engine, Base  # las tablas ya creadas en tareas previas

app = FastAPI(
    title="Triki Multiplataforma",
    description="Servidor FastAPI con WebSockets para Triki multijugador.",
    version="1.0"
)

# montar carpeta static si usas la parte web
app.mount("/static", StaticFiles(directory="static"), name="static")

# Crear tablas (si no se han creado)
Base.metadata.create_all(bind=engine)

# ----- Estructuras en memoria para gestionar partidas -----
# partidas: partida_id -> TrikiGame
PARTIDAS: Dict[str, TrikiGame] = {}

# conexiones: partida_id -> list of websockets
CONNS: Dict[str, List[WebSocket]] = {}

# mapa de websocket -> player info { "name": str, "symbol": "X"/"O" }
PLAYER_INFO: Dict[WebSocket, Dict[str, Any]] = {}

# lock para evitar race conditions al manipular las estructuras
PARTIDAS_LOCK = asyncio.Lock()


# ======= Utilidades =========
async def broadcast_to_partida(partida_id: str, message: dict):
    """Envía mensaje JSON a todos los websockets conectados a la partida."""
    if partida_id not in CONNS:
        return
    dead = []
    for ws in list(CONNS[partida_id]):
        try:
            await ws.send_text(json.dumps(message))
        except Exception:
            # recolectar conexiones muertas para limpiar
            dead.append(ws)
    # limpiar
    for d in dead:
        await disconnect_ws_from_partida(partida_id, d)


async def disconnect_ws_from_partida(partida_id: str, websocket: WebSocket):
    try:
        if websocket in CONNS.get(partida_id, []):
            CONNS[partida_id].remove(websocket)
        if websocket in PLAYER_INFO:
            PLAYER_INFO.pop(websocket)
    except Exception:
        pass


def make_state_message(game: TrikiGame) -> dict:
    """Construye el payload con el estado del juego para enviar a clientes."""
    return {
        "type": "state",
        "board": game.get_board_state(),
        "current_player": game.current_player,
        "winner": game.winner,
        "moves": game.moves,
    }


# ======= Endpoints REST simples ========
@app.get("/")
async def root():
    return HTMLResponse("""
    <html>
      <head><meta charset="utf-8"><title>Triki - Servidor</title></head>
      <body>
        <h2>Servidor Triki activo ✅</h2>
        <p>Documentación OpenAPI en <a href="/docs">/docs</a></p>
      </body>
    </html>
    """)


@app.post("/api/create_partida")
async def api_create_partida():
    """Crea una nueva partida y devuelve su id (UUID corto)."""
    partida_id = str(uuid.uuid4())[:8]
    async with PARTIDAS_LOCK:
        PARTIDAS[partida_id] = TrikiGame()
        CONNS[partida_id] = []
    return {"partida_id": partida_id}


@app.get("/api/partidas")
async def api_list_partidas():
    """Lista partidas activas (id y número de jugadores conectados)."""
    result = []
    for pid, conns in CONNS.items():
        result.append({"partida_id": pid, "players_connected": len(conns)})
    return result


# ======= WebSocket endpoint por partida ========
@app.websocket("/ws/{partida_id}")
async def websocket_partida(websocket: WebSocket, partida_id: str):
    """
    Protocolo JSON básico:
    - Cliente -> servidor:
      {"action":"join", "name":"Andres"}
      {"action":"move", "position": 4}
      {"action":"reset"}
    - Servidor -> cliente:
      {"type":"state", ...}  # estado completo
      {"type":"info", "message":"..."}
    """
    await websocket.accept()
    # validar existencia de partida
    async with PARTIDAS_LOCK:
        if partida_id not in PARTIDAS:
            # crear la partida si no existe
            PARTIDAS[partida_id] = TrikiGame()
            CONNS[partida_id] = []

        # añadir conexión
        CONNS[partida_id].append(websocket)

    try:
        # Esperamos al mensaje de join con el nombre del jugador
        data_text = await websocket.receive_text()
        try:
            data = json.loads(data_text)
        except Exception:
            await websocket.send_text(json.dumps({"type": "error", "message": "JSON inválido"}))
            await disconnect_ws_from_partida(partida_id, websocket)
            return

        if data.get("action") != "join" or "name" not in data:
            await websocket.send_text(json.dumps({"type": "error", "message": "Primero debes enviar action='join' con tu nombre."}))
            await disconnect_ws_from_partida(partida_id, websocket)
            return

        player_name = data["name"]

        # Asignar símbolo (X u O)
        # Si ya hay 0 jugadores -> X, si 1 jugador -> O, si 2+ -> espectador (no puede jugar)
        existing_players = [PLAYER_INFO[w]["symbol"] for w in CONNS[partida_id] if w in PLAYER_INFO]
        if "X" not in existing_players:
            symbol = "X"
        elif "O" not in existing_players:
            symbol = "O"
        else:
            symbol = None  # espectador

        PLAYER_INFO[websocket] = {"name": player_name, "symbol": symbol}

        # informar al cliente su símbolo
        await websocket.send_text(json.dumps({"type": "info", "message": f"Conectado a partida {partida_id}", "symbol": symbol}))

        # enviar estado inicial a todos
        await broadcast_to_partida(partida_id, {"type": "info", "message": f"{player_name} se unió como {symbol}"})
        await broadcast_to_partida(partida_id, make_state_message(PARTIDAS[partida_id]))

        # main loop: recibir acciones
        while True:
            text = await websocket.receive_text()
            payload = json.loads(text)
            action = payload.get("action")

            game = PARTIDAS[partida_id]

            if action == "move":
                pos = payload.get("position")
                info = PLAYER_INFO.get(websocket, {})
                symbol = info.get("symbol")
                name = info.get("name", "Jugador")

                if symbol is None:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Eres espectador, no puedes jugar."}))
                    continue

                # validar turno
                if game.winner:
                    await websocket.send_text(json.dumps({"type": "error", "message": f"Juego terminado: {game.winner}"}))
                    continue

                if symbol != game.current_player:
                    await websocket.send_text(json.dumps({"type": "error", "message": "No es tu turno"}))
                    continue

                # intentar hacer la jugada usando la lógica central
                ok, msg = game.make_move(pos)
                # si ok, transmitir nuevo estado a todos
                if ok:
                    await broadcast_to_partida(partida_id, {
                        "type": "move_result",
                        "message": msg,
                        "by": name,
                        "symbol": symbol,
                        **make_state_message(game)
                    })
                    # si hay ganador o empate, informar y (opcional) reiniciar después de X segundos
                    if game.winner:
                        await broadcast_to_partida(partida_id, {"type": "info", "message": f"Juego terminado: {game.winner}"})
                else:
                    await websocket.send_text(json.dumps({"type": "error", "message": msg}))

            elif action == "reset":
                PARTIDAS[partida_id] = TrikiGame()
                await broadcast_to_partida(partida_id, {"type": "info", "message": "Juego reiniciado"})
                await broadcast_to_partida(partida_id, make_state_message(PARTIDAS[partida_id]))

            else:
                await websocket.send_text(json.dumps({"type": "error", "message": "Action desconocida"}))

    except WebSocketDisconnect:
        # limpiar
        await disconnect_ws_from_partida(partida_id, websocket)
        await broadcast_to_partida(partida_id, {"type": "info", "message": "Un jugador se desconectó"})
    except Exception as e:
        await disconnect_ws_from_partida(partida_id, websocket)
        await broadcast_to_partida(partida_id, {"type": "error", "message": f"Error servidor: {str(e)}"})