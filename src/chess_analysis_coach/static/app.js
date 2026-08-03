"use strict";

const pieceNames = {
  K: "weißer König", Q: "weiße Dame", R: "weißer Turm",
  B: "weißer Läufer", N: "weißer Springer", P: "weißer Bauer",
  k: "schwarzer König", q: "schwarze Dame", r: "schwarzer Turm",
  b: "schwarzer Läufer", n: "schwarzer Springer", p: "schwarzer Bauer",
};

const boardElement = document.querySelector("#board");
const startButton = document.querySelector("#start-button");
const resetButton = document.querySelector("#reset-button");
const errorMessage = document.querySelector("#error-message");
const recommendationsElement = document.querySelector("#recommendations");
const moveListElement = document.querySelector("#move-list");
const coachArrowElement = document.querySelector("#coach-arrow");
const evaluationBarElement = document.querySelector("#evaluation-bar");
const evaluationWhiteElement = document.querySelector("#evaluation-white");
const evaluationBlackElement = document.querySelector("#evaluation-black");
const evaluationScoreElement = document.querySelector("#evaluation-score");

let gameState = null;
let selectedSquare = null;
let requestInProgress = false;
let stateReceivedAt = performance.now();

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json();
  if (!response.ok) {
    throw new Error(payload.error || "Die lokale Anwendung konnte die Anfrage nicht ausführen.");
  }
  return payload;
}

async function loadState() {
  try {
    applyState(await requestJson("/api/game"));
  } catch (error) {
    showError(error.message);
  }
}

function applyState(nextState) {
  const positionChanged = gameState?.fen !== nextState.fen;
  gameState = nextState;
  stateReceivedAt = performance.now();
  if (positionChanged || !nextState.is_player_turn) {
    selectedSquare = null;
  }
  hideError();
  render();
}

function render() {
  if (!gameState) return;
  renderBoard();
  renderPlayers();
  renderEvaluationBar();
  renderStatus();
  renderRecommendations();
  renderMoves();
  renderClocks();
}

function parseFen(fen) {
  const board = {};
  const rows = fen.split(" ")[0].split("/");
  rows.forEach((row, rowIndex) => {
    let fileIndex = 0;
    for (const token of row) {
      if (/\d/.test(token)) {
        fileIndex += Number(token);
      } else {
        const square = `${String.fromCharCode(97 + fileIndex)}${8 - rowIndex}`;
        board[square] = token;
        fileIndex += 1;
      }
    }
  });
  return board;
}

function renderBoard() {
  const pieces = parseFen(gameState.fen);
  const whiteOrientation = gameState.player_color === "white";
  const files = whiteOrientation
    ? ["a", "b", "c", "d", "e", "f", "g", "h"]
    : ["h", "g", "f", "e", "d", "c", "b", "a"];
  const ranks = whiteOrientation
    ? [8, 7, 6, 5, 4, 3, 2, 1]
    : [1, 2, 3, 4, 5, 6, 7, 8];
  const legalTargets = selectedSquare
    ? gameState.legal_moves.filter(move => move.startsWith(selectedSquare))
    : [];
  const coachMove = gameState.is_player_turn && gameState.recommendation.length > 0
    ? gameState.recommendation[0].uci
    : null;
  const coachSource = coachMove?.slice(0, 2);
  const coachTarget = coachMove?.slice(2, 4);

  boardElement.replaceChildren();
  ranks.forEach((rank, rankIndex) => {
    files.forEach((file, fileIndex) => {
      const squareName = `${file}${rank}`;
      const piece = pieces[squareName];
      const square = document.createElement("button");
      const isDark = ((file.charCodeAt(0) - 97) + rank) % 2 === 1;
      square.type = "button";
      square.className = `square ${isDark ? "dark" : "light"}`;
      square.dataset.square = squareName;
      square.setAttribute("role", "gridcell");
      square.setAttribute(
        "aria-label",
        piece ? `${squareName}, ${pieceNames[piece]}` : `${squareName}, leer`,
      );

      if (squareName === coachSource) square.classList.add("coach-source");
      if (squareName === coachTarget) square.classList.add("coach-target");
      if (selectedSquare === squareName) square.classList.add("selected");
      if (legalTargets.some(move => move.slice(2, 4) === squareName)) {
        square.classList.add("legal-target");
        if (piece) square.classList.add("occupied");
      }

      if (piece) {
        const pieceElement = document.createElement("img");
        pieceElement.className = "piece";
        pieceElement.src = `/pieces/${piece}.svg`;
        pieceElement.alt = "";
        pieceElement.draggable = false;
        square.append(pieceElement);
      }
      if (fileIndex === 0) square.append(coordinateLabel("rank", String(rank)));
      if (rankIndex === 7) square.append(coordinateLabel("file", file));
      square.addEventListener("click", () => selectSquare(squareName, pieces));
      boardElement.append(square);
    });
  });
  renderCoachArrow(coachMove, whiteOrientation);
}

