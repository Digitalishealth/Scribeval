const state = {
  data: null,
  dimension: "overall",
  view: "overview",
};

const dimensionLabels = {
  overall: "Overall",
  omission: "Omission",
  hallucination: "Hallucination",
  medicolegal: "Medicolegal",
  ahpra: "AHPRA",
  pdqi9: "PDQI-9",
  qnote: "QNOTE",
  medication_terminology: "Medication Terminology",
};

async function loadDemo() {
  const response = await fetch("./demo-data.json");
  if (!response.ok) {
    throw new Error(`Unable to load demo data: ${response.status}`);
  }
  state.data = await response.json();
  initialiseControls();
  render();
}

function initialiseControls() {
  const select = document.querySelector("#dimension-select");
  select.innerHTML = state.data.dimensions
    .map((dimension) => {
      const label = dimensionLabels[dimension] || titleCase(dimension);
      return `<option value="${dimension}">${label}</option>`;
    })
    .join("");
  select.value = state.dimension;
  select.addEventListener("change", (event) => {
    state.dimension = event.target.value;
    render();
  });

  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.view = button.dataset.view;
      document.querySelectorAll(".tab-button").forEach((tab) => {
        const active = tab.dataset.view === state.view;
        tab.classList.toggle("active", active);
        tab.setAttribute("aria-selected", String(active));
      });
      document.querySelectorAll(".view").forEach((view) => {
        view.classList.toggle("active", view.id === `${state.view}-view`);
      });
    });
  });
}

function render() {
  renderHeader();
  renderMetrics();
  renderRanking();
  renderCaseMix();
  renderStrategyMatrix();
  renderPromptLift();
  renderFindings();
  renderValidation();
}

function renderHeader() {
  document.querySelector("#case-count").textContent = `${state.data.metadata.case_count} cases`;
  document.querySelector("#generated-at").textContent = state.data.metadata.disclaimer;
}

function renderMetrics() {
  const ranked = rankedCandidates();
  const top = ranked[0];
  const baseline = state.data.candidates.find((candidate) => candidate.id === "nurse_cdss");
  const bestModel = ranked.find((candidate) => candidate.type === "ai_scribe");
  const biggestLift = promptLifts()[0];
  const safetyEvents = state.data.candidates.reduce(
    (sum, candidate) => sum + candidate.critical_findings,
    0,
  );

  const metrics = [
    {
      label: "Top candidate",
      value: top.label,
      detail: `${formatScore(top.scores[state.dimension])} ${dimensionLabel()} score`,
    },
    {
      label: "Best model",
      value: bestModel.label,
      detail: `${formatScore(bestModel.scores.overall)} overall vs ${formatScore(baseline.scores.overall)} baseline`,
    },
    {
      label: "Largest prompt lift",
      value: biggestLift.label,
      detail: `+${formatScore(biggestLift.lift)} from standard to CDSS-informed`,
    },
    {
      label: "Critical findings",
      value: String(safetyEvents),
      detail: "Across synthetic candidate summaries",
    },
  ];

  document.querySelector("#metrics-row").innerHTML = metrics
    .map(
      (metric) => `
        <article class="metric">
          <div class="metric-label">${escapeHtml(metric.label)}</div>
          <div class="metric-value">${escapeHtml(metric.value)}</div>
          <p class="metric-detail">${escapeHtml(metric.detail)}</p>
        </article>
      `,
    )
    .join("");
}

function renderRanking() {
  document.querySelector("#ranking-bars").innerHTML = rankedCandidates()
    .map((candidate) => barRow(candidate, candidate.scores[state.dimension]))
    .join("");
}

function renderCaseMix() {
  document.querySelector("#case-mix").innerHTML = state.data.case_mix
    .map(
      (item) => `
        <article class="case-item">
          <h3>${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(titleCase(item.acuity))} acuity · highest risk: ${escapeHtml(dimensionLabels[item.highest_risk_dimension] || titleCase(item.highest_risk_dimension))}</p>
        </article>
      `,
    )
    .join("");
}

