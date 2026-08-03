"""Pure geometry helpers for moving and resizing the overlay window."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntFlag, auto


class ResizeEdge(IntFlag):
    """Edges selected by a pointer near the overlay frame."""

    NONE = 0
    LEFT = auto()
    TOP = auto()
    RIGHT = auto()
    BOTTOM = auto()


@dataclass(frozen=True, slots=True)
class Bounds:
    """Screen-space window bounds using an exclusive right/bottom edge."""

    left: int
    top: int
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("Bounds width and height must be positive.")

    @property
    def right(self) -> int:
        return self.left + self.width

    @property
    def bottom(self) -> int:
        return self.top + self.height


@dataclass(frozen=True, slots=True)
class RelativePoint:
    """A location in the overlay where both axes range from zero to one."""

    x: float
    y: float

    def __post_init__(self) -> None:
        if not 0.0 <= self.x <= 1.0 or not 0.0 <= self.y <= 1.0:
            raise ValueError("Relative coordinates must be between 0 and 1.")

    def to_pixels(self, width: int, height: int) -> tuple[float, float]:
        if width <= 0 or height <= 0:
            raise ValueError("Target width and height must be positive.")
        return self.x * width, self.y * height


def hit_test_edges(
    x: float,
    y: float,
    width: int,
    height: int,
    margin: int,
) -> ResizeEdge:
    """Return the frame edges close enough to be resized at ``x, y``."""

    if width <= 0 or height <= 0:
        raise ValueError("Frame width and height must be positive.")
    if margin <= 0:
        raise ValueError("Resize margin must be positive.")

    effective_margin = min(margin, width / 2, height / 2)
    edges = ResizeEdge.NONE

    if x <= effective_margin:
        edges |= ResizeEdge.LEFT
    elif x >= width - effective_margin:
        edges |= ResizeEdge.RIGHT

    if y <= effective_margin:
        edges |= ResizeEdge.TOP
    elif y >= height - effective_margin:
        edges |= ResizeEdge.BOTTOM

    return edges


def transformed_bounds(
    original: Bounds,
    edges: ResizeEdge,
    delta_x: int,
    delta_y: int,
    *,
    minimum_width: int,
    minimum_height: int,
) -> Bounds:
    """Move or resize ``original`` while preserving the configured minimum size."""

    if minimum_width <= 0 or minimum_height <= 0:
        raise ValueError("Minimum dimensions must be positive.")

    if edges == ResizeEdge.NONE:
        return Bounds(
            original.left + delta_x,
            original.top + delta_y,
            original.width,
            original.height,
        )

    left = original.left
    right = original.right
    top = original.top
    bottom = original.bottom

    if edges & ResizeEdge.LEFT:
        left = min(original.left + delta_x, right - minimum_width)
    elif edges & ResizeEdge.RIGHT:
        right = max(original.right + delta_x, left + minimum_width)

    if edges & ResizeEdge.TOP:
        top = min(original.top + delta_y, bottom - minimum_height)
    elif edges & ResizeEdge.BOTTOM:
        bottom = max(original.bottom + delta_y, top + minimum_height)

    return Bounds(left, top, right - left, bottom - top)