function renderCoachArrow(move, whiteOrientation) {
  if (!move) {
    coachArrowElement.classList.remove("visible");
    return;
  }

  const start = squareCenter(move.slice(0, 2), whiteOrientation);
  const target = squareCenter(move.slice(2, 4), whiteOrientation);
  const deltaX = target.x - start.x;
  const deltaY = target.y - start.y;
  const distance = Math.hypot(deltaX, deltaY);
  const shortenBy = Math.min(28, distance * 0.2);
  const endX = target.x - (deltaX / distance) * shortenBy;
  const endY = target.y - (deltaY / distance) * shortenBy;

  coachArrowElement.setAttribute("x1", start.x);
  coachArrowElement.setAttribute("y1", start.y);
  coachArrowElement.setAttribute("x2", endX);
  coachArrowElement.setAttribute("y2", endY);
  coachArrowElement.classList.add("visible");
}

function squareCenter(square, whiteOrientation) {
  const file = square.charCodeAt(0) - 97;
  const rank = Number(square[1]);
  return {
    x: (whiteOrientation ? file : 7 - file) * 100 + 50,
    y: (whiteOrientation ? 8 - rank : rank - 1) * 100 + 50,
  };
}

function coordinateLabel(kind, text) {
  const label = document.createElement("span");
  label.className = `coordinate ${kind}`;
  label.textContent = text;
  return label;
}

function selectSquare(square, pieces) {
  if (!gameState.started || gameState.game_over || !gameState.is_player_turn || requestInProgress) {
    return;
  }

  const piece = pieces[square];
  const pieceIsPlayer = piece && (
    (gameState.player_color === "white" && piece === piece.toUpperCase()) ||
    (gameState.player_color === "black" && piece === piece.toLowerCase())
  );

  if (!selectedSquare) {
    if (pieceIsPlayer) {
      selectedSquare = square;
      renderBoard();
    }
    return;
  }

  if (pieceIsPlayer) {
    selectedSquare = square;
    renderBoard();
    return;
  }

  const matchingMoves = gameState.legal_moves.filter(
    move => move.startsWith(selectedSquare + square),
  );
  if (matchingMoves.length === 0) {
    selectedSquare = null;
    renderBoard();
    return;
  }

  let move = matchingMoves[0];
  if (matchingMoves.length > 1) {
    const promotion = (window.prompt("Umwandlung: q, r, b oder n", "q") || "q").toLowerCase();
    move = matchingMoves.find(candidate => candidate.endsWith(promotion)) || matchingMoves[0];
  }
  playMove(move);
}

async function playMove(move) {
  requestInProgress = true;
  selectedSquare = null;
  document.querySelector("#game-status").textContent = "Stockfish denkt …";
  document.querySelector("#status-detail").textContent = "Dein Zug wird geprüft und der lokale Gegner antwortet.";
  renderBoard();
  try {
    const state = await requestJson("/api/game/move", {
      method: "POST",
      body: JSON.stringify({ move }),
    });
    applyState(state);
  } catch (error) {
    showError(error.message);
    await loadState();
  } finally {
    requestInProgress = false;
    renderStatus();
  }
}

