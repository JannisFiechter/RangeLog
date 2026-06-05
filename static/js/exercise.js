const builder = document.querySelector(".exercise-builder");

if (builder) {
  const targetsNode = document.querySelector("#targetsData");
  const scoringNode = document.querySelector("#scoringData");
  const targets = JSON.parse((targetsNode && targetsNode.textContent) || "[]");
  const scoringMethods = JSON.parse((scoringNode && scoringNode.textContent) || "[]");
  const type = document.querySelector("#exerciseType");
  const targetSelect = document.querySelector("#targetSelect");
  const method = document.querySelector("#scoringMethod");
  const preview = document.querySelector("#targetPreview");
  const hint = document.querySelector("#scoringHint");
  const defaultScoringByTarget = {
    idpa: "idpa_time_plus",
    ipsc: "ipsc_minor",
    universal_silhouette: "time_plus",
  };

  function selectedTarget() {
    return targets.find((target) => target.id === targetSelect.value);
  }

  function selectedMethod() {
    return scoringMethods.find((item) => item.id === method.value);
  }

  function syncType() {
    const isStatic = type.value === "static";
    document.querySelectorAll(".static-options").forEach((item) => {
      item.hidden = !isStatic;
    });
    document.querySelectorAll(".dynamic-options").forEach((item) => {
      item.hidden = isStatic;
    });
    targetSelect.querySelectorAll("option").forEach((option) => {
      option.hidden = option.dataset.category !== type.value;
    });
    if (targetSelect.selectedOptions[0] && targetSelect.selectedOptions[0].hidden) {
      const first = Array.prototype.find.call(targetSelect.options, (option) => !option.hidden);
      if (first) targetSelect.value = first.value;
    }
    method.querySelectorAll("option").forEach((option) => {
      option.hidden = option.dataset.category !== type.value;
    });
    if (method.selectedOptions[0] && method.selectedOptions[0].hidden) {
      const first = Array.prototype.find.call(method.options, (option) => !option.hidden);
      if (first) method.value = first.value;
    }
    if (builder.dataset.existing !== "1") {
      applyTargetDefault();
    }
    syncPreview();
  }

  function applyTargetDefault() {
    const target = selectedTarget();
    const defaultMethod = target ? defaultScoringByTarget[target.id] : "";
    if (defaultMethod && method.querySelector(`option[value="${defaultMethod}"]`)) {
      method.value = defaultMethod;
    }
  }

  function syncPreview() {
    const target = selectedTarget();
    const scoring = selectedMethod();
    if (preview && target) {
      if (target.input_mode === "number_range") {
        preview.textContent = `${target.name}: Zahlenfeld ${target.min}-${target.max}.`;
      } else if (target.zones) {
        preview.textContent = `${target.name}: ${target.zones.map((zone) => zone.label).join(", ")}`;
      } else {
        preview.textContent = `${target.name}: ${target.description || "dynamische Scheibe"}`;
      }
    }
    if (hint && target && scoring) {
      hint.textContent = scoring.category === "dynamic"
        ? `Eingabezonen kommen aus ${scoring.name}, die Scheibe bleibt ${target.name}.`
        : "Statische Trefferwerte kommen aus der gewählten Scheibe.";
    }
  }

  type.addEventListener("change", syncType);
  targetSelect.addEventListener("change", () => {
    applyTargetDefault();
    syncPreview();
  });
  method.addEventListener("change", syncPreview);
  syncType();
}
