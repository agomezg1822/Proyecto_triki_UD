# clients/client_tk.py
import json
import asyncio
import threading
import queue
import tkinter as tk
import customtkinter as ctk
import websockets  # usa la librería 'websockets'
from typing import Optional

# Config CustomTkinter
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

# Cambia HOST si corres el servidor en otra IP/máquina
WS_HOST = "ws://127.0.0.1:8000"

class TrikiClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Triki - Cliente")
        self.root.geometry("420x520")

        self.name_var = tk.StringVar(value="Jugador")
        self.partida_var = tk.StringVar(value="")  # deja vacío para crear con REST
        self.symbol: Optional[str] = None
        self.connected = False
        self.ws = None

        # cola para recibir mensajes desde el hilo async
        self.incoming = queue.Queue()

        self.build_ui()
        # polling UI para procesar mensajes
        self.root.after(100, self.process_incoming)

        # cola para enviar acciones al hilo async
        self.send_queue = asyncio.Queue()

    def build_ui(self):
        top_frame = ctk.CTkFrame(self.root)
        top_frame.pack(padx=12, pady=12, fill="x")

        ctk.CTkLabel(top_frame, text="Nombre:").grid(row=0, column=0, sticky="w")
        ctk.CTkEntry(top_frame, textvariable=self.name_var).grid(row=0, column=1, sticky="we", padx=6)
        ctk.CTkLabel(top_frame, text="Partida (id):").grid(row=1, column=0, sticky="w")
        ctk.CTkEntry(top_frame, textvariable=self.partida_var).grid(row=1, column=1, sticky="we", padx=6)

        self.connect_btn = ctk.CTkButton(top_frame, text="Conectar", command=self.on_connect)
        self.connect_btn.grid(row=2, column=0, columnspan=2, pady=8, sticky="we")

        # tablero
        self.board_frame = ctk.CTkFrame(self.root)
        self.board_frame.pack(padx=12, pady=8)

        self.cell_buttons = []
        for i in range(9):
            btn = ctk.CTkButton(self.board_frame, text="", width=90, height=90, font=("Arial", 28),
                                command=lambda i=i: self.on_cell_click(i))
            row = i // 3
            col = i % 3
            btn.grid(row=row, column=col, padx=6, pady=6)
            self.cell_buttons.append(btn)

        # info
        self.info_label = ctk.CTkLabel(self.root, text="Desconectado", anchor="center")
        self.info_label.pack(pady=12)

        # reset
        self.reset_btn = ctk.CTkButton(self.root, text="Reiniciar partida", command=self.on_reset)
        self.reset_btn.pack(pady=6, fill="x", padx=12)
        self.reset_btn.configure(state="disabled")

    def process_incoming(self):
        """Procesa mensajes puestos por el hilo async en self.incoming"""
        while True:
            try:
                msg = self.incoming.get_nowait()
            except queue.Empty:
                break
            try:
                self.handle_message(msg)
            except Exception as e:
                print("Error procesando mensaje:", e)
        self.root.after(100, self.process_incoming)

    def handle_message(self, raw_text):
        data = json.loads(raw_text)
        t = data.get("type")
        if t == "state" or t == "move_result":
            board = data.get("board", [""] * 9)
            winner = data.get("winner")
            current = data.get("current_player")
            self.update_board(board)
            if winner:
                self.info_label.configure(text=f"Juego terminado: {winner}")
                self.reset_btn.configure(state="normal")
            else:
                self.info_label.configure(text=f"Turno: {current}")
                self.reset_btn.configure(state="disabled")
        elif t == "info":
            self.info_label.configure(text=data.get("message", ""))
        elif t == "error":
            self.info_label.configure(text="Error: " + data.get("message", ""))
        else:
            # info genérica (ej: al conectarse se recibe)
            self.info_label.configure(text=str(data))

    def update_board(self, board):
        for i, val in enumerate(board):
            self.cell_buttons[i].configure(text=val if val else "")

    def on_connect(self):
        if not self.connected:
            # lanzar hilo que corre el loop asyncio
            partida_id = self.partida_var.get().strip()
            if partida_id == "":
                tk.messagebox.showinfo("Partida vacía", "Crea una partida desde el servidor (POST /api/create_partida) o ingresa un id.")
                return
            name = self.name_var.get().strip() or "Jugador"
            self.connect_btn.configure(state="disabled")
            threading.Thread(target=self.run_async_loop, args=(partida_id, name), daemon=True).start()
        else:
            tk.messagebox.showinfo("Ya conectado", "Ya estás conectado a una partida.")

    def on_cell_click(self, position: int):
        if not self.connected:
            tk.messagebox.showinfo("No conectado", "Conéctate primero.")
            return
        # enviar acción al hilo async
        asyncio.run_coroutine_threadsafe(self.send_queue.put({"action": "move", "position": position}), asyncio.get_event_loop())
        # Nota: el servidor validará turno y casilla.

    def on_reset(self):
        if not self.connected:
            return
        asyncio.run_coroutine_threadsafe(self.send_queue.put({"action": "reset"}), asyncio.get_event_loop())

    def run_async_loop(self, partida_id: str, name: str):
        """
        Se ejecuta en hilo separado. Crea un loop async y lo corre.
        """
        # cada hilo debe tener su propio event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.async_main(partida_id, name))
        except Exception as e:
            print("Error loop async:", e)
        finally:
            loop.close()

    async def async_main(self, partida_id: str, name: str):
        uri = f"{WS_HOST}/ws/{partida_id}"
        try:
            async with websockets.connect(uri) as ws:
                self.connected = True
                self.info_label.configure(text="Conectado. Esperando respuesta...")
                # enviar join
                await ws.send(json.dumps({"action": "join", "name": name}))
                # iniciar tareas: receiver and sender
                receiver = asyncio.create_task(self.receiver(ws))
                sender = asyncio.create_task(self.sender(ws))
                # mantener hasta que alguna termine (receiver se rompe al desconectar)
                done, pending = await asyncio.wait([receiver, sender], return_when=asyncio.FIRST_COMPLETED)
                for p in pending:
                    p.cancel()
        except Exception as e:
            # enviar error a UI
            self.incoming.put(json.dumps({"type": "error", "message": f"Conexión fallida: {e}"}))
            self.connected = False
            self.connect_btn.configure(state="normal")

    async def receiver(self, ws):
        try:
            async for msg in ws:
                # colocar en cola thread-safe para Tkinter
                self.incoming.put(msg)
        except Exception as e:
            self.incoming.put(json.dumps({"type": "error", "message": f"Receiver terminó: {e}"}))
            self.connected = False

    async def sender(self, ws):
        # listener que toma acciones de self.send_queue y las manda al websocket
        try:
            while True:
                action = await self.send_queue.get()
                if action["action"] == "move":
                    payload = {"action": "move", "position": action["position"]}
                elif action["action"] == "reset":
                    payload = {"action": "reset"}
                else:
                    payload = action
                await ws.send(json.dumps(payload))
        except Exception as e:
            self.incoming.put(json.dumps({"type": "error", "message": f"Sender terminado: {e}"}))

def run_app():
    root = ctk.CTk()
    app = TrikiClientApp(root)
    root.mainloop()

if __name__ == "__main__":
    run_app()