function renderPlayers() {
  const playerIsWhite = gameState.player_color === "white";
  document.querySelector("#bottom-player-name").textContent = "Du";
  document.querySelector("#bottom-player-detail").textContent = playerIsWhite ? "Weiß" : "Schwarz";
  document.querySelector("#top-player-name").textContent = "Stockfish";
  document.querySelector("#top-player-detail").textContent = playerIsWhite ? "Schwarz · lokaler Gegner" : "Weiß · lokaler Gegner";
}

function renderEvaluationBar() {
  const summary = gameState.evaluation_bar;
  const whiteAtTop = gameState.player_color === "black";
  const whitePercent = summary?.white_percent ?? 50;
  const blackPercent = summary?.black_percent ?? 50;
  const splitFromTop = whiteAtTop ? whitePercent : blackPercent;
  const topLabel = document.querySelector("#evaluation-top-label");
  const bottomLabel = document.querySelector("#evaluation-bottom-label");

  evaluationBarElement.classList.toggle("white-at-top", whiteAtTop);
  evaluationWhiteElement.style.height = `${whitePercent}%`;
  evaluationBlackElement.style.height = `${blackPercent}%`;
  evaluationScoreElement.style.top = `${Math.min(96, Math.max(4, splitFromTop))}%`;
  evaluationScoreElement.textContent = summary?.display ?? "–";
  topLabel.textContent = whiteAtTop ? "W" : "S";
  bottomLabel.textContent = whiteAtTop ? "S" : "W";
  topLabel.style.color = whiteAtTop ? "#282923" : "#f1f1e9";
  bottomLabel.style.color = whiteAtTop ? "#f1f1e9" : "#282923";

  const description = summary
    ? `Live-Bewertung ${summary.display}; Weiß ${whitePercent.toFixed(0)} Prozent, Schwarz ${blackPercent.toFixed(0)} Prozent.`
    : "Noch keine Live-Bewertung";
  evaluationBarElement.setAttribute("aria-label", description);
}

function renderStatus() {
  if (!gameState) return;
  const status = document.querySelector("#game-status");
  const detail = document.querySelector("#status-detail");
  startButton.disabled = gameState.started || requestInProgress;

  if (!gameState.started) {
    status.textContent = "Bereit für eine lokale Partie";
    detail.textContent = "Die Uhren beginnen erst nach Klick auf „Partie starten“.";
  } else if (gameState.game_over) {
    status.textContent = `Partie beendet · ${gameState.result || "*"}`;
    detail.textContent = gameState.termination === "time forfeit"
      ? "Die Partie wurde durch Zeitüberschreitung entschieden."
      : `Grund: ${gameState.termination || "Partieende"}`;
  } else if (gameState.is_player_turn) {
    status.textContent = "Du bist am Zug";
    detail.textContent = "Wähle eine eigene Figur und danach das Zielfeld.";
  } else {
    status.textContent = "Stockfish ist am Zug";
    detail.textContent = "Der lokale Gegner berechnet seinen Zug.";
  }
}

function renderRecommendations() {
  recommendationsElement.replaceChildren();
  const coachState = document.querySelector("#coach-state");
  if (!gameState.started) {
    coachState.textContent = "Wartet";
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Nach dem Start erscheinen hier Kandidaten und taktische Hinweise."));
    return;
  }
  if (gameState.game_over) {
    coachState.textContent = "Beendet";
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Die Live-Analyse ist beendet. Die PGN-Aufzeichnung steht zum Download bereit."));
    return;
  }
  if (!gameState.is_player_turn || gameState.recommendation.length === 0) {
    coachState.textContent = "Analysiert";
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Empfehlungen werden nur für deinen Zug angezeigt."));
    return;
  }

  coachState.textContent = "Bereit";
  coachState.className = "state-pill ready";
  gameState.recommendation.forEach(candidate => {
    const card = document.createElement("article");
    card.className = "recommendation-card";

    const topLine = document.createElement("div");
    topLine.className = "recommendation-topline";
    const moveName = document.createElement("span");
    moveName.className = "move-name";
    moveName.textContent = `${candidate.rank}. ${candidate.san}`;
    const evaluation = document.createElement("span");
    evaluation.className = "evaluation";
    evaluation.textContent = candidate.evaluation;
    topLine.append(moveName, evaluation);

    const explanation = document.createElement("p");
    explanation.className = "explanation";
    explanation.textContent = candidate.explanation;
    const variation = document.createElement("p");
    variation.className = "variation";
    variation.textContent = `Variante: ${candidate.variation.join(" ")}`;
    card.append(topLine, explanation, variation);
    recommendationsElement.append(card);
  });
}

