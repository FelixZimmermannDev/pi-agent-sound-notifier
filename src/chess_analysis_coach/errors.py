"""User-facing errors raised by the chess analysis workflow."""


class CoachError(Exception):
    """Base class for expected chess coach failures."""


class PositionError(CoachError):
    """The supplied position cannot be used for move recommendations."""


class InvalidPositionError(PositionError):
    """The supplied FEN does not describe a valid chess position."""


class PositionNotAnalyzableError(PositionError):
    """The position is valid but has no move to recommend."""


class SessionError(CoachError):
    """Base class for expected local-game session failures."""


class InvalidMoveError(SessionError):
    """Player or engine move input is malformed or illegal."""


class SessionStateError(SessionError):
    """An operation is not allowed in the current local-game state."""


class EngineError(CoachError):
    """Base class for Stockfish process and analysis failures."""


class EngineUnavailableError(EngineError):
    """Stockfish could not be started."""


class EngineAnalysisError(EngineError):
    """Stockfish started but could not produce a usable analysis."""
