async function cargarEstadisticas() {
            const res = await fetch('/api/estadisticas');
            const jugadores = await res.json();
            const tbody = document.getElementById('tabla-body');
            tbody.innerHTML = "";

            jugadores.forEach((j, i) => {
                const fila = `
                    <tr class="hover:bg-gray-800">
                        <td class="py-2 px-4">${i + 1}</td>
                        <td class="py-2 px-4">${j.nombre}</td>
                        <td class="py-2 px-4">${j.ganadas}</td>
                        <td class="py-2 px-4">${j.perdidas}</td>
                        <td class="py-2 px-4">${j.puntaje}</td>
                    </tr>
                `;
                tbody.innerHTML += fila;
            });
        }

        cargarEstadisticas();