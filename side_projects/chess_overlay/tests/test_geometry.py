import pytest

from chess_overlay.geometry import (
    Bounds,
    RelativePoint,
    ResizeEdge,
    hit_test_edges,
    transformed_bounds,
)


def test_hit_test_identifies_corner_and_center() -> None:
    assert hit_test_edges(4, 5, 600, 400, 14) == (
        ResizeEdge.LEFT | ResizeEdge.TOP
    )
    assert hit_test_edges(300, 200, 600, 400, 14) == ResizeEdge.NONE


def test_center_drag_moves_window_without_resizing_it() -> None:
    original = Bounds(left=100, top=80, width=600, height=500)

    moved = transformed_bounds(
        original,
        ResizeEdge.NONE,
        35,
        -20,
        minimum_width=320,
        minimum_height=320,
    )

    assert moved == Bounds(left=135, top=60, width=600, height=500)


def test_corner_drag_resizes_while_opposite_corner_stays_fixed() -> None:
    original = Bounds(left=100, top=80, width=600, height=500)

    resized = transformed_bounds(
        original,
        ResizeEdge.LEFT | ResizeEdge.TOP,
        40,
        30,
        minimum_width=320,
        minimum_height=320,
    )

    assert resized == Bounds(left=140, top=110, width=560, height=470)
    assert resized.right == original.right
    assert resized.bottom == original.bottom


def test_resize_stops_at_minimum_dimensions() -> None:
    original = Bounds(left=100, top=80, width=400, height=350)

    resized = transformed_bounds(
        original,
        ResizeEdge.LEFT | ResizeEdge.TOP,
        250,
        200,
        minimum_width=320,
        minimum_height=320,
    )

    assert resized == Bounds(left=180, top=110, width=320, height=320)


def test_relative_point_maps_to_current_overlay_size() -> None:
    assert RelativePoint(0.25, 0.75).to_pixels(800, 600) == (200.0, 450.0)


def test_relative_point_rejects_coordinates_outside_overlay() -> None:
    with pytest.raises(ValueError, match="between 0 and 1"):
        RelativePoint(1.1, 0.5)