function emptyMessage(text) {
  const element = document.createElement("p");
  element.className = "empty-state";
  element.textContent = text;
  return element;
}

function renderMoves() {
  moveListElement.replaceChildren();
  document.querySelector("#recording-name").textContent = gameState.recording_filename;
  if (gameState.moves.length === 0) {
    const row = document.createElement("tr");
    const cell = document.createElement("td");
    cell.colSpan = 3;
    cell.className = "empty-cell";
    cell.textContent = "Noch keine Züge";
    row.append(cell);
    moveListElement.append(row);
    return;
  }
  gameState.moves.forEach(move => {
    const row = document.createElement("tr");
    [move.number, move.white || "", move.black || ""].forEach(value => {
      const cell = document.createElement("td");
      cell.textContent = value;
      row.append(cell);
    });
    moveListElement.append(row);
  });
  const scrollContainer = document.querySelector(".move-table-wrap");
  scrollContainer.scrollTop = scrollContainer.scrollHeight;
}

function renderClocks() {
  if (!gameState) return;
  const elapsed = (performance.now() - stateReceivedAt) / 1000;
  const clocks = {
    white: gameState.clocks.white_seconds,
    black: gameState.clocks.black_seconds,
  };
  if (gameState.started && !gameState.game_over && gameState.clocks.active_color) {
    clocks[gameState.clocks.active_color] = Math.max(
      0,
      clocks[gameState.clocks.active_color] - elapsed,
    );
  }

  const bottomColor = gameState.player_color;
  const topColor = bottomColor === "white" ? "black" : "white";
  updateClock(document.querySelector("#bottom-clock"), clocks[bottomColor], bottomColor);
  updateClock(document.querySelector("#top-clock"), clocks[topColor], topColor);
}

function updateClock(element, seconds, color) {
  element.textContent = formatClock(seconds);
  element.classList.toggle(
    "active",
    gameState.started && !gameState.game_over && gameState.clocks.active_color === color,
  );
  element.classList.toggle("low-time", seconds <= 30);
}

function formatClock(seconds) {
  const safeSeconds = Math.max(0, seconds);
  if (safeSeconds < 10) {
    return `0:${safeSeconds.toFixed(1).padStart(4, "0")}`;
  }
  const wholeSeconds = Math.ceil(safeSeconds);
  const minutes = Math.floor(wholeSeconds / 60);
  const remainder = wholeSeconds % 60;
  return `${minutes}:${String(remainder).padStart(2, "0")}`;
}

function showError(message) {
  errorMessage.textContent = message;
  errorMessage.hidden = false;
}

function hideError() {
  errorMessage.hidden = true;
  errorMessage.textContent = "";
}

startButton.addEventListener("click", async () => {
  requestInProgress = true;
  startButton.disabled = true;
  try {
    applyState(await requestJson("/api/game/start", { method: "POST", body: "{}" }));
  } catch (error) {
    showError(error.message);
  } finally {
    requestInProgress = false;
    renderStatus();
  }
});

resetButton.addEventListener("click", async () => {
  if (gameState?.started && !window.confirm("Aktuelle Partie beenden und ein neues Brett öffnen?")) {
    return;
  }
  requestInProgress = true;
  try {
    applyState(await requestJson("/api/game/reset", { method: "POST", body: "{}" }));
  } catch (error) {
    showError(error.message);
  } finally {
    requestInProgress = false;
    renderStatus();
  }
});

setInterval(renderClocks, 100);
setInterval(() => {
  if (gameState?.started && !gameState.game_over && !requestInProgress) loadState();
}, 1500);

loadState();
