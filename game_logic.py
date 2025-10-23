# game_logic.py
from typing import List, Optional, Tuple

class TrikiGame:
    def __init__(self):
        # Representa el tablero con 9 posiciones (0..8)
        self.board = [""] * 9
        self.current_player = "X"
        self.winner: Optional[str] = None
        self.moves = 0

    def reset(self):
        """Reinicia el tablero."""
        self.board = [""] * 9
        self.current_player = "X"
        self.winner = None
        self.moves = 0

    def make_move(self, position: int) -> Tuple[bool, str]:
        """
        Realiza una jugada.
        :param position: índice de 0 a 8.
        :return: (éxito, mensaje)
        """
        if self.winner:
            return False, f"Juego terminado. Ganador: {self.winner}"

        if not 0 <= position <= 8:
            return False, "Posición inválida"

        if self.board[position] != "":
            return False, "Casilla ocupada"

        # Realizar jugada
        self.board[position] = self.current_player
        self.moves += 1

        # Verificar si hay ganador o empate
        if self.check_winner():
            self.winner = self.current_player
            return True, f"¡Ganó {self.current_player}!"
        elif self.moves == 9:
            self.winner = "Empate"
            return True, "Empate"
        else:
            # Cambiar jugador
            self.current_player = "O" if self.current_player == "X" else "X"
            return True, "Jugada válida"

    def check_winner(self) -> bool:
        """Verifica si el jugador actual ha ganado."""
        b = self.board
        combos = [
            (0, 1, 2),
            (3, 4, 5),
            (6, 7, 8),
            (0, 3, 6),
            (1, 4, 7),
            (2, 5, 8),
            (0, 4, 8),
            (2, 4, 6),
        ]
        for a, b_, c in combos:
            if (
                self.board[a] == self.board[b_] == self.board[c]
                and self.board[a] != ""
            ):
                return True
        return False

    def get_board_state(self) -> List[str]:
        """Devuelve el estado actual del tablero."""
        return self.board

    def get_status(self) -> dict:
        """Devuelve el estado del juego en forma de diccionario."""
        return {
            "board": self.board,
            "current_player": self.current_player,
            "winner": self.winner,
            "moves": self.moves,
        }

    def calculate_score(self, result: str) -> int:
        """
        Calcula puntaje según resultado:
        - Ganar: 3 puntos
        - Empate: 1 punto
        - Perder: 0 puntos
        """
        if result == "win":
            return 3
        elif result == "draw":
            return 1
        else:
            return 0