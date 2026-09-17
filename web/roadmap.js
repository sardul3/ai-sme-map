const NS = "http://www.w3.org/2000/svg";
const VIEW_W = 5600;
const VIEW_H = 9000;
const CHIP_W = 280;
const CHIP_H = 34;
const CHIP_GAP = 8;
const PAD = 16;
const COL_GAP = 20;
const CLUSTER_COLS = 3;
const TITLE_H = 40;
const LANE_LABEL_H = 18;
const ORIGIN_X = 48;
const ORIGIN_Y = 56;
const STACK_GAP = 40;
const RAIL_GAP = 72;
const SCALE_MIN = 0.2;
const SCALE_MAX = 8;
const LANES = [
  { id: "do", label: "MUST" },
  { id: "parallel", label: "ELECTIVE" },
  { id: "skim", label: "MAY" },
  { id: "project", label: "Build" },
];
const CHECKPOINT_W = PAD * 2 + LANES.length * CHIP_W + (LANES.length - 1) * COL_GAP;
const STAGE_GAP = CHECKPOINT_W + 96;
const CLUSTER_W = PAD * 2 + CLUSTER_COLS * CHIP_W + (CLUSTER_COLS - 1) * COL_GAP;

function canvasRow(r) {
  return r && !(r.audio_url && r.purpose);
}

function laneX(laneId) {
  const i = Math.max(0, LANES.findIndex((l) => l.id === laneId));
  return PAD + i * (CHIP_W + COL_GAP);
}

function stationLaneLayout(st, byId, progress) {
  const atlas = globalThis.atlas;
  const lanes = {};
  let maxY = TITLE_H;
  for (const lane of LANES) {
    const ids =
      atlas && lane.id === "do"
        ? atlas.doIdsForStation(st, progress || {}, byId || {})
        : st[lane.id] || [];
    const x = laneX(lane.id);
    let y = TITLE_H + LANE_LABEL_H;
    const items = [];
    for (const id of ids) {
      const r = byId && byId[id];
      if (!canvasRow(r)) continue;
      items.push({ id, x, y });
      y += CHIP_H + CHIP_GAP;
    }
    if (items.length === 0) y += CHIP_H + CHIP_GAP;
    y += 6;
    maxY = Math.max(maxY, y);
    lanes[lane.id] = items;
  }
  return { lanes, height: Math.max(maxY + PAD, TITLE_H + 48) };
}

function checkpointHeight(st, byId, progress) {
  return stationLaneLayout(st, byId, progress).height;
}

function stageX(stage) {
  return ORIGIN_X + (stage || 0) * STAGE_GAP;
}

function checkpointPos(st, layout, i, height) {
  const hit = layout.checkpoints && layout.checkpoints[st.id];
  if (hit && typeof hit.x === "number") return hit;
  const x = stageX(st.stage);
  const band = st.rail === "practice" ? ORIGIN_Y + 900 : ORIGIN_Y;
  const y = band + (i || 0) * ((height || 0) + STACK_GAP);
  return { x, y };
}

function placeGroup(group, layout, byId, progress, startY, pos) {
  let y = startY;
  for (let i = 0; i < group.length; i++) {
    const st = group[i];
    const height = checkpointHeight(st, byId, progress);
    const placed = checkpointPos(st, layout, i, height);
    const authored = layout.checkpoints && layout.checkpoints[st.id];
    pos[st.id] = authored && typeof authored.x === "number" ? placed : { x: placed.x, y };
    y = pos[st.id].y + height + STACK_GAP;
  }
  return y;
}

function checkpointStack(stations, layout, byId, progress) {
  const groups = new Map();
  for (const st of stations || []) {
    const rail = st.rail === "practice" ? "practice" : "theory";
    const key = `${st.stage || 0}:${rail}`;
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(st);
  }
  const pos = {};
  const stages = [...new Set((stations || []).map((s) => s.stage || 0))].sort((a, b) => a - b);
  for (const stage of stages) {
    const theory = groups.get(`${stage}:theory`) || [];
    const practice = groups.get(`${stage}:practice`) || [];
    const theoryBottom = placeGroup(theory, layout, byId, progress, ORIGIN_Y, pos);
    const practiceStart = theory.length ? theoryBottom + RAIL_GAP : ORIGIN_Y;
    placeGroup(practice, layout, byId, progress, practiceStart, pos);
  }
  return pos;
}

