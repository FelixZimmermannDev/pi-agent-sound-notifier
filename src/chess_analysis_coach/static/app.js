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
const candidateArrowsElement = document.querySelector("#candidate-arrows");
const evaluationBarElement = document.querySelector("#evaluation-bar");
const evaluationWhiteElement = document.querySelector("#evaluation-white");
const evaluationBlackElement = document.querySelector("#evaluation-black");
const evaluationScoreElement = document.querySelector("#evaluation-score");
const candidateCountButtons = Array.from(
  document.querySelectorAll("[data-candidate-count]"),
);
const forecastModeButtons = Array.from(
  document.querySelectorAll("[data-forecast-mode]"),
);
const botEloSlider = document.querySelector("#bot-elo-slider");
const botEloValue = document.querySelector("#bot-elo-value");
const coachMaxStrength = document.querySelector("#coach-max-strength");
const coachEloSlider = document.querySelector("#coach-elo-slider");
const coachEloValue = document.querySelector("#coach-elo-value");
const engineBudgetNote = document.querySelector("#engine-budget-note");

let gameState = null;
let selectedSquare = null;
let selectedCandidateUci = null;
let selectedRecommendationCount = 1;
let selectedBotElo = 1500;
let selectedCoachElo = null;
let limitedCoachElo = 1800;
let opponentForecastMode = "relevant";
let ownForecastMode = "relevant";
let queuedPremoveUci = null;
let dragSourceSquare = null;
let requestInProgress = false;
let botMoveInProgress = false;
let stateReceivedAt = performance.now();
let displayedEvaluationWhitePercent = null;

const evaluationBarDeadband = 2.0;

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
  const availableCandidates = nextState.recommendation.map(candidate => candidate.uci);
  gameState = nextState;
  selectedRecommendationCount = nextState.candidate_count;
  selectedBotElo = nextState.bot_elo;
  selectedCoachElo = nextState.coach_elo;
  if (nextState.coach_elo != null) limitedCoachElo = nextState.coach_elo;
  stateReceivedAt = performance.now();
  if (positionChanged || !nextState.is_player_turn) {
    selectedSquare = null;
  }
  if (positionChanged || !availableCandidates.includes(selectedCandidateUci)) {
    selectedCandidateUci = availableCandidates[0] ?? null;
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
  renderRecommendationSettings();
  renderForecastControls();
  renderMoveQuality();
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
  const availableMoves = currentMoveOptions();
  const legalTargets = selectedSquare
    ? availableMoves.filter(move => move.startsWith(selectedSquare))
    : [];
  const premoveSource = queuedPremoveUci?.slice(0, 2);
  const premoveTarget = queuedPremoveUci?.slice(2, 4);
  const candidates = gameState.is_player_turn ? gameState.recommendation : [];
  const selectedCandidate = candidates.find(
    candidate => candidate.uci === selectedCandidateUci,
  ) ?? candidates[0];
  const coachSource = selectedCandidate?.uci.slice(0, 2);
  const coachTarget = selectedCandidate?.uci.slice(2, 4);

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
      if (squareName === premoveSource) square.classList.add("premove-source");
      if (squareName === premoveTarget) square.classList.add("premove-target");
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
      square.draggable = Boolean(piece && isPlayerPiece(piece) && canUseBoard());
      square.addEventListener("click", () => selectSquare(squareName, pieces));
      square.addEventListener("dragstart", event => startDrag(event, squareName, piece));
      square.addEventListener("dragover", event => {
        if (dragSourceSquare) event.preventDefault();
      });
      square.addEventListener("drop", event => dropPiece(event, squareName, pieces));
      square.addEventListener("dragend", endDrag);
      boardElement.append(square);
    });
  });
  renderCandidateArrows(candidates, whiteOrientation);
}