function renderStrategyMatrix() {
  const strategies = state.data.prompting_strategies;
  const candidates = state.data.candidates;
  const header = strategies.map((strategy) => `<th>${escapeHtml(strategy.label)}</th>`).join("");

  const rows = candidates
    .map((candidate) => {
      const cells = strategies
        .map((strategy) => {
          const score = candidate.prompt_results[strategy.id];
          if (score === null) {
            return `<td class="score-cell">Baseline</td>`;
          }
          return `
            <td class="score-cell">
              <div class="cell-meter" style="--candidate-color: ${candidate.accent}; --cell-opacity: ${score};">
                ${formatScore(score)}
                <span style="width: ${score * 100}%"></span>
              </div>
            </td>
          `;
        })
        .join("");

      return `
        <tr>
          <th scope="row">
            <span class="candidate-name">
              <span class="swatch" style="--candidate-color: ${candidate.accent}"></span>
              ${escapeHtml(candidate.label)}
            </span>
          </th>
          ${cells}
        </tr>
      `;
    })
    .join("");

  document.querySelector("#strategy-matrix").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Candidate</th>
          ${header}
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function renderPromptLift() {
  document.querySelector("#prompt-lift").innerHTML = promptLifts()
    .map((item) => barRow(item, item.lift, true))
    .join("");
}

function renderFindings() {
  document.querySelector("#findings-list").innerHTML = state.data.findings
    .map(
      (finding) => `
        <article class="finding-item severity-${finding.severity}">
          <h3>${escapeHtml(finding.candidate)} · ${escapeHtml(finding.dimension)}</h3>
          <p>
            <span class="pill">${escapeHtml(titleCase(finding.severity))}</span>
            <span class="pill">${escapeHtml(finding.strategy)}</span>
          </p>
          <p>${escapeHtml(finding.finding)}</p>
        </article>
      `,
    )
    .join("");
}

function renderValidation() {
  const pilot = state.data.validation_pilot;
  if (!pilot) {
    return;
  }

  const summary = [
    {
      label: "Pilot cases",
      value: String(pilot.case_count),
      detail: `${pilot.submissions_per_case} blinded submissions per case`,
    },
    {
      label: "Reviewers",
      value: String(pilot.clinician_reviewers),
      detail: "Independent human ratings for calibration",
    },
    {
      label: "Median kappa",
      value: formatScore(pilot.summary.median_weighted_kappa),
      detail: pilot.summary.kappa_interpretation,
    },
    {
      label: "Median ICC",
      value: formatScore(pilot.summary.median_icc),
      detail: "Absolute score agreement",
    },
  ];

  document.querySelector("#validation-summary").innerHTML = summary
    .map(
      (metric) => `
        <article class="metric">
          <div class="metric-label">${escapeHtml(metric.label)}</div>
          <div class="metric-value">${escapeHtml(metric.value)}</div>
          <p class="metric-detail">${escapeHtml(metric.detail)}</p>
        </article>
      `,
    )
    .join("");

  document.querySelector("#agreement-table").innerHTML = `
    <table>
      <thead>
        <tr>
          <th>Dimension</th>
          <th>N</th>
          <th>Weighted kappa</th>
          <th>ICC(2,1)</th>
          <th>Mean diff</th>
        </tr>
      </thead>
      <tbody>
        ${pilot.agreement
          .map(
            (item) => `
              <tr>
                <th scope="row">${escapeHtml(dimensionLabels[item.dimension] || titleCase(item.dimension))}</th>
                <td>${escapeHtml(item.n_pairs)}</td>
                <td>${formatScore(item.weighted_kappa)}</td>
                <td>${formatScore(item.icc_2_1)}</td>
                <td>${formatScore(item.mean_abs_difference)}</td>
              </tr>
            `,
          )
          .join("")}
      </tbody>
    </table>
  `;

  document.querySelector("#validation-workflow").innerHTML = pilot.workflow
    .map(
      (item) => `
        <article class="case-item">
          <h3>${escapeHtml(item.label)}</h3>
          <p>${escapeHtml(item.detail)}</p>
        </article>
      `,
    )
    .join("");
}

function rankedCandidates() {
  return [...state.data.candidates].sort(
    (left, right) => right.scores[state.dimension] - left.scores[state.dimension],
  );
}

function promptLifts() {
  return state.data.candidates
    .filter((candidate) => candidate.type === "ai_scribe")
    .map((candidate) => ({
      ...candidate,
      lift: candidate.prompt_results.cdss_informed - candidate.prompt_results.standard,
    }))
    .sort((left, right) => right.lift - left.lift);
}

function barRow(candidate, score, isLift = false) {
  const width = isLift ? Math.min(score / 0.2, 1) : score;
  const scoreText = isLift ? `+${formatScore(score)}` : formatScore(score);
  return `
    <div class="bar-row" style="--candidate-color: ${candidate.accent}; --score-width: ${width * 100}%">
      <div class="candidate-name">
        <span class="swatch"></span>
        <span>${escapeHtml(candidate.label)}</span>
      </div>
      <div class="bar-track" aria-hidden="true">
        <div class="bar-fill"></div>
      </div>
      <div class="score">${scoreText}</div>
    </div>
  `;
}

function dimensionLabel() {
  return dimensionLabels[state.dimension] || titleCase(state.dimension);
}

function formatScore(score) {
  return Number(score).toFixed(2);
}

function titleCase(value) {
  return String(value)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

loadDemo().catch((error) => {
  document.body.innerHTML = `
    <main class="layout">
      <section class="panel">
        <h1>Unable to load demo</h1>
        <p>${escapeHtml(error.message)}</p>
      </section>
    </main>
  `;
});
