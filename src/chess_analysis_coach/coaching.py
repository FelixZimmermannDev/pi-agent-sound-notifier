"""Small deterministic coaching cues derived from a candidate move."""

from dataclasses import dataclass

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


@dataclass(frozen=True)
class CandidateForecast:
    """Structured, heuristic context for a short principal variation."""

    phase: str
    context_label: str
    tactical: bool
    goal: str
    opponent_reply_san: str | None
    opponent_counter: str | None
    opponent_relevant: bool
    own_follow_up_san: str | None
    own_follow_up_goal: str | None
    own_follow_up_relevant: bool


@dataclass(frozen=True)
class _LineMove:
    san: str
    is_capture: bool
    gives_check: bool
    is_promotion: bool
    attacked_names: tuple[str, ...]

    @property
    def is_tactical(self) -> bool:
        return (
            self.is_capture
            or self.gives_check
            or self.is_promotion
            or bool(self.attacked_names)
        )


def build_candidate_forecast(
    board: chess.Board,
    candidate: CandidateMove,
) -> CandidateForecast:
    """Classify visible plans and counters without claiming deep tactical proof."""
    phase, phase_label = _classify_phase(board)
    try:
        root_move = chess.Move.from_uci(candidate.uci)
    except ValueError:
        root_move = None
    if root_move is None or root_move not in board.legal_moves:
        return CandidateForecast(
            phase=phase,
            context_label=f"{phase_label} · positionell",
            tactical=False,
            goal="Figurenaktivität und Stellungsqualität verbessern",
            opponent_reply_san=None,
            opponent_counter=None,
            opponent_relevant=False,
            own_follow_up_san=None,
            own_follow_up_goal=None,
            own_follow_up_relevant=False,
        )

    line = _forecast_line(board, candidate)
    root = line[0] if line else None
    goal = _root_goal(board, root_move, root)
    tactical = board.is_check() or any(move.is_tactical for move in line)
    opponent = line[1] if len(line) >= 2 else None
    follow_up = line[2] if len(line) >= 3 else None
    root_gives_check = root.gives_check if root is not None else False
    opponent_relevant = bool(
        opponent is not None and (opponent.is_tactical or root_gives_check)
    )
    own_relevant = bool(follow_up is not None and follow_up.is_tactical)

    return CandidateForecast(
        phase=phase,
        context_label=f"{phase_label} · {'taktisch' if tactical else 'positionell'}",
        tactical=tactical,
        goal=goal,
        opponent_reply_san=opponent.san if opponent is not None else None,
        opponent_counter=(
            _counter_description(opponent, answering_check=root_gives_check)
            if opponent is not None
            else None
        ),
        opponent_relevant=opponent_relevant,
        own_follow_up_san=follow_up.san if follow_up is not None else None,
        own_follow_up_goal=(
            _follow_up_description(follow_up) if follow_up is not None else None
        ),
        own_follow_up_relevant=own_relevant,
    )


def explain_candidate_plan(board: chess.Board, candidate: CandidateMove) -> str:
    """Render the structured forecast as one complete text fallback."""
    forecast = build_candidate_forecast(board, candidate)
    parts = [f"Ziel: {forecast.goal}."]
    if forecast.opponent_reply_san is not None:
        parts.append(f"Erwartete Antwort: {forecast.opponent_reply_san}.")
    if forecast.own_follow_up_san is not None:
        parts.append(f"Nächster eigener Schritt: {forecast.own_follow_up_san}.")
    if forecast.opponent_relevant and forecast.opponent_counter is not None:
        parts.append(f"Relevanter Counter: {forecast.opponent_counter}.")
    return " ".join(parts)


def _forecast_line(
    board: chess.Board,
    candidate: CandidateMove,
) -> tuple[_LineMove, ...]:
    line_board = board.copy(stack=False)
    line: list[_LineMove] = []
    variation_uci = candidate.principal_variation_uci or (candidate.uci,)
    for uci in variation_uci[:3]:
        try:
            move = chess.Move.from_uci(uci)
        except ValueError:
            break
        if move not in line_board.legal_moves:
            break
        san = line_board.san(move)
        is_capture = line_board.is_capture(move)
        is_promotion = move.promotion is not None
        line_board.push(move)
        line.append(
            _LineMove(
                san=san,
                is_capture=is_capture,
                gives_check=line_board.is_check(),
                is_promotion=is_promotion,
                attacked_names=tuple(
                    _attacked_valuable_pieces(line_board, move.to_square)
                ),
            )
        )
    return tuple(line)


def _root_goal(
    board: chess.Board,
    move: chess.Move,
    forecast: _LineMove | None,
) -> str:
    moving_piece = board.piece_at(move.from_square)
    goals: list[str] = []
    if board.is_castling(move):
        goals.append("den König sichern und die Türme verbinden")
    if board.is_capture(move):
        goals.append("Material schlagen oder sinnvoll tauschen")
    if (
        moving_piece is not None
        and moving_piece.piece_type in {chess.KNIGHT, chess.BISHOP}
        and chess.square_rank(move.from_square)
        == (0 if moving_piece.color == chess.WHITE else 7)
    ):
        goals.append("eine Leichtfigur entwickeln")
    if (
        moving_piece is not None
        and moving_piece.piece_type == chess.PAWN
        and chess.square_file(move.to_square) in {2, 3, 4, 5}
        and chess.square_rank(move.to_square)
        == (3 if moving_piece.color == chess.WHITE else 4)
    ):
        goals.append("Raum und Kontrolle im Zentrum gewinnen")
    if forecast is not None and forecast.gives_check:
        goals.append("mit Tempo Schach geben")
    if forecast is not None and len(forecast.attacked_names) >= 2:
        goals.append("einen taktischen Mehrfachangriff aufbauen")
    return " und ".join(goals) if goals else "Figurenaktivität und Stellungsqualität verbessern"


def _counter_description(move: _LineMove, *, answering_check: bool) -> str:
    if answering_check:
        return f"{move.san} beantwortet das Schach"
    if move.gives_check:
        return f"{move.san} gibt Schach und erzwingt eine Reaktion"
    if move.is_capture:
        return f"{move.san} schlägt oder tauscht Material"
    if move.attacked_names:
        return f"{move.san} greift {', '.join(move.attacked_names[:2])} an"
    return f"{move.san} ist Stockfishs positioneller Gegenzug"


def _follow_up_description(move: _LineMove) -> str:
    if move.gives_check:
        return f"{move.san} setzt mit Schach fort"
    if move.is_capture:
        return f"{move.san} nutzt die Variante für einen Materialtausch"
    if move.attacked_names:
        return f"{move.san} erhöht den Druck auf {', '.join(move.attacked_names[:2])}"
    return f"{move.san} setzt den positionellen Plan fort"


def _classify_phase(board: chess.Board) -> tuple[str, str]:
    piece_values = {
        chess.KNIGHT: 3,
        chess.BISHOP: 3,
        chess.ROOK: 5,
        chess.QUEEN: 9,
    }
    non_pawn_material = sum(
        len(board.pieces(piece_type, color)) * value
        for piece_type, value in piece_values.items()
        for color in chess.COLORS
    )
    if non_pawn_material <= 24:
        return "endgame", "Endspiel"
    if board.fullmove_number <= 10 and non_pawn_material >= 48:
        return "opening", "Eröffnung"
    return "middlegame", "Mittelspiel"


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
