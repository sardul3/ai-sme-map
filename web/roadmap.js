const NS = "http://www.w3.org/2000/svg";
const VIEW_W = 3600;
const VIEW_H = 2800;
const CHIP_W = 200;
const CHIP_H = 28;
const CHIP_GAP = 4;
const PAD = 12;
const CHECKPOINT_W = PAD * 2 + CHIP_W;
const TITLE_H = 36;
const LANE_LABEL_H = 16;
const LANES = [
  { id: "do", label: "MUST" },
  { id: "parallel", label: "ELECTIVE" },
  { id: "skim", label: "MAY" },
  { id: "project", label: "Build" },
];

function checkpointPos(st, layout) {
  const hit = layout.checkpoints && layout.checkpoints[st.id];
  if (hit && typeof hit.x === "number") return hit;
  const x = 48 + (st.stage || 0) * 300;
  const y = st.rail === "theory" ? 56 : 460;
  return { x, y };
}

function clusterKey(group, rows) {
  const list = rows || (group && group.rows) || [];
  const sources = [...new Set(list.map((r) => r && r.source).filter(Boolean))];
  if (sources.length === 1 && String(sources[0]).endsWith(".md")) return sources[0];
  return (group && group.category) || "";
}

function clusterPos(key, index, layout) {
  const hit = layout.clusters && layout.clusters[key];
  if (hit && typeof hit.x === "number") return hit;
  return { x: 48 + 8 * 300, y: 56 + index * 240 };
}

if (document.body.dataset.page !== "roadmap") {
  /* Canvas lives on roadmap.html only. */
} else {
  initRoadmap();
}

