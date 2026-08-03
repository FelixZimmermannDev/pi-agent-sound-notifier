"""Explicit state for an interactive local chess game."""

from dataclasses import dataclass

import chess

from chess_analysis_coach.errors import InvalidMoveError, SessionStateError


@dataclass(frozen=True)
class PlayedMove:
    """A successfully applied move and the resulting session revision."""

    san: str
    uci: str
    revision: int


class LocalGameSession:
    """Own the board and validate all state transitions for one local game."""

    def __init__(self, board: chess.Board, *, player_color: chess.Color) -> None:
        self._board = board.copy(stack=True)
        self._player_color = player_color
        self._starting_ply_count = len(self._board.move_stack)
        self._revision = 0

    @property
    def player_color(self) -> chess.Color:
        return self._player_color

    @property
    def revision(self) -> int:
        return self._revision

    @property
    def is_player_turn(self) -> bool:
        return self._board.turn == self._player_color

    @property
    def is_game_over(self) -> bool:
        return self._board.is_game_over(claim_draw=True)

    @property
    def result(self) -> str:
        return self._board.result(claim_draw=True)

    def snapshot(self) -> chess.Board:
        """Return a defensive board copy, including repetition history."""
        return self._board.copy(stack=True)

    def apply_player_move(self, notation: str) -> PlayedMove:
        if not self.is_player_turn:
            raise SessionStateError("Wait for the local Stockfish opponent to move.")
        move = self._parse_move(notation)
        return self._apply_legal_move(move)

    def apply_bot_move(self, move: chess.Move) -> PlayedMove:
        if self.is_player_turn:
            raise SessionStateError("The local Stockfish opponent cannot move on your turn.")
        if move not in self._board.legal_moves:
            raise InvalidMoveError(f"The engine selected an illegal move: {move.uci()}.")
        return self._apply_legal_move(move)

    def undo_last_turn(self) -> int:
        """Undo back toward the previous position where the player can move."""
        if len(self._board.move_stack) <= self._starting_ply_count:
            raise SessionStateError("There are no moves to undo.")

        undone_moves = 0
        while len(self._board.move_stack) > self._starting_ply_count:
            self._board.pop()
            undone_moves += 1
            if self.is_player_turn:
                break

        self._revision += 1
        return undone_moves

    def _parse_move(self, notation: str) -> chess.Move:
        cleaned_notation = notation.strip()
        if not cleaned_notation:
            raise InvalidMoveError("Enter a move in SAN (for example Nf3) or UCI (g1f3).")

        try:
            return self._board.parse_san(cleaned_notation)
        except ValueError:
            try:
                move = chess.Move.from_uci(cleaned_notation.lower())
            except ValueError as error:
                raise InvalidMoveError(
                    f"'{cleaned_notation}' is not valid SAN or UCI move notation."
                ) from error

        if move not in self._board.legal_moves:
            raise InvalidMoveError(
                f"'{cleaned_notation}' is not legal in the current position."
            )
        return move

    def _apply_legal_move(self, move: chess.Move) -> PlayedMove:
        san = self._board.san(move)
        uci = move.uci()
        self._board.push(move)
        self._revision += 1
        return PlayedMove(san=san, uci=uci, revision=self._revision)
