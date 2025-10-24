const menu = document.getElementById('menu');
    const juego = document.getElementById('juego');
    const tableroDiv = document.getElementById('tablero');
    const turnoDiv = document.getElementById('turno');
    const tituloPartida = document.getElementById('tituloPartida');

    let ws = null;
    let symbol = null;
    let currentPlayer = null;
    let partidaId = null;

    document.getElementById('createBtn').onclick = async () => {
      const res = await fetch('/api/create_partida', {method: 'POST'});
      const data = await res.json();
      document.getElementById('partidaId').value = data.partida_id;
      alert(`✅ Partida creada con ID: ${data.partida_id}`);
    };

    document.getElementById('joinBtn').onclick = () => {
      const name = document.getElementById('name').value.trim();
      partidaId = document.getElementById('partidaId').value.trim();

      if (!name || !partidaId) {
        alert('⚠️ Ingresa nombre e ID de partida');
        return;
      }

      menu.classList.add('hidden');
      juego.classList.remove('hidden');
      tituloPartida.textContent = `ID: ${partidaId}`;

      ws = new WebSocket(`ws://${location.host}/ws/${partidaId}`);

      ws.onopen = () => {
        ws.send(JSON.stringify({action: "join", name}));
      };

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data);
        if (msg.type === "info") {
          if (msg.symbol) symbol = msg.symbol;
          turnoDiv.textContent = msg.message;
        }
        if (msg.type === "state") {
          renderBoard(msg.board, msg.current_player, msg.winner);
        }
        if (msg.type === "error") alert(msg.message);
      };

      ws.onclose = () => {
        turnoDiv.textContent = "❌ Conexión cerrada";
      };
    };

    function renderBoard(board, current, winner) {
      tableroDiv.innerHTML = '';
      currentPlayer = current;
      board.forEach((cell, i) => {
        const btn = document.createElement('button');
        btn.textContent = cell || '';
        btn.className = "w-20 h-20 text-3xl border border-gray-400 bg-white rounded hover:bg-gray-200";
        btn.onclick = () => makeMove(i);
        tableroDiv.appendChild(btn);
      });
      if (winner) {
        turnoDiv.textContent = winner.includes('Empate') ? "🤝 Empate!" : `🏁 ${winner}`;
      } else {
        turnoDiv.textContent = (symbol === current) ? "Tu turno!" : "Esperando rival...";
      }
    }

    function makeMove(pos) {
      if (ws && currentPlayer === symbol) {
        ws.send(JSON.stringify({action: "move", position: pos}));
      }
    }

    document.getElementById('volverBtn').onclick = () => {
      location.reload();
    };