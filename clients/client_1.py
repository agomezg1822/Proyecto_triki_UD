import asyncio
import json
import websockets
import customtkinter as ctk
from threading import Thread

SERVER_URL = "ws://127.0.0.1:8000/ws"

class TrikiApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Triki Multijugador 🎮")
        self.geometry("420x550")

        # ---- Interfaz inicial ----
        self.label = ctk.CTkLabel(self, text="Conectar a Partida", font=("Arial", 18))
        self.label.pack(pady=10)

        self.entry_partida = ctk.CTkEntry(self, placeholder_text="ID de partida")
        self.entry_partida.pack(pady=5)

        self.entry_nombre = ctk.CTkEntry(self, placeholder_text="Tu nombre")
        self.entry_nombre.pack(pady=5)

        self.btn_conectar = ctk.CTkButton(self, text="Conectar", command=self.connect_to_server)
        self.btn_conectar.pack(pady=10)

        # ---- Panel del tablero ----
        self.board_frame = ctk.CTkFrame(self)
        self.cells = []
        for i in range(3):
            row = []
            for j in range(3):
                btn = ctk.CTkButton(self.board_frame, text="", width=100, height=100,
                                     font=("Arial", 28), command=lambda x=i, y=j: self.play_move(x, y))
                btn.grid(row=i, column=j, padx=5, pady=5)
                row.append(btn)
            self.cells.append(row)

        self.status_label = ctk.CTkLabel(self, text="", font=("Arial", 16))
        self.status_label.pack(pady=10)

        self.symbol = None
        self.partida_id = None
        self.websocket = None
        self.loop = None

    def connect_to_server(self):
        self.partida_id = self.entry_partida.get().strip()
        self.nombre = self.entry_nombre.get().strip()
        if not self.partida_id or not self.nombre:
            self.status_label.configure(text="⚠️ Ingresa ID y nombre.")
            return

        self.board_frame.pack(pady=15)
        self.status_label.configure(text="Conectando...")

        Thread(target=self.run_async, daemon=True).start()

    def run_async(self):
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self.ws_handler())

    async def ws_handler(self):
        try:
            async with websockets.connect(f"{SERVER_URL}/{self.partida_id}") as ws:
                self.websocket = ws
                # Enviar mensaje de join
                await ws.send(json.dumps({"action": "join", "name": self.nombre}))

                # Recibir mensajes del servidor
                async for msg in ws:
                    data = json.loads(msg)
                    self.handle_message(data)
        except Exception as e:
            self.status_label.configure(text=f"❌ Error conexión: {e}")

    def handle_message(self, data):
        tipo = data.get("type")
        if tipo == "info":
            msg = data.get("message", "")
            self.symbol = data.get("symbol", self.symbol)
            self.status_label.configure(text=msg)
        elif tipo in ("state", "move_result"):
            board = data.get("board", [])
            self.update_board(board)
            winner = data.get("winner")
            if winner:
                self.status_label.configure(text=f"🎉 {winner}")
        elif tipo == "error":
            self.status_label.configure(text=f"⚠️ {data.get('message')}")

    def update_board(self, board):
        for i in range(3):
            for j in range(3):
                val = board[i * 3 + j]
                self.cells[i][j].configure(text=val or "")

    def play_move(self, i, j):
        if not self.websocket or not self.symbol:
            return
        pos = i * 3 + j
        asyncio.run_coroutine_threadsafe(
            self.websocket.send(json.dumps({"action": "move", "position": pos})),
            self.loop
        )

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("blue")
    app = TrikiApp()
    app.mainloop()
