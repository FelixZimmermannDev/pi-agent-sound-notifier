# Chess Desktop Overlay

Windows desktop presentation for the existing Chess Analysis Coach. It is limited to permitted local/offline boards, local computer opponents, and explicitly agreed assisted training. It has no website-specific adapter, DOM access, browser control, or active-online-game integration.

## Implemented data path

```text
DXCAM frame in RAM
  → stable 8×8 visual occupancy observation
  → unique legal move reconciliation with python-chess
  → monotonic position revision
  → bounded latest-position Stockfish analysis
  → existing recommendation and coaching functions
  → revision-bound arrow, evaluation, and coaching text
```

Capture knows only the configured rectangle. Raw frames stay in reusable memory, are never sent to Stockfish, are not written to files, and are discarded after feature extraction. Overlay graphics are excluded from Windows capture so arrows and cards do not feed back into recognition.

The local web game and desktop overlay are separate position sources and presentations. They share the existing `recommend_moves`, Stockfish adapter, candidate values, and coaching functions directly; the overlay does not use or embed Flask.

## Install

Install the main repository first, then the optional side project into the same virtual environment:

```powershell
cd C:\Users\Felix\Code\Projects\PythonProject\chess-analysis-coach
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m pip install -e ".\side_projects\chess_overlay[dev]"
```

`dxcam`, NumPy, and PySide6 are Python dependencies installed by pip. There is no separate dxcam application to launch and no video recorder.

## Recommended local end-to-end workflow

Terminal 1 — start the existing local website with its own coach display and coach calculations disabled:

```powershell
python -m chess_analysis_coach web `
  --no-coach `
  --player-color white `
  --bot-elo 1500
```

Terminal 2 — start the desktop coach. Orientation means the color shown at the bottom of the board:

```powershell
python -m chess_overlay `
  --orientation white `
  --time-ms 250 `
  --candidates 1
```

Use the same `white`/`black` orientation as the local website's player color. `--engine PATH`, `STOCKFISH_PATH`, PATH discovery, and the winget Stockfish location follow the main application's existing discovery behavior. `--coach-elo 1800` optionally limits coach strength.

## Calibration

1. Keep the local website at the standard chess starting position.
2. Place the overlay over **only the square 8×8 board**. Do not include clocks, evaluation bar, player names, margins, or side panels.
3. Make the frame square and align all four outer edges with the board.
4. Press `F6` to lock it and start capture.
5. Wait for `Grundstellung erkannt und synchronisiert` and a current revision-0 recommendation.
6. Start and play the local game normally. The web board remains clickable because the locked overlay is click-through.

The recognizer samples the alternating board colors and visual piece occupancy. It starts from `chess.STARTING_FEN`; it never invents castling rights, en-passant state, side to move, or move counters from one screenshot. Instead, every stable visual change must match exactly one legal `python-chess` move before the logical board advances.

## Controls

- `F6`: edit frame ↔ lock frame and run capture/recognition.
- `F8`: hide/show only the overlay presentation. Capture, synchronized board state, current revision, and background analysis continue while hidden.
- `F9`: discard visual synchronization and reset the logical source to the standard starting position. First reset the local board to its starting position, then press F9 and hold the board stable.
- `Escape`: exit while edit mode is active.
- Tray menu: fallback for all actions if a global hotkey is occupied.

Status colors distinguish calibration/analysis waiting, synchronized live operation, and errors. Recommendations are cleared immediately while recognition is unstable, the board is lost, or a transition is ambiguous.

## Recognition and resynchronization limits

- The complete board must remain on the Windows primary monitor.
- Calibration currently requires the standard starting position.
- The board must be square, static, and aligned exactly with the frame; perspective camera images are not supported.
- The recognizer tracks occupancy and compact visual square signatures. Exact piece identity remains owned by the legal logical board.
- Promotions are intentionally rejected as ambiguous when multiple promotion choices have the same visible transition. Reset to a known starting position with F9 afterward.
- If one or more moves happen while capture is paused, the next image may not match one legal transition. Return the local board to its starting position and use F9.
- Themes with weak light/dark contrast, animated pieces, heavy square decorations, or nonstandard piece scaling may need threshold calibration. The included local website's colors and SVG piece source are covered by deterministic recognition tests.
- This is not a generic active-website reader and must not be placed over online human games.

## Verification

Overlay suite:

```powershell
cd side_projects\chess_overlay
python -m pytest
```

Main practical suite:

```powershell
cd ..\..
python -m pytest
```

The real smoke path requires Windows desktop composition and locally installed Stockfish. It validates actual DXCAM capture behind an excluded overlay, starting-position calibration, one visual `e2e4` transition, bounded Stockfish analysis for both revisions, F8 state preservation, rendering, and cleanup. Browser placement itself remains a short manual check because the product deliberately contains no browser automation.
