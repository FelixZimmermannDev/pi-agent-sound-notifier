"""Small deterministic coaching cues derived from a candidate move."""

import chess

from chess_analysis_coach.models import CandidateMove

_PIECE_NAMES = {
    chess.PAWN: "Bauern",
    chess.KNIGHT: "Springer",
    chess.BISHOP: "Läufer",
    chess.ROOK: "Turm",
    chess.QUEEN: "Dame",
    chess.KING: "König",
}


def explain_candidate(board: chess.Board, candidate: CandidateMove) -> str:
    """Describe visible tactical properties without replacing engine analysis."""
    try:
        move = chess.Move.from_uci(candidate.uci)
    except ValueError:
        return "Stockfish bevorzugt diesen Zug in der angezeigten Variante."
    if move not in board.legal_moves:
        return "Stockfish bevorzugt diesen Zug in der angezeigten Variante."

    cues: list[str] = []
    moving_piece = board.piece_at(move.from_square)

    if board.is_castling(move):
        cues.append("Rochiert und verbessert die Königssicherheit.")

    if board.is_capture(move):
        captured_piece = board.piece_at(move.to_square)
        captured_name = _PIECE_NAMES[
            chess.PAWN if captured_piece is None else captured_piece.piece_type
        ]
        cues.append(f"Schlägt die gegnerische Figur: {captured_name}.")

    if move.promotion is not None:
        cues.append(f"Wandelt den Bauern in {_PIECE_NAMES[move.promotion]} um.")

    resulting_board = board.copy(stack=False)
    resulting_board.push(move)
    if resulting_board.is_check():
        cues.append("Setzt den gegnerischen König unter Schach.")

    attacked_names = _attacked_valuable_pieces(resulting_board, move.to_square)
    if len(attacked_names) >= 2:
        cues.append(
            "Erzeugt einen Mehrfachangriff auf " + " und ".join(attacked_names[:2]) + "."
        )
    elif attacked_names and moving_piece is not None:
        cues.append(f"Greift folgende gegnerische Figur an: {attacked_names[0]}.")

    if not cues:
        cues.append("Stockfish bevorzugt den Zug aufgrund der angezeigten Variante.")
    return " ".join(cues)


def _attacked_valuable_pieces(
    board: chess.Board,
    attacking_square: chess.Square,
) -> list[str]:
    attacking_piece = board.piece_at(attacking_square)
    if attacking_piece is None:
        return []

    opponent = not attacking_piece.color
    attacked_names: list[str] = []
    for square in board.attacks(attacking_square):
        target = board.piece_at(square)
        if (
            target is not None
            and target.color == opponent
            and target.piece_type in {
                chess.KNIGHT,
                chess.BISHOP,
                chess.ROOK,
                chess.QUEEN,
            }
        ):
            attacked_names.append(_PIECE_NAMES[target.piece_type])
    return attacked_names