function initRoadmap() {
  const view = { x: 0, y: 0, scale: 1 };
  let drawerTarget = null;
  let panned = false;

  function esc(value) {
    return String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function truncate(title, n = 28) {
    const s = String(title || "");
    if (s.length <= n) return s;
    return `${s.slice(0, n - 1)}…`;
  }

  function canvasRow(r) {
    return r && !(r.audio_url && r.purpose);
  }

  function applyView(svg) {
    const world = svg.querySelector("#roadmap-world");
    if (!world) return;
    world.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.scale})`);
  }

  function svgPoint(svg, clientX, clientY) {
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    return pt.matrixTransform(ctm.inverse());
  }

  function chipMarkup(r, x, y, { stationId = "", pinId = "" } = {}) {
    const atlas = globalThis.atlas;
    const done = atlas.isComplete(atlas.state.progress, r.id, atlas.state.byId);
    const starred = Boolean(stationId && pinId === r.id);
    const titleX = done ? 18 : 8;
    const stationAttr = stationId ? ` data-station="${esc(stationId)}"` : "";
    return `<g class="roadmap-chip" data-resource="${esc(r.id)}"${stationAttr} transform="translate(${x} ${y})" role="button" tabindex="0">
      <rect width="${CHIP_W}" height="${CHIP_H}"/>
      ${done ? `<text class="roadmap-mark" x="6" y="18">✓</text>` : ""}
      <text class="roadmap-chip-title" x="${titleX}" y="18">${esc(truncate(r.title))}</text>
      ${starred ? `<text class="roadmap-star" x="184" y="18">★</text>` : ""}
    </g>`;
  }

  function laneIds(st, laneId, progress, byId) {
    const atlas = globalThis.atlas;
    if (laneId === "do") return atlas.doIdsForStation(st, progress, byId);
    return st[laneId] || [];
  }

  function checkpointMarkup(st, pos, { progress, byId, pinId }) {
    const rail = st.rail === "practice" ? "practice" : "theory";
    let y = TITLE_H;
    const chips = [];
    for (const lane of LANES) {
      chips.push(
        `<text class="roadmap-lane-label" x="${PAD}" y="${y + 11}">${esc(lane.label)}</text>`
      );
      y += LANE_LABEL_H;
      const ids = laneIds(st, lane.id, progress, byId);
      for (const id of ids) {
        const r = byId[id];
        if (!canvasRow(r)) continue;
        chips.push(chipMarkup(r, PAD, y, { stationId: st.id, pinId }));
        y += CHIP_H + CHIP_GAP;
      }
      y += 6;
    }
    const height = Math.max(y + PAD, TITLE_H + 48);
    return `<g class="roadmap-checkpoint ${rail}" data-station="${esc(st.id)}" transform="translate(${pos.x} ${pos.y})">
      <rect class="roadmap-checkpoint-body" width="${CHECKPOINT_W}" height="${height}"/>
      <rect class="roadmap-checkpoint-rail" width="6" height="${height}"/>
      <text class="roadmap-checkpoint-kicker" x="16" y="14">T${esc(st.stage)} · ${esc(st.branch || "")}</text>
      <text class="roadmap-checkpoint-title" x="16" y="30">${esc(st.title)}</text>
      ${chips.join("")}
    </g>`;
  }

  function clusterMarkup(group, pos, key) {
    let y = TITLE_H;
    const chips = [];
    for (const r of group.rows || []) {
      if (!canvasRow(r)) continue;
      chips.push(chipMarkup(r, PAD, y, {}));
      y += CHIP_H + CHIP_GAP;
    }
    const height = Math.max(y + PAD, TITLE_H + 28);
    return `<g class="roadmap-cluster" data-cluster="${esc(key)}" transform="translate(${pos.x} ${pos.y})">
      <rect class="roadmap-cluster-body" width="${CHECKPOINT_W}" height="${height}"/>
      <text class="roadmap-checkpoint-title" x="12" y="22">${esc(group.category)}</text>
      ${chips.join("")}
    </g>`;
  }

  function refreshDrawer() {
    const atlas = globalThis.atlas;
    if (!atlas || !drawerTarget) return;
    const { state } = atlas;
    if (drawerTarget.kind === "station") {
      const st = (state.graph.nodes || []).find((n) => n.id === drawerTarget.id) || drawerTarget.station;
      if (st) atlas.renderDrawer(st, state.byId, state.progress);
      return;
    }
    const r = state.byId[drawerTarget.id];
    const el = atlas.$("drawer");
    if (!el || !r) return;
    el.hidden = false;
    el.innerHTML = `<p class="kicker">Unassigned</p>${atlas.renderResource(r, state.progress, { rail: "skim" })}`;
  }

  function openChip(chip) {
    const atlas = globalThis.atlas;
    const rid = chip.getAttribute("data-resource");
    const sid = chip.getAttribute("data-station");
    const { state } = atlas;
    if (sid) {
      const st = (state.graph.nodes || []).find((n) => n.id === sid);
      if (!st) return;
      atlas.active = st;
      drawerTarget = { kind: "station", id: st.id, station: st };
      atlas.renderDrawer(st, state.byId, state.progress);
      return;
    }
    if (!rid || !state.byId[rid]) return;
    drawerTarget = { kind: "resource", id: rid };
    refreshDrawer();
  }

  function bindPanZoom(svg) {
    if (svg.dataset.panBound) return;
    svg.dataset.panBound = "1";
    let dragging = false;
    let lastX = 0;
    let lastY = 0;

    svg.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const chip = ev.target.closest && ev.target.closest(".roadmap-chip");
      if (chip) return;
      dragging = true;
      panned = false;
      lastX = ev.clientX;
      lastY = ev.clientY;
      svg.setPointerCapture(ev.pointerId);
      svg.classList.add("panning");
    });
    svg.addEventListener("pointermove", (ev) => {
      if (!dragging) return;
      const dx = ev.clientX - lastX;
      const dy = ev.clientY - lastY;
      if (Math.abs(dx) + Math.abs(dy) > 3) panned = true;
      lastX = ev.clientX;
      lastY = ev.clientY;
      const p0 = svgPoint(svg, ev.clientX - dx, ev.clientY - dy);
      const p1 = svgPoint(svg, ev.clientX, ev.clientY);
      view.x += p1.x - p0.x;
      view.y += p1.y - p0.y;
      applyView(svg);
    });
    const endPan = (ev) => {
      if (!dragging) return;
      dragging = false;
      svg.classList.remove("panning");
      try {
        svg.releasePointerCapture(ev.pointerId);
      } catch {
        /* already released */
      }
    };
    svg.addEventListener("pointerup", endPan);
    svg.addEventListener("pointercancel", endPan);
    svg.addEventListener("click", (ev) => {
      if (panned) {
        panned = false;
        ev.preventDefault();
        return;
      }
      const chip = ev.target.closest && ev.target.closest(".roadmap-chip");
      if (!chip) return;
      ev.preventDefault();
      openChip(chip);
    });
    svg.addEventListener(
      "wheel",
      (ev) => {
        ev.preventDefault();
        const factor = ev.deltaY < 0 ? 1.08 : 1 / 1.08;
        const next = Math.min(2.5, Math.max(0.25, view.scale * factor));
        const p = svgPoint(svg, ev.clientX, ev.clientY);
        const k = next / view.scale;
        view.x = p.x - (p.x - view.x) * k;
        view.y = p.y - (p.y - view.y) * k;
        view.scale = next;
        applyView(svg);
      },
      { passive: false }
    );
  }

  function ensureBoard() {
    const board = document.getElementById("board");
    if (!board) return null;
    let fit = document.getElementById("roadmap-fit");
    if (!fit) {
      fit = document.createElement("button");
      fit.type = "button";
      fit.id = "roadmap-fit";
      fit.textContent = "Fit";
      fit.setAttribute("aria-label", "Fit roadmap to view");
      fit.addEventListener("click", () => {
        view.x = 0;
        view.y = 0;
        view.scale = 1;
        const svg = board.querySelector("svg");
        if (svg) applyView(svg);
      });
      board.prepend(fit);
    }
    let svg = board.querySelector("svg");
    if (!svg) {
      svg = document.createElementNS(NS, "svg");
      svg.setAttribute("viewBox", `0 0 ${VIEW_W} ${VIEW_H}`);
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", "Harvest graph roadmap");
      const world = document.createElementNS(NS, "g");
      world.setAttribute("id", "roadmap-world");
      svg.appendChild(world);
      board.appendChild(svg);
      bindPanZoom(svg);
    }
    return svg;
  }

  function renderRoadmap() {
    const atlas = globalThis.atlas;
    if (!atlas) return;
    const svg = ensureBoard();
    if (!svg) return;
    const world = svg.querySelector("#roadmap-world");
    if (!world) return;
    const { state, pinsOf, unassignedResources, libraryGroups } = atlas;
    const layout = state.layout || { schema_version: 1, checkpoints: {}, clusters: {} };
    const graph = state.graph || { nodes: [] };
    const stations = graph.nodes || [];
    const byId = state.byId || {};
    const progress = state.progress || {};
    const pins = pinsOf(progress);
    const pos = {};
    for (const st of stations) pos[st.id] = checkpointPos(st, layout);

    const parts = [];
    for (const st of stations) {
      const to = pos[st.id];
      for (const pre of st.prereqs || st.prereq || []) {
        const from = pos[pre];
        if (!from || !to) continue;
        const x1 = from.x + CHECKPOINT_W / 2;
        const y1 = from.y;
        const x2 = to.x + CHECKPOINT_W / 2;
        const y2 = to.y;
        parts.push(`<line class="roadmap-edge" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}"/>`);
      }
    }
    for (const st of stations) {
      parts.push(
        checkpointMarkup(st, pos[st.id], {
          progress,
          byId,
          pinId: pins[st.id] || "",
        })
      );
    }
    const unassigned = unassignedResources(graph, state.resources || []);
    const groups = libraryGroups(unassigned);
    groups.forEach((group, index) => {
      const key = clusterKey(group, group.rows);
      parts.push(clusterMarkup(group, clusterPos(key, index, layout), key));
    });
    world.innerHTML = parts.join("");
    applyView(svg);
    refreshDrawer();
  }

  globalThis.renderRoadmap = renderRoadmap;
  renderRoadmap();
}