function renderCandidateArrows(candidates, whiteOrientation) {
  candidateArrowsElement.replaceChildren();
  const selectedCandidate = candidates.find(
    candidate => candidate.uci === selectedCandidateUci,
  );
  if (selectedCandidate) {
    renderFutureArrows(selectedCandidate, whiteOrientation);
  }
  candidates.forEach(candidate => {
    const rankStyle = Math.min(candidate.rank, 3);
    const endpoints = arrowEndpoints(candidate.uci, whiteOrientation);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.classList.add("candidate-arrow", `rank-${rankStyle}`);
    if (candidate.uci === selectedCandidateUci) line.classList.add("selected");
    line.setAttribute("x1", endpoints.start.x);
    line.setAttribute("y1", endpoints.start.y);
    line.setAttribute("x2", endpoints.end.x);
    line.setAttribute("y2", endpoints.end.y);
    line.setAttribute("marker-end", `url(#candidate-arrowhead-${rankStyle})`);
    candidateArrowsElement.append(line);
  });
}

function renderFutureArrows(candidate, whiteOrientation) {
  if (!candidate.variation_uci || candidate.variation_uci[0] !== candidate.uci) return;
  const rankStyle = Math.min(candidate.rank, 3);
  candidate.variation_uci.slice(1, 3).forEach((move, index) => {
    const plyNumber = index + 2;
    const isOpponentReply = plyNumber % 2 === 0;
    const shouldShow = isOpponentReply
      ? shouldShowForecast(opponentForecastMode, candidate.forecast.opponent_relevant)
      : shouldShowForecast(ownForecastMode, candidate.forecast.own_follow_up_relevant);
    if (!shouldShow) return;

    const endpoints = arrowEndpoints(move, whiteOrientation);
    const line = document.createElementNS("http://www.w3.org/2000/svg", "line");
    line.classList.add(
      "future-arrow",
      isOpponentReply ? "response" : "own",
      `rank-${rankStyle}`,
    );
    line.setAttribute("x1", endpoints.start.x);
    line.setAttribute("y1", endpoints.start.y);
    line.setAttribute("x2", endpoints.end.x);
    line.setAttribute("y2", endpoints.end.y);
    line.setAttribute(
      "marker-end",
      isOpponentReply
        ? "url(#future-arrowhead-response)"
        : `url(#candidate-arrowhead-${rankStyle})`,
    );
    candidateArrowsElement.append(line);

    const target = squareCenter(move.slice(2, 4), whiteOrientation);
    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
    circle.classList.add("variation-step-circle");
    circle.setAttribute("cx", target.x);
    circle.setAttribute("cy", target.y);
    circle.setAttribute("r", 18);
    const number = document.createElementNS("http://www.w3.org/2000/svg", "text");
    number.classList.add("variation-step-number");
    number.setAttribute("x", target.x);
    number.setAttribute("y", target.y + 1);
    number.textContent = plyNumber;
    candidateArrowsElement.append(circle, number);
  });
}

function shouldShowForecast(mode, isRelevant) {
  return mode === "all" || (mode === "relevant" && isRelevant);
}

