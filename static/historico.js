async function cargarTabla() {
      const res = await fetch('/api/historico');
      const data = await res.json();
      let html = `
        <table class="min-w-full border border-gray-700 text-center">
          <thead class="bg-gray-700">
            <tr>
              <th class="py-3 px-4 border-b border-gray-600">Jugador 1</th>
              <th class="py-3 px-4 border-b border-gray-600">Jugador 2</th>
              <th class="py-3 px-4 border-b border-gray-600">Ganador</th>
              <th class="py-3 px-4 border-b border-gray-600">Fecha</th>
            </tr>
          </thead>
          <tbody>`;
      for (const p of data) {
        html += `
          <tr class="hover:bg-gray-700">
            <td class="py-2 px-4 border-b border-gray-700">${p.jugador1}</td>
            <td class="py-2 px-4 border-b border-gray-700">${p.jugador2}</td>
            <td class="py-2 px-4 border-b border-gray-700">${p.ganador}</td>
            <td class="py-2 px-4 border-b border-gray-700">${p.fecha}</td>
          </tr>`;
      }
      html += `</tbody></table>`;
      document.getElementById('tabla-container').innerHTML = html;
    }
    cargarTabla();