function listingAnchors(stations, pos, byId, progress) {
  const anchors = {};
  for (const st of stations || []) {
    const origin = (pos && pos[st.id]) || { x: 0, y: 0 };
    const laid = stationLaneLayout(st, byId, progress);
    for (const lane of LANES) {
      for (const item of laid.lanes[lane.id] || []) {
        anchors[item.id] = {
          x: origin.x + item.x,
          y: origin.y + item.y,
          lane: lane.id,
          station: st.id,
        };
      }
    }
  }
  return anchors;
}

function listingEdges(stations, pos, byId, progress) {
  const anchors = listingAnchors(stations, pos, byId, progress);
  const edges = [];
  const seen = new Set();
  function push(from, to, kind) {
    if (!from || !to || from === to) return;
    if (!anchors[from] || !anchors[to]) return;
    const key = `${from}->${to}:${kind}`;
    if (seen.has(key)) return;
    seen.add(key);
    edges.push({ from, to, kind });
  }
  for (const st of stations || []) {
    const laid = stationLaneLayout(st, byId, progress);
    const must = (laid.lanes.do || []).map((item) => item.id);
    for (let i = 0; i < must.length - 1; i++) push(must[i], must[i + 1], "must");
    const firstMust = must[0];
    if (firstMust) {
      for (const lane of LANES) {
        if (lane.id === "do") continue;
        const head = (laid.lanes[lane.id] || [])[0];
        if (head) push(firstMust, head.id, "side");
      }
    }
    for (const pre of st.prereqs || []) {
      const prior = stationLaneLayout(
        (stations || []).find((n) => n.id === pre) || { id: pre },
        byId,
        progress
      );
      const fromMust = (prior.lanes.do || []).map((item) => item.id);
      const src = fromMust[fromMust.length - 1];
      if (src && firstMust) push(src, firstMust, "prereq");
    }
  }
  return edges;
}

function edgeMarkup(a, b, kind) {
  const vertical = Math.abs(a.x - b.x) < CHIP_W / 2;
  const x1 = vertical ? a.x + CHIP_W / 2 : a.x + CHIP_W;
  const y1 = vertical ? a.y + CHIP_H : a.y + CHIP_H / 2;
  const x2 = vertical ? b.x + CHIP_W / 2 : b.x;
  const y2 = vertical ? b.y : b.y + CHIP_H / 2;
  return `<line class="roadmap-edge roadmap-edge-${kind}" x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" marker-end="url(#roadmap-arrow)"/>`;
}

function clusterKey(group, rows) {
  const list = rows || (group && group.rows) || [];
  const sources = [...new Set(list.map((r) => r && r.source).filter(Boolean))];
  if (sources.length === 1 && String(sources[0]).endsWith(".md")) return sources[0];
  return (group && group.category) || "";
}

function clusterHeight(nChips) {
  const rows = Math.max(1, Math.ceil((nChips || 0) / CLUSTER_COLS));
  return TITLE_H + rows * (CHIP_H + CHIP_GAP) + PAD * 2;
}

