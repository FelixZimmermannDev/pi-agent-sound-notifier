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


def explain_candidate_plan(board: chess.Board, candidate: CandidateMove) -> str:
    """Summarize one short engine line as goal, reply, and continuation."""
    try:
        root_move = chess.Move.from_uci(candidate.uci)
    except ValueError:
        return "Ziel: Die Figurenaktivität gemäß der Stockfish-Variante verbessern."
    if root_move not in board.legal_moves:
        return "Ziel: Die Figurenaktivität gemäß der Stockfish-Variante verbessern."

    moving_piece = board.piece_at(root_move.from_square)
    goals: list[str] = []
    if board.is_castling(root_move):
        goals.append("den König sichern und die Türme verbinden")
    if board.is_capture(root_move):
        goals.append("Material schlagen oder sinnvoll tauschen")
    if (
        moving_piece is not None
        and moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}
        and chess.square_rank(root_move.from_square)
        == (0 if moving_piece.color == chess.WHITE else 7)
    ):
        goals.append("eine Leichtfigur entwickeln")
    if (
        moving_piece is not None
        and moving_piece.piece_type == chess.PAWN
        and chess.square_file(root_move.to_square) in {2, 3, 4, 5}
        and chess.square_rank(root_move.to_square)
        == (3 if moving_piece.color == chess.WHITE else 4)
    ):
        goals.append("Raum und Kontrolle im Zentrum gewinnen")

    line_board = board.copy(stack=False)
    line_san: list[str] = []
    tactical_events: list[str] = []
    root_gives_check = False
    variation_uci = candidate.principal_variation_uci or (candidate.uci,)
    for ply, uci in enumerate(variation_uci[:3]):
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            break
        if move not in line_board.legal_moves:
            break
        san = line_board.san(move)
        is_capture = line_board.is_capture(move)
        line_board.push(move)
        line_san.append(san)
        if ply == 0 and line_board.is_check():
            root_gives_check = True
        if ply > 0 and is_capture:
            tactical_events.append(f"{san} führt zu einem Materialtausch")
        if ply > 0 and line_board.is_check():
            tactical_events.append(f"{san} setzt Schach")

    if root_gives_check:
        goals.append("mit Tempo Schach geben")
    if not goals:
        goals.append("Figurenaktivität und Stellungsqualität verbessern")

    parts = ["Ziel: " + " und ".join(goals) + "."]
    if len(line_san) >= 2:
        parts.append(f"Erwartete Antwort: {line_san[1]}.")
    elif len(candidate.principal_variation_san) >= 2:
        parts.append(
            f"Erwartete Antwort: {candidate.principal_variation_san[1]}."
        )
    if len(line_san) >= 3:
        parts.append(f"Nächster eigener Schritt: {line_san[2]}.")
    elif len(candidate.principal_variation_san) >= 3:
        parts.append(
            f"Nächster eigener Schritt: {candidate.principal_variation_san[2]}."
        )
    if tactical_events:
        parts.append("Zwischenidee: " + "; ".join(tactical_events[:2]) + ".")
    return " ".join(parts)


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