function arrowEndpoints(move, whiteOrientation) {
  const start = squareCenter(move.slice(0, 2), whiteOrientation);
  const target = squareCenter(move.slice(2, 4), whiteOrientation);
  const deltaX = target.x - start.x;
  const deltaY = target.y - start.y;
  const distance = Math.hypot(deltaX, deltaY);
  const shortenBy = Math.min(28, distance * 0.2);
  return {
    start,
    end: {
      x: target.x - (deltaX / distance) * shortenBy,
      y: target.y - (deltaY / distance) * shortenBy,
    },
  };
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

function canUseBoard() {
  return Boolean(
    gameState?.started &&
    !gameState.game_over &&
    (gameState.is_player_turn || botMoveInProgress),
  );
}

function currentMoveOptions() {
  if (!gameState) return [];
  return gameState.is_player_turn ? gameState.legal_moves : gameState.premove_moves;
}

function isPlayerPiece(piece) {
  return Boolean(piece) && (
    (gameState.player_color === "white" && piece === piece.toUpperCase()) ||
    (gameState.player_color === "black" && piece === piece.toLowerCase())
  );
}

function selectSquare(square, pieces) {
  if (!canUseBoard() || (requestInProgress && !botMoveInProgress)) return;

  const piece = pieces[square];
  const pieceIsPlayer = isPlayerPiece(piece);

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

  const matchingMoves = currentMoveOptions().filter(
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
  if (botMoveInProgress && !gameState.is_player_turn) {
    queuedPremoveUci = move;
    selectedSquare = null;
    renderBoard();
    renderStatus();
    return;
  }
  playMove(move);
}

function startDrag(event, square, piece) {
  if (!canUseBoard() || !isPlayerPiece(piece)) {
    event.preventDefault();
    return;
  }
  dragSourceSquare = square;
  selectedSquare = square;
  event.currentTarget.classList.add("dragging");
  event.dataTransfer.effectAllowed = "move";
  event.dataTransfer.setData("text/plain", square);
}

function dropPiece(event, targetSquare, pieces) {
  event.preventDefault();
  if (!dragSourceSquare) return;
  selectedSquare = dragSourceSquare;
  dragSourceSquare = null;
  selectSquare(targetSquare, pieces);
}

function endDrag() {
  dragSourceSquare = null;
  document.querySelectorAll(".square.dragging").forEach(square => {
    square.classList.remove("dragging");
  });
}

async function playMove(move) {
  requestInProgress = true;
  selectedSquare = null;
  queuedPremoveUci = null;
  document.querySelector("#game-status").textContent = "Zug wird bewertet …";
  document.querySelector("#status-detail").textContent = "Die schnelle Live-Qualität wird berechnet.";
  renderBoard();
  let requestBotAfterMove = false;
  try {
    const state = await requestJson("/api/game/move", {
      method: "POST",
      body: JSON.stringify({ move }),
    });
    applyState(state);
    requestBotAfterMove = state.started && !state.game_over && !state.is_player_turn;
  } catch (error) {
    showError(error.message);
    await loadState();
  } finally {
    requestInProgress = false;
    renderStatus();
  }
  if (requestBotAfterMove) requestBotMove();
}

async function requestBotMove() {
  botMoveInProgress = true;
  requestInProgress = true;
  selectedSquare = null;
  renderBoard();
  renderStatus();
  let completedState = null;
  let premove = null;
  try {
    completedState = await requestJson("/api/game/bot-move", {
      method: "POST",
      body: "{}",
    });
    premove = queuedPremoveUci;
    queuedPremoveUci = null;
  } catch (error) {
    queuedPremoveUci = null;
    showError(error.message);
    await loadState();
  } finally {
    botMoveInProgress = false;
    requestInProgress = false;
  }

  if (!completedState) {
    renderStatus();
    renderBoard();
    return;
  }

  applyState(completedState);
  if (premove && completedState.legal_moves.includes(premove)) {
    await playMove(premove);
    return;
  }
  if (premove) {
    showError(`Premove ${premove} wurde verworfen, weil er nach dem Bot-Zug nicht legal ist.`);
  }
  renderStatus();
  renderBoard();
}

function renderPlayers() {
  const playerIsWhite = gameState.player_color === "white";
  document.querySelector("#bottom-player-name").textContent = "Du";
  document.querySelector("#bottom-player-detail").textContent = playerIsWhite ? "Weiß" : "Schwarz";
  document.querySelector("#top-player-name").textContent = "Stockfish";
  const opponentColor = playerIsWhite ? "Schwarz" : "Weiß";
  document.querySelector("#top-player-detail").textContent = `${opponentColor} · UCI-Ziel ${gameState.bot_elo}`;
}

function renderEvaluationBar() {
  const summary = gameState.evaluation_bar;
  const whiteAtTop = gameState.player_color === "black";
  const targetWhitePercent = summary?.white_percent ?? 50;
  const forceTarget = gameState.game_over || summary?.display.includes("#");
  if (
    displayedEvaluationWhitePercent == null
    || summary == null
    || forceTarget
    || Math.abs(targetWhitePercent - displayedEvaluationWhitePercent) >= evaluationBarDeadband
  ) {
    displayedEvaluationWhitePercent = targetWhitePercent;
  }
  const whitePercent = displayedEvaluationWhitePercent;
  const blackPercent = 100 - whitePercent;
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
    ? `Live-Bewertung ${summary.display}; geglättete Anzeige Weiß ${whitePercent.toFixed(0)} Prozent, Schwarz ${blackPercent.toFixed(0)} Prozent.`
    : "Noch keine Live-Bewertung";
  evaluationBarElement.setAttribute("aria-label", description);
}

function renderRecommendationSettings() {
  candidateCountButtons.forEach(button => {
    const count = Number(button.dataset.candidateCount);
    const isSelected = count === selectedRecommendationCount;
    button.classList.toggle("selected", isSelected);
    button.setAttribute("aria-pressed", isSelected ? "true" : "false");
    button.disabled = gameState.started || requestInProgress;
  });
  botEloSlider.value = selectedBotElo;
  botEloValue.textContent = `UCI-Ziel ${selectedBotElo}`;
  botEloSlider.disabled = gameState.started || requestInProgress;

  const coachUsesMaximum = selectedCoachElo == null;
  coachMaxStrength.checked = coachUsesMaximum;
  coachMaxStrength.disabled = gameState.started || requestInProgress;
  coachEloSlider.value = limitedCoachElo;
  coachEloSlider.disabled = (
    gameState.started || requestInProgress || coachUsesMaximum
  );
  coachEloValue.textContent = coachUsesMaximum
    ? "Maximal"
    : `UCI-Ziel ${selectedCoachElo}`;

  const equalBudgets = gameState.coach_time_ms === gameState.bot_time_ms;
  engineBudgetNote.textContent = equalBudgets
    ? `Gleiches Budget für die Hauptzugauswahl: Coach und Gegner jeweils ${gameState.coach_time_ms} ms. Weitere Kandidaten, Erklärungen und die objektive Balkenbewertung rechnen zusätzlich, ändern den gewählten Hauptzug aber nicht.`
    : `Unterschiedliche Budgets für die Hauptzugauswahl: Coach ${gameState.coach_time_ms} ms, Gegner ${gameState.bot_time_ms} ms. Für direkte Vergleiche beim Start dieselben CLI-Zeiten verwenden.`;
}

function renderForecastControls() {
  forecastModeButtons.forEach(button => {
    const selectedMode = button.dataset.forecastSide === "opponent"
      ? opponentForecastMode
      : ownForecastMode;
    const isSelected = button.dataset.forecastMode === selectedMode;
    button.classList.toggle("selected", isSelected);
    button.setAttribute("aria-pressed", isSelected ? "true" : "false");
  });
}

function renderMoveQuality() {
  const running = gameState.running_accuracy;
  document.querySelector("#white-accuracy").textContent = formatAccuracy(
    running.white_percent,
  );
  document.querySelector("#black-accuracy").textContent = formatAccuracy(
    running.black_percent,
  );

  const container = document.querySelector("#latest-quality");
  const quality = gameState.latest_move_quality;
  container.className = "latest-quality";
  container.replaceChildren();
  if (!quality) {
    container.textContent = "Nach deinem ersten Zug erscheint hier die schnelle Bewertung.";
    return;
  }

  container.classList.add(quality.category);
  const title = document.createElement("strong");
  title.textContent = `${quality.san}: ${quality.label}`;
  const detail = document.createElement("span");
  const loss = quality.loss_percentage_points.toFixed(1);
  detail.textContent = quality.category === "best"
    ? "Du hast den ersten Stockfish-Kandidaten gespielt."
    : `Verlust im Bewertungsanteil: ${loss} Punkte. Besser war ${quality.best_move_san}.`;
  container.append(title, detail);
}

function formatAccuracy(value) {
  return value == null ? "–" : `${value.toFixed(1)}%`;
}

function renderStatus() {
  if (!gameState) return;
  const status = document.querySelector("#game-status");
  const detail = document.querySelector("#status-detail");
  startButton.disabled = gameState.started || requestInProgress;
  resetButton.disabled = requestInProgress;

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
    detail.textContent = queuedPremoveUci
      ? `Premove ${queuedPremoveUci} ist vorgemerkt und wird anschließend geprüft.`
      : "Du kannst während der Berechnung einen Zug klicken oder ziehen, um ihn vorzumerken.";
  }
}

function renderRecommendations() {
  recommendationsElement.replaceChildren();
  const coachState = document.querySelector("#coach-state");
  const strengthLabel = selectedCoachElo == null ? "Max" : `UCI ${selectedCoachElo}`;
  if (!gameState.started) {
    coachState.textContent = `${strengthLabel} · Wartet`;
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Nach dem Start erscheinen hier Kandidaten und taktische Hinweise."));
    return;
  }
  if (gameState.game_over) {
    coachState.textContent = `${strengthLabel} · Beendet`;
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Die Live-Analyse ist beendet. Die PGN-Aufzeichnung steht zum Download bereit."));
    return;
  }
  if (!gameState.is_player_turn || gameState.recommendation.length === 0) {
    coachState.textContent = `${strengthLabel} · Analysiert`;
    coachState.className = "state-pill";
    recommendationsElement.append(emptyMessage("Empfehlungen werden nur für deinen Zug angezeigt."));
    return;
  }

  coachState.textContent = `${strengthLabel} · Bereit`;
  coachState.className = "state-pill ready";
  gameState.recommendation.forEach(candidate => {
    const rankStyle = Math.min(candidate.rank, 3);
    const card = document.createElement("button");
    card.type = "button";
    card.className = `recommendation-card rank-${rankStyle}`;
    card.classList.toggle("selected", candidate.uci === selectedCandidateUci);
    card.setAttribute(
      "aria-pressed",
      candidate.uci === selectedCandidateUci ? "true" : "false",
    );
    card.addEventListener("click", () => {
      selectedCandidateUci = candidate.uci;
      selectedSquare = null;
      renderBoard();
      renderRecommendations();
    });

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
    const context = document.createElement("span");
    context.className = "forecast-context";
    context.textContent = candidate.forecast.context_label;
    const plan = document.createElement("p");
    plan.className = "plan";
    plan.textContent = `Ziel: ${candidate.forecast.goal}.`;

    const showOpponent = Boolean(candidate.forecast.opponent_reply_san) &&
      shouldShowForecast(
        opponentForecastMode,
        candidate.forecast.opponent_relevant,
      );
    const showOwn = Boolean(candidate.forecast.own_follow_up_san) &&
      shouldShowForecast(
        ownForecastMode,
        candidate.forecast.own_follow_up_relevant,
      );
    const forecastDetails = [];
    if (showOpponent) {
      const counter = document.createElement("p");
      counter.className = "forecast-detail counter";
      counter.textContent = `Gegner-Counter: ${candidate.forecast.opponent_counter}.`;
      forecastDetails.push(counter);
    }
    if (showOwn) {
      const own = document.createElement("p");
      own.className = "forecast-detail own";
      own.textContent = `Eigene Fortsetzung: ${candidate.forecast.own_follow_up_goal}.`;
      forecastDetails.push(own);
    }

    const variationMoves = [candidate.variation[0] || candidate.san];
    if (showOpponent && candidate.variation[1]) variationMoves.push(candidate.variation[1]);
    if (showOwn && candidate.variation[2]) {
      if (!showOpponent) variationMoves.push("…");
      variationMoves.push(candidate.variation[2]);
    }
    const variation = document.createElement("p");
    variation.className = "variation";
    variation.textContent = `Sichtbare Variante: ${variationMoves.join(" ")}`;
    card.append(topLine, explanation, context, plan, ...forecastDetails, variation);
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
    const numberCell = document.createElement("td");
    numberCell.textContent = move.number;
    row.append(
      numberCell,
      moveTableCell(move.white, move.white_quality),
      moveTableCell(move.black, move.black_quality),
    );
    moveListElement.append(row);
  });
  const scrollContainer = document.querySelector(".move-table-wrap");
  scrollContainer.scrollTop = scrollContainer.scrollHeight;
}

function moveTableCell(move, quality) {
  const cell = document.createElement("td");
  cell.textContent = move || "";
  if (quality) {
    const qualityTag = document.createElement("span");
    qualityTag.className = "move-quality-tag";
    qualityTag.textContent = quality;
    cell.append(qualityTag);
  }
  return cell;
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

botEloSlider.addEventListener("input", () => {
  if (gameState?.started || requestInProgress) return;
  selectedBotElo = Number(botEloSlider.value);
  botEloValue.textContent = `UCI-Ziel ${selectedBotElo}`;
});

coachMaxStrength.addEventListener("change", () => {
  if (gameState?.started || requestInProgress) return;
  selectedCoachElo = coachMaxStrength.checked ? null : limitedCoachElo;
  renderRecommendationSettings();
});

coachEloSlider.addEventListener("input", () => {
  if (gameState?.started || requestInProgress || coachMaxStrength.checked) return;
  limitedCoachElo = Number(coachEloSlider.value);
  selectedCoachElo = limitedCoachElo;
  coachEloValue.textContent = `UCI-Ziel ${selectedCoachElo}`;
});

forecastModeButtons.forEach(button => {
  button.addEventListener("click", () => {
    if (button.dataset.forecastSide === "opponent") {
      opponentForecastMode = button.dataset.forecastMode;
    } else {
      ownForecastMode = button.dataset.forecastMode;
    }
    renderForecastControls();
    renderBoard();
    renderRecommendations();
  });
});

candidateCountButtons.forEach(button => {
  button.addEventListener("click", () => {
    if (gameState?.started || requestInProgress) return;
    selectedRecommendationCount = Number(button.dataset.candidateCount);
    renderRecommendationSettings();
  });
});

startButton.addEventListener("click", async () => {
  requestInProgress = true;
  startButton.disabled = true;
  let requestOpeningBotMove = false;
  try {
    const state = await requestJson("/api/game/start", {
      method: "POST",
      body: JSON.stringify({
        candidate_count: selectedRecommendationCount,
        bot_elo: selectedBotElo,
        coach_elo: selectedCoachElo,
      }),
    });
    applyState(state);
    requestOpeningBotMove = state.started && !state.game_over && !state.is_player_turn;
  } catch (error) {
    showError(error.message);
  } finally {
    requestInProgress = false;
    renderStatus();
    renderRecommendationSettings();
  }
  if (requestOpeningBotMove) requestBotMove();
});

resetButton.addEventListener("click", async () => {
  if (gameState?.started && !window.confirm("Aktuelle Partie beenden und ein neues Brett öffnen?")) {
    return;
  }
  requestInProgress = true;
  queuedPremoveUci = null;
  selectedSquare = null;
  try {
    applyState(await requestJson("/api/game/reset", { method: "POST", body: "{}" }));
  } catch (error) {
    showError(error.message);
  } finally {
    requestInProgress = false;
    renderStatus();
    renderRecommendationSettings();
  }
});

document.addEventListener("keydown", event => {
  if (event.key === "Escape" && queuedPremoveUci) {
    queuedPremoveUci = null;
    selectedSquare = null;
    renderBoard();
    renderStatus();
  }
});

setInterval(renderClocks, 100);
setInterval(() => {
  if (gameState?.started && !gameState.game_over && !requestInProgress) loadState();
}, 1500);

loadState();