function clusterPos(key, layout, nChips, previousCluster) {
  const height = clusterHeight(nChips || 0);
  const hit = layout.clusters && layout.clusters[key];
  if (hit && typeof hit.x === "number") return { x: hit.x, y: hit.y, height };
  const x = ORIGIN_X + 8 * STAGE_GAP;
  const y = previousCluster ? previousCluster.y + previousCluster.height + 48 : 56;
  return { x, y, height, width: CLUSTER_W };
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

  function truncate(title, n = 42) {
    const s = String(title || "");
    if (s.length <= n) return s;
    return `${s.slice(0, n - 1)}…`;
  }

  function syncViewBox(svg) {
    const rect = svg.getBoundingClientRect();
    const w = Math.max(1, Math.round(rect.width) || VIEW_W);
    const h = Math.max(1, Math.round(rect.height) || VIEW_H);
    svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  }

  function applyView(svg) {
    const world = svg.querySelector("#roadmap-world");
    if (!world) return;
    world.setAttribute("transform", `translate(${view.x} ${view.y}) scale(${view.scale})`);
    updateZoomPct();
  }

  function setScale(next, svg, clientX, clientY) {
    const clamped = Math.min(SCALE_MAX, Math.max(SCALE_MIN, next));
    const rect = svg.getBoundingClientRect();
    const cx = clientX == null ? rect.left + rect.width / 2 : clientX;
    const cy = clientY == null ? rect.top + rect.height / 2 : clientY;
    const p = svgPoint(svg, cx, cy);
    const k = view.scale ? clamped / view.scale : 1;
    view.x = p.x - (p.x - view.x) * k;
    view.y = p.y - (p.y - view.y) * k;
    view.scale = clamped;
    applyView(svg);
  }

  function zoomBy(factor, svg) {
    setScale(view.scale * factor, svg);
  }

  function fitView(svg) {
    const world = svg.querySelector("#roadmap-world");
    if (!world) return;
    let bbox;
    try {
      bbox = world.getBBox();
    } catch {
      bbox = { x: 0, y: 0, width: VIEW_W, height: VIEW_H };
    }
    if (!bbox.width || !bbox.height) {
      view.x = 0;
      view.y = 0;
      view.scale = 1;
      applyView(svg);
      return;
    }
    const rect = svg.getBoundingClientRect();
    const pad = 48;
    const sx = (rect.width - pad * 2) / bbox.width;
    const sy = (rect.height - pad * 2) / bbox.height;
    view.scale = Math.min(SCALE_MAX, Math.max(SCALE_MIN, Math.min(sx, sy)));
    view.x = -bbox.x * view.scale + pad;
    view.y = -bbox.y * view.scale + pad;
    applyView(svg);
  }

  function svgPoint(svg, clientX, clientY) {
    const pt = svg.createSVGPoint();
    pt.x = clientX;
    pt.y = clientY;
    const ctm = svg.getScreenCTM();
    if (!ctm) return { x: 0, y: 0 };
    return pt.matrixTransform(ctm.inverse());
  }

  function parseTranslate(value) {
    const m = /translate\(\s*(-?[\d.]+)\s*[,\s]\s*(-?[\d.]+)/.exec(value || "");
    return m ? { x: Number(m[1]), y: Number(m[2]) } : { x: 0, y: 0 };
  }

  function worldDelta(svg, x0, y0, x1, y1) {
    const p0 = svgPoint(svg, x0, y0);
    const p1 = svgPoint(svg, x1, y1);
    return { x: p1.x - p0.x, y: p1.y - p0.y };
  }

  function ensureRoadmapNote() {
    let note = document.getElementById("roadmap-note");
    if (note) return note;
    note = document.createElement("p");
    note.id = "roadmap-note";
    note.className = "rule";
    note.hidden = true;
    note.dataset.file = "assignments.json";
    const board = document.getElementById("board");
    if (board && board.parentNode) board.parentNode.insertBefore(note, board);
    else document.body.appendChild(note);
    return note;
  }

  function setRoadmapNote(text) {
    const note = ensureRoadmapNote();
    note.textContent = text;
    note.hidden = !text;
  }

  function snapBack(el, orig) {
    if (el) el.setAttribute("transform", orig);
    setRoadmapNote("Assignments are localhost-only.");
  }

  function inSeedRails(id, seed) {
    for (const st of (seed && seed.nodes) || []) {
      for (const lane of LANES) {
        if ((st[lane.id] || []).includes(id)) return true;
      }
    }
    return false;
  }

  function dropTargetAt(clientX, clientY, dragged) {
    const prev = dragged && dragged.style ? dragged.style.pointerEvents : "";
    if (dragged && dragged.style) dragged.style.pointerEvents = "none";
    const el = document.elementFromPoint(clientX, clientY);
    if (dragged && dragged.style) dragged.style.pointerEvents = prev;
    const lane = el && el.closest && el.closest("[data-drop-station][data-drop-rail]");
    if (lane) {
      return {
        kind: "lane",
        station: lane.getAttribute("data-drop-station"),
        rail: lane.getAttribute("data-drop-rail"),
      };
    }
    const cluster = el && el.closest && el.closest("[data-drop-cluster]");
    if (cluster) {
      return { kind: "cluster", key: cluster.getAttribute("data-drop-cluster") };
    }
    return null;
  }

  function placementsCopy() {
    const atlas = globalThis.atlas;
    const cur = (atlas.state.assignments && atlas.state.assignments.placements) || {};
    return { ...cur };
  }

  function chipMarkup(r, x, y, { stationId = "", pinId = "" } = {}) {
    const atlas = globalThis.atlas;
    const done = atlas.isComplete(atlas.state.progress, r.id, atlas.state.byId);
    const starred = Boolean(stationId && pinId === r.id);
    const titleX = done ? 20 : 10;
    const stationAttr = stationId ? ` data-station="${esc(stationId)}"` : "";
    const url = r.url || "";
    const urlAttr = url ? ` data-url="${esc(url)}"` : "";
    const starX = CHIP_W - 18;
    const inner = `<g class="roadmap-chip" data-resource="${esc(r.id)}"${stationAttr}${urlAttr} transform="translate(${x} ${y})" role="link" tabindex="0">
      <rect width="${CHIP_W}" height="${CHIP_H}"/>
      ${done ? `<text class="roadmap-mark" x="8" y="22">✓</text>` : ""}
      <text class="roadmap-chip-title" x="${titleX}" y="22">${esc(truncate(r.title))}</text>
      ${starred ? `<text class="roadmap-star" x="${starX}" y="22">★</text>` : ""}
    </g>`;
    if (!url) return inner;
    return `<a class="roadmap-chip-link" href="${esc(url)}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
  }

  function checkpointMarkup(st, origin, { progress, byId, pinId }) {
    const rail = st.rail === "practice" ? "practice" : "theory";
    const laid = stationLaneLayout(st, byId, progress);
    const chips = [
      `<g class="roadmap-checkpoint-header" data-drag-checkpoint="${esc(st.id)}">
      <rect class="roadmap-checkpoint-head" width="${CHECKPOINT_W}" height="${TITLE_H}" fill="transparent"/>
      <text class="roadmap-checkpoint-kicker" x="16" y="14">T${esc(st.stage)} · ${esc(st.branch || "")}</text>
      <text class="roadmap-checkpoint-title" x="16" y="30">${esc(st.title)}</text>
    </g>`,
    ];
    for (const lane of LANES) {
      const x = laneX(lane.id);
      const items = laid.lanes[lane.id] || [];
      const laneParts = [
        `<text class="roadmap-lane-label" x="${x}" y="${TITLE_H + 11}">${esc(lane.label)}</text>`,
      ];
      for (const item of items) {
        const r = byId[item.id];
        if (!canvasRow(r)) continue;
        laneParts.push(chipMarkup(r, item.x, item.y, { stationId: st.id, pinId }));
      }
      const lastY = items.length ? items[items.length - 1].y + CHIP_H + 6 : TITLE_H + LANE_LABEL_H + CHIP_H;
      const laneH = Math.max(lastY - TITLE_H, CHIP_H + LANE_LABEL_H);
      chips.push(`<g class="roadmap-lane" data-drop-station="${esc(st.id)}" data-drop-rail="${esc(lane.id)}">
      <rect class="roadmap-lane-drop" x="${x - 4}" y="${TITLE_H}" width="${CHIP_W + 8}" height="${laneH}" fill="transparent"/>
      ${laneParts.join("")}
    </g>`);
    }
    const height = laid.height;
    return `<g class="roadmap-checkpoint ${rail}" data-station="${esc(st.id)}" transform="translate(${origin.x} ${origin.y})">
      <rect class="roadmap-checkpoint-body" width="${CHECKPOINT_W}" height="${height}"/>
      <rect class="roadmap-checkpoint-rail" width="6" height="${height}"/>
      ${chips.join("")}
    </g>`;
  }

  function clusterMarkup(group, origin, key) {
    const chips = [
      `<g class="roadmap-cluster-header" data-drag-cluster="${esc(key)}">
      <rect class="roadmap-cluster-head" width="${CLUSTER_W}" height="${TITLE_H}" fill="transparent"/>
      <text class="roadmap-checkpoint-title" x="12" y="22">${esc(group.category)}</text>
    </g>`,
    ];
    let i = 0;
    for (const r of group.rows || []) {
      if (!canvasRow(r)) continue;
      const col = i % CLUSTER_COLS;
      const row = Math.floor(i / CLUSTER_COLS);
      const x = PAD + col * (CHIP_W + COL_GAP);
      const y = TITLE_H + row * (CHIP_H + CHIP_GAP);
      chips.push(chipMarkup(r, x, y, {}));
      i += 1;
    }
    const height = clusterHeight(i);
    return `<g class="roadmap-cluster" data-cluster="${esc(key)}" data-drop-cluster="${esc(key)}" transform="translate(${origin.x} ${origin.y})">
      <rect class="roadmap-cluster-body" width="${CLUSTER_W}" height="${height}"/>
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
      if (st) {
        atlas.active = st;
        drawerTarget = { kind: "station", id: st.id, station: st };
        atlas.renderDrawer(st, state.byId, state.progress);
      }
    } else if (rid && state.byId[rid]) {
      drawerTarget = { kind: "resource", id: rid };
      refreshDrawer();
    }
  }

  async function finishChipDrag(ev, drag) {
    const atlas = globalThis.atlas;
    if (!drag.moved) {
      drag.el.setAttribute("transform", drag.orig);
      openChip(drag.el);
      const url = drag.el.getAttribute("data-url");
      if (url) window.open(url, "_blank", "noopener,noreferrer");
      return;
    }
    panned = true;
    if (!atlas || !atlas.isAuthor()) {
      snapBack(drag.el, drag.orig);
      return;
    }
    const hit = dropTargetAt(ev.clientX, ev.clientY, drag.el);
    if (!hit || !drag.resourceId) {
      drag.el.setAttribute("transform", drag.orig);
      return;
    }
    const placements = placementsCopy();
    const id = drag.resourceId;
    if (hit.kind === "lane") {
      placements[id] = { station: hit.station, rail: hit.rail };
    } else if (!atlas.state.graphSeed || inSeedRails(id, atlas.state.graphSeed)) {
      placements[id] = null;
    } else {
      delete placements[id];
    }
    try {
      await atlas.saveAssignments({ schema_version: 1, placements });
      setRoadmapNote("");
      renderRoadmap();
    } catch {
      snapBack(drag.el, drag.orig);
    }
  }

  async function finishGroupDrag(ev, drag, svg) {
    const atlas = globalThis.atlas;
    if (!drag.moved) {
      drag.el.setAttribute("transform", drag.orig);
      return;
    }
    panned = true;
    if (!atlas || !atlas.isAuthor()) {
      snapBack(drag.el, drag.orig);
      return;
    }
    const d = worldDelta(svg, drag.startX, drag.startY, ev.clientX, ev.clientY);
    const orig = parseTranslate(drag.orig);
    const next = { x: orig.x + d.x, y: orig.y + d.y };
    const layout = atlas.state.layout || { schema_version: 1, checkpoints: {}, clusters: {} };
    const nextLayout = {
      schema_version: layout.schema_version || 1,
      checkpoints: { ...(layout.checkpoints || {}) },
      clusters: { ...(layout.clusters || {}) },
    };
    if (drag.checkpointId) nextLayout.checkpoints[drag.checkpointId] = next;
    if (drag.clusterKey) nextLayout.clusters[drag.clusterKey] = next;
    try {
      await atlas.saveLayout(nextLayout);
      setRoadmapNote("");
      renderRoadmap();
    } catch {
      snapBack(drag.el, drag.orig);
    }
  }

  function bindPanZoom(svg) {
    if (svg.dataset.panBound) return;
    svg.dataset.panBound = "1";
    let drag = null;

    svg.addEventListener("pointerdown", (ev) => {
      if (ev.button !== 0) return;
      const chip = ev.target.closest && ev.target.closest(".roadmap-chip");
      if (chip) {
        drag = {
          kind: "chip",
          el: chip,
          orig: chip.getAttribute("transform") || "",
          startX: ev.clientX,
          startY: ev.clientY,
          resourceId: chip.getAttribute("data-resource") || "",
          moved: false,
        };
        panned = false;
        svg.setPointerCapture(ev.pointerId);
        return;
      }
      const header =
        ev.target.closest && ev.target.closest("[data-drag-checkpoint], [data-drag-cluster]");
      if (header) {
        const group = header.closest(".roadmap-checkpoint, .roadmap-cluster");
        if (!group) return;
        drag = {
          kind: "group",
          el: group,
          orig: group.getAttribute("transform") || "",
          startX: ev.clientX,
          startY: ev.clientY,
          checkpointId: header.getAttribute("data-drag-checkpoint") || "",
          clusterKey: header.getAttribute("data-drag-cluster") || "",
          moved: false,
        };
        panned = false;
        svg.setPointerCapture(ev.pointerId);
        return;
      }
      drag = {
        kind: "pan",
        lastX: ev.clientX,
        lastY: ev.clientY,
        moved: false,
      };
      panned = false;
      svg.setPointerCapture(ev.pointerId);
      svg.classList.add("panning");
    });
    svg.addEventListener("pointermove", (ev) => {
      if (!drag) return;
      if (drag.kind === "pan") {
        const dx = ev.clientX - drag.lastX;
        const dy = ev.clientY - drag.lastY;
        if (Math.abs(dx) + Math.abs(dy) > 3) {
          drag.moved = true;
          panned = true;
        }
        drag.lastX = ev.clientX;
        drag.lastY = ev.clientY;
        const p0 = svgPoint(svg, ev.clientX - dx, ev.clientY - dy);
        const p1 = svgPoint(svg, ev.clientX, ev.clientY);
        view.x += p1.x - p0.x;
        view.y += p1.y - p0.y;
        applyView(svg);
        return;
      }
      const d = worldDelta(svg, drag.startX, drag.startY, ev.clientX, ev.clientY);
      if (Math.abs(d.x) + Math.abs(d.y) > 3) drag.moved = true;
      const orig = parseTranslate(drag.orig);
      drag.el.setAttribute("transform", `translate(${orig.x + d.x} ${orig.y + d.y})`);
    });
    const endDrag = (ev) => {
      if (!drag) return;
      const current = drag;
      drag = null;
      svg.classList.remove("panning");
      try {
        svg.releasePointerCapture(ev.pointerId);
      } catch {
        /* already released */
      }
      if (current.kind === "chip") {
        void finishChipDrag(ev, current);
        return;
      }
      if (current.kind === "group") {
        void finishGroupDrag(ev, current, svg);
      }
    };
    svg.addEventListener("pointerup", endDrag);
    svg.addEventListener("pointercancel", endDrag);
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
        const factor = ev.deltaY < 0 ? 1.12 : 1 / 1.12;
        setScale(view.scale * factor, svg, ev.clientX, ev.clientY);
      },
      { passive: false }
    );
  }

  function ensureBoard() {
    const board = document.getElementById("board");
    if (!board) return null;
    ensureRoadmapNote();
    let zoom = document.getElementById("roadmap-zoom");
    if (!zoom) {
      zoom = document.createElement("div");
      zoom.id = "roadmap-zoom";
      zoom.className = "roadmap-zoom";
      zoom.innerHTML =
        '<button type="button" id="roadmap-zoom-out" aria-label="Zoom out">−</button>' +
        '<span id="roadmap-zoom-pct">100%</span>' +
        '<button type="button" id="roadmap-zoom-in" aria-label="Zoom in">+</button>' +
        '<button type="button" id="roadmap-fit" aria-label="Fit roadmap to view">Fit</button>';
      board.prepend(zoom);
      const svgOf = () => board.querySelector("svg");
      document.getElementById("roadmap-zoom-out").addEventListener("click", () => {
        const next = svgOf();
        if (next) zoomBy(1 / 1.25, next);
      });
      document.getElementById("roadmap-zoom-in").addEventListener("click", () => {
        const next = svgOf();
        if (next) zoomBy(1.25, next);
      });
      document.getElementById("roadmap-fit").addEventListener("click", () => {
        const next = svgOf();
        if (next) fitView(next);
      });
    }
    let svg = board.querySelector("svg");
    if (!svg) {
      svg = document.createElementNS(NS, "svg");
      svg.setAttribute("role", "img");
      svg.setAttribute("aria-label", "Harvest graph roadmap");
      svg.setAttribute("preserveAspectRatio", "xMinYMin meet");
      const world = document.createElementNS(NS, "g");
      world.setAttribute("id", "roadmap-world");
      svg.appendChild(world);
      board.appendChild(svg);
      bindPanZoom(svg);
      window.addEventListener("resize", () => syncViewBox(svg));
    }
    syncViewBox(svg);
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
    const pos = checkpointStack(stations, layout, byId, progress);
    const anchors = listingAnchors(stations, pos, byId, progress);
    const edges = listingEdges(stations, pos, byId, progress);

    const parts = [
      `<defs><marker id="roadmap-arrow" viewBox="0 0 8 8" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path class="roadmap-arrow" d="M0 0 L8 4 L0 8 z"/></marker></defs>`,
    ];
    for (const edge of edges) {
      const a = anchors[edge.from];
      const b = anchors[edge.to];
      if (a && b) parts.push(edgeMarkup(a, b, edge.kind));
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
    let previousCluster = null;
    groups.forEach((group) => {
      const key = clusterKey(group, group.rows);
      const nChips = (group.rows || []).filter(canvasRow).length;
      previousCluster = clusterPos(key, layout, nChips, previousCluster);
      parts.push(clusterMarkup(group, previousCluster, key));
    });
    world.innerHTML = parts.join("");
    applyView(svg);
    refreshDrawer();
  }

  globalThis.renderRoadmap = renderRoadmap;
  renderRoadmap();
}
