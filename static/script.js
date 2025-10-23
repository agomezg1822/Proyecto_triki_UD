// static/script.js
let ws = null;
const tablero = document.getElementById("tablero");
const info = document.getElementById("info");



// Crear partida
document.getElementById("crearPartida").onclick = async () => {
  const res = await fetch("/api/create_partida", { method: "POST" });
  const data = await res.json();
  info.innerText = `ID de partida: ${data.partida_id}`;
};

// Conectar al WS
document.getElementById("conectar").onclick = async () => {
  const id = document.getElementById("inputPartida").value.trim();
  const name = document.getElementById("inputName").value.trim();
  if (!id || !name) {
    info.innerText = "Debes ingresar un ID y un nombre.";
    return;
  }

  ws = new WebSocket(`ws://127.0.0.1:8000/ws/${id}`);
  ws.onopen = () => {
    ws.send(JSON.stringify({ action: "join", name }));
    info.innerText = "Conectado al servidor...";
  };

  ws.onmessage = (event) => {
    const msg = JSON.parse(event.data);
    if (msg.type === "state" || msg.type === "move_result") {
      updateBoard(msg.board);
      if (msg.winner) info.innerText = msg.winner;
      else info.innerText = `Turno de ${msg.current_player}`;
    } else if (msg.type === "info") {
      info.innerText = msg.message;
    } else if (msg.type === "error") {
      info.innerText = "⚠️ " + msg.message;
    }
  };
};

function updateBoard(board) {
  const cells = tablero.querySelectorAll("button");
  board.forEach((val, i) => (cells[i].innerText = val || ""));
}
