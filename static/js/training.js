const form = document.querySelector(".training-form");

function number(value) {
  return Number(value || 0);
}

function slug(value) {
  return value.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

if (form && form.dataset.kind === "static") {
  const shots = [];
  const shotInput = document.querySelector("#shotsInput");
  const entriesInput = document.querySelector("#shotEntriesInput");
  const shotTargetEl = document.querySelector("#shotTarget");
  const shotTarget = number(shotTargetEl ? shotTargetEl.textContent : 0);
  const total = document.querySelector("#staticTotal");
  const percent = document.querySelector("#staticPercent");
  const progress = document.querySelector("#shotProgress");
  const phaseLabel = document.querySelector("#phaseLabel");
  const seriesWrap = document.querySelector("#seriesProgressWrap");
  const seriesProgress = document.querySelector("#seriesProgress");
  const list = document.querySelector("#shotList");
  const buttons = document.querySelectorAll("#scoreButtons button");
  const undo = document.querySelector("#undoShot");
  const save = document.querySelector("#saveRun");
  const rangeInput = document.querySelector("#rangeScoreInput");
  const rangeButton = document.querySelector("#addRangeScore");
  const values = (form.dataset.staticValues || "").split(",").map(number).filter((value) => !Number.isNaN(value));
  const flow = JSON.parse(form.dataset.flow || "[]");
  const maxScore = shotTarget * Math.max(...values, 0);

  function phaseForShot(shotNumber) {
    if (!flow.length) {
      return {
        phase_index: null,
        phase_name: `Schuss ${shotNumber}`,
        phase_type: "single",
        series_index: null,
        shot_in_phase: shotNumber,
        shots: shotTarget,
      };
    }
    let cursor = 0;
    for (const phase of flow) {
      if (shotNumber <= cursor + phase.shots) {
        return { ...phase, shot_in_phase: shotNumber - cursor };
      }
      cursor += phase.shots;
    }
    return { phase_name: "Fertig", phase_type: "single", shot_in_phase: 0, shots: 1 };
  }

  function phaseText() {
    const next = Math.min(shots.length + 1, shotTarget);
    const phase = phaseForShot(next);
    if (shots.length >= shotTarget) return "Vollständig";
    if (phase.phase_type === "series") {
      return `Serie ${phase.series_index} von 3 - Schuss ${phase.shot_in_phase} von ${phase.shots}`;
    }
    const singleTotal = flow.filter((item) => item.phase_type === "single").length || shotTarget;
    return `Einzelschuss ${phase.shot_in_phase || next} von ${singleTotal}`;
  }

  function currentSeriesCount() {
    if (!shots.length) return 0;
    const nextPhase = phaseForShot(Math.min(shots.length + 1, shotTarget));
    const seriesIndex = nextPhase.series_index || phaseForShot(shots.length).series_index;
    if (!seriesIndex) return 0;
    return shots.filter((entry) => entry.series_index === seriesIndex).length;
  }

  function addShot(value) {
    if (shots.length >= shotTarget) return;
    const shotNumber = shots.length + 1;
    const phase = phaseForShot(shotNumber);
    shots.push({
      shot_number: shotNumber,
      phase_index: phase.phase_index,
      phase_name: phase.phase_name,
      phase_type: phase.phase_type,
      series_index: phase.series_index,
      shot_in_phase: phase.shot_in_phase,
      value,
    });
    renderShots();
  }

  function renderShots() {
    const score = shots.reduce((sum, entry) => sum + number(entry.value), 0);
    shotInput.value = shots.map((entry) => entry.value).join(",");
    entriesInput.value = JSON.stringify(shots);
    total.textContent = score;
    percent.textContent = maxScore > 0 ? `${((score / maxScore) * 100).toFixed(1)}%` : "0.0%";
    progress.textContent = `${shots.length} / ${shotTarget}`;
    phaseLabel.textContent = phaseText();
    const phase = phaseForShot(Math.min(shots.length + 1, shotTarget));
    seriesWrap.hidden = phase.phase_type !== "series" && !phase.series_index;
    seriesProgress.textContent = `${currentSeriesCount()} / ${phase.shots || 5}`;
    list.innerHTML = shots.map((shot) => `<span title="${shot.phase_name}">${shot.value}</span>`).join("");
    buttons.forEach((button) => {
      button.disabled = shots.length >= shotTarget;
    });
    if (rangeButton) rangeButton.disabled = shots.length >= shotTarget;
    undo.disabled = shots.length === 0;
    save.disabled = shots.length !== shotTarget;
  }

  buttons.forEach((button) => {
    button.addEventListener("click", () => addShot(number(button.dataset.score)));
  });

  if (rangeButton) {
    rangeButton.addEventListener("click", () => {
      const value = number(rangeInput.value);
      const min = number(form.dataset.min);
      const max = number(form.dataset.max);
      if (value >= min && value <= max) addShot(value);
    });
  }

  undo.addEventListener("click", () => {
    shots.pop();
    renderShots();
  });

  form.addEventListener("submit", (event) => {
    if (shots.length !== shotTarget) {
      event.preventDefault();
      alert("Bitte alle Treffer vollständig erfassen.");
    }
  });
  renderShots();
}

if (form && form.dataset.kind === "dynamic") {
  const config = JSON.parse(form.dataset.config || "{}");
  const shotTargetEl = document.querySelector("#shotTarget");
  const shotTarget = number(shotTargetEl ? shotTargetEl.textContent : 0);
  const primary = document.querySelector("#dynamicPrimary");
  const label = document.querySelector("#primaryResultLabel");
  const factor = document.querySelector("#hitFactor");
  const penalty = document.querySelector("#penaltyTime");
  const hfTile = document.querySelector(".hf-tile");
  const timeTile = document.querySelector(".time-tile");
  const rawTimeSummary = document.querySelector("#rawTimeSummary");
  const shotWarning = document.querySelector("#dynamicShotWarning");
  const inputs = form.querySelectorAll("input[type='number']");
  const counterRows = form.querySelectorAll(".counter-row");

  function zoneValue(zone) {
    const element = form.elements[`zone_${slug(zone)}`];
    return number(element ? element.value : 0);
  }

  function clampCounter(input) {
    input.value = Math.max(0, Math.floor(number(input.value)));
  }

  function renderCounterState() {
    counterRows.forEach((row) => {
      const input = row.querySelector(".counter-value");
      const minus = row.querySelector('[data-counter-step="-1"]');
      if (input && minus) minus.disabled = number(input.value) <= 0;
    });
  }

  function countedShots() {
    return Array.from(counterRows).reduce((sum, row) => {
      if (row.dataset.shotCountable !== "1") return sum;
      const input = row.querySelector(".counter-value");
      return sum + number(input ? input.value : 0);
    }, 0);
  }

  function renderShotWarning() {
    if (!shotWarning || !shotTarget) return;
    const count = countedShots();
    if (count === shotTarget) {
      shotWarning.hidden = true;
      shotWarning.textContent = "";
      return;
    }
    shotWarning.hidden = false;
    shotWarning.textContent = `Du hast ${count} von ${shotTarget} Treffern erfasst.`;
  }

  function renderDynamic() {
    const raw = number(form.elements.raw_time ? form.elements.raw_time.value : 0);
    const zones = config.zones || {};
    const mode = config.result || "points";
    const score = Object.entries(zones).reduce((sum, [zone, value]) => sum + zoneValue(zone) * number(value), 0);
    if (rawTimeSummary) rawTimeSummary.textContent = `${raw.toFixed(2)} s`;
    hfTile.hidden = mode !== "hit_factor";
    timeTile.hidden = mode !== "final_time";
    if (mode === "hit_factor") {
      label.textContent = "Punkte";
      primary.textContent = score.toFixed(0);
      factor.textContent = raw > 0 ? (score / raw).toFixed(2) : "0.00";
    } else if (mode === "final_time") {
      label.textContent = "Final Time";
      primary.textContent = `${(raw + score).toFixed(2)} s`;
      penalty.textContent = `${score.toFixed(2)} s`;
    } else {
      label.textContent = "Punkte";
      primary.textContent = score.toFixed(0);
    }
    renderCounterState();
    renderShotWarning();
  }

  document.querySelectorAll(".counter-btn").forEach((button) => {
    button.addEventListener("click", () => {
      const row = button.closest(".counter-row");
      const input = row ? row.querySelector(".counter-value") : null;
      if (!input) return;
      input.value = Math.max(0, number(input.value) + number(button.dataset.counterStep));
      renderDynamic();
    });
  });

  document.querySelectorAll("[data-time-adjust]").forEach((button) => {
    button.addEventListener("click", () => {
      const raw = form.elements.raw_time;
      if (!raw) return;
      raw.value = Math.max(0, number(raw.value) + number(button.dataset.timeAdjust)).toFixed(2);
      renderDynamic();
    });
  });

  const clearRawTime = document.querySelector("#clearRawTime");
  if (clearRawTime) {
    clearRawTime.addEventListener("click", () => {
      if (form.elements.raw_time) {
        form.elements.raw_time.value = "0";
        renderDynamic();
      }
    });
  }

  inputs.forEach((input) => input.addEventListener("input", renderDynamic));
  form.querySelectorAll(".counter-value").forEach((input) => {
    input.addEventListener("change", () => {
      clampCounter(input);
      renderDynamic();
    });
  });
  renderDynamic();
}
