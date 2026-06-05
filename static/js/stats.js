function formatValue(value, unit) {
  if (unit === "s") return `${value.toFixed(2)} s`;
  if (unit === "%") return `${value.toFixed(1)}%`;
  return value.toFixed(value >= 10 ? 1 : 2);
}

function themeColor(name) {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

function drawMetricChart(canvas) {
  const data = JSON.parse(canvas.dataset.chart || "{}");
  const ctx = canvas.getContext("2d");
  const width = canvas.width;
  const height = canvas.height;
  const pad = { top: 38, right: 20, bottom: 48, left: 58 };
  const values = (data.values || []).map(Number);
  const labels = data.labels || [];
  const unit = data.unit || "";
  const colors = {
    surface: themeColor("--surface"),
    text: themeColor("--text"),
    muted: themeColor("--muted"),
    border: themeColor("--border"),
    primary: themeColor("--primary"),
  };

  ctx.clearRect(0, 0, width, height);
  ctx.fillStyle = colors.surface;
  ctx.fillRect(0, 0, width, height);
  ctx.fillStyle = colors.text;
  ctx.font = "17px system-ui";
  ctx.fillText((data.title || "Analyse").slice(0, 48), pad.left, 24);

  if (!values.length) {
    ctx.fillStyle = colors.muted;
    ctx.font = "18px system-ui";
    ctx.fillText("Noch keine Runs", pad.left, height / 2);
    return;
  }

  const rawMin = Math.min(...values);
  const rawMax = Math.max(...values);
  const span = rawMax - rawMin;
  const margin = span === 0 ? Math.max(rawMax * 0.1, 1) : span * 0.15;
  const min = rawMin - margin;
  const max = rawMax + margin;
  const range = max - min || 1;
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  ctx.strokeStyle = colors.border;
  ctx.fillStyle = colors.muted;
  ctx.lineWidth = 1;
  ctx.font = "12px system-ui";
  for (let i = 0; i < 4; i += 1) {
    const value = min + (range / 3) * i;
    const y = height - pad.bottom - ((value - min) / range) * plotH;
    ctx.beginPath();
    ctx.moveTo(pad.left, y);
    ctx.lineTo(width - pad.right, y);
    ctx.stroke();
    ctx.fillText(formatValue(value, unit), 8, y + 4);
  }

  const step = values.length > 1 ? plotW / (values.length - 1) : 0;
  const points = values.map((value, index) => ({
    x: pad.left + step * index,
    y: height - pad.bottom - ((value - min) / range) * plotH,
    value,
  }));

  ctx.strokeStyle = colors.primary;
  ctx.lineWidth = 3;
  ctx.beginPath();
  points.forEach((point, index) => {
    if (index === 0) ctx.moveTo(point.x, point.y);
    else ctx.lineTo(point.x, point.y);
  });
  ctx.stroke();

  points.forEach((point) => {
    ctx.fillStyle = colors.primary;
    ctx.beginPath();
    ctx.arc(point.x, point.y, 5, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = colors.text;
    ctx.font = "12px system-ui";
    ctx.fillText(formatValue(point.value, unit), point.x - 18, point.y - 10);
  });

  ctx.fillStyle = colors.muted;
  ctx.font = "12px system-ui";
  ctx.fillText(labels[0] || "", pad.left, height - 16);
  ctx.fillText(labels[labels.length - 1] || "", Math.max(pad.left, width - pad.right - 92), height - 16);
  ctx.fillText(data.lower_is_better ? "Weniger ist besser" : "Mehr ist besser", pad.left, height - 4);
}

function redrawCharts() {
  document.querySelectorAll(".metric-chart").forEach(drawMetricChart);
}

window.addEventListener("rangelog:theme-change", redrawCharts);
redrawCharts();
