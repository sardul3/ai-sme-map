const $ = (id) => document.getElementById(id);
const EVAL_KEY = "atlas_eval_log";
const PAGE = document.body.dataset.page || "home";

function atlasRoot(pathname = location.pathname) {
  const pageStems = new Set(["index", "commute", "library"]);
  let path = pathname || "/";
  if (!path.startsWith("/")) path = `/${path}`;
  let trimmed = path.replace(/\/+$/, "");
  const last = trimmed.split("/").pop() || "";
  const stem = last.endsWith(".html") ? last.slice(0, -5) : last;
  if (last.endsWith(".html") || pageStems.has(stem)) {
    trimmed = trimmed.replace(/\/[^/]+$/, "");
  }
  if (trimmed.endsWith("/web")) trimmed = trimmed.slice(0, -4);
  else if (trimmed === "web") trimmed = "";
  if (!trimmed || trimmed === "/") return "/";
  return `${trimmed}/`;
}

function dataHref(name) {
  return `${atlasRoot()}data/${name}`;
}

async function load() {
  const [graph, resources, progress, meta, placement, linkStatus, inbox] = await Promise.all([
    fetch(dataHref("graph.json")).then((r) => r.json()),
    fetch(dataHref("resources.json")).then((r) => r.json()),
    fetch(dataHref("progress.json"))
      .then((r) => r.json())
      .catch(() => ({})),
    fetch(dataHref("catalog_meta.json"))
      .then((r) => r.json())
      .catch(() => ({})),
    fetch(dataHref("placement.json"))
      .then((r) => r.json())
      .catch(() => ({ questions: [] })),
    fetch(dataHref("link_status.json"))
      .then((r) => (r.ok ? r.json() : { urls: {} }))
      .catch(() => ({ urls: {} })),
    fetch(dataHref("inbox.json"))
      .then((r) => (r.ok ? r.json() : { commute_candidates: [] }))
      .catch(() => ({ commute_candidates: [] })),
  ]);
  const stored = JSON.parse(localStorage.getItem("atlas_progress") || "null");
  const byId = Object.fromEntries(resources.map((r) => [r.id, r]));
  return {
    graph,
    resources,
    byId,
    progress: stored && Object.keys(stored).length > 1 ? { ...progress, ...stored } : progress,
    meta,
    placement,
    linkStatus,
    inbox,
  };
}

function parentOf(id, byId) {
  const rec = byId[id];
  if (rec && rec.parent_id) return byId[rec.parent_id];
  return Object.values(byId).find((r) => (r.parts || []).some((p) => p.id === id));
}

function isComplete(progress, id, byId) {
  if (progress[id] === "done") return true;
  const rec = byId[id] || {};
  const parts = rec.parts || [];
  if (parts.length && parts.every((p) => isComplete(progress, p.id, byId))) return true;
  const parent = parentOf(id, byId);
  if (parent && progress[parent.id] === "done") return true;
  return false;
}

function pinsOf(progress) {
  const raw = progress && progress.pins;
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) return {};
  const out = {};
  for (const [k, v] of Object.entries(raw)) {
    if (typeof k === "string" && typeof v === "string") out[k] = v;
  }
  return out;
}

function stationPrimary(station, progress, byId) {
  const pin = pinsOf(progress)[station.id];
  if (pin && byId[pin] && !isComplete(progress, pin, byId)) return pin;
  return (station.do || [])[0] || null;
}

function doIdsForStation(station, progress, byId) {
  const doIds = [...(station.do || [])];
  const pin = pinsOf(progress)[station.id];
  if (pin && byId[pin] && !isComplete(progress, pin, byId)) {
    return [pin, ...doIds.filter((id) => id !== pin)];
  }
  return doIds;
}

function togglePin(progress, stationId, resourceId) {
  const pins = { ...pinsOf(progress) };
  if (pins[stationId] === resourceId) delete pins[stationId];
  else pins[stationId] = resourceId;
  return { ...progress, pins };
}

function applyStatus(progress, byId, id, status) {
  const out = { ...progress, [id]: status };
  const rec = byId[id] || {};
  if (status === "done") {
    for (const p of rec.parts || []) out[p.id] = "done";
    const parent = parentOf(id, byId);
    if (parent && (parent.parts || []).every((p) => out[p.id] === "done")) out[parent.id] = "done";
  } else {
    const parent = parentOf(id, byId);
    if (parent && out[parent.id] === "done") out[parent.id] = "doing";
  }
  return out;
}

function nextFocus(graph, resources, progress) {
  // Keep in sync with scripts/focus.py
  const byId = Object.fromEntries(resources.map((r) => [r.id, r]));
  for (const station of graph.nodes || []) {
    const primaryId = stationPrimary(station, progress, byId);
    if (!primaryId) continue;
    const rec = byId[primaryId];
    if (!rec) continue;
    if (rec.parts && rec.parts.length) {
      for (const part of rec.parts) {
        if (!isComplete(progress, part.id, byId)) {
          return packFocus(station, rec, part);
        }
      }
      if (!isComplete(progress, rec.id, byId)) return packFocus(station, rec, null);
      continue;
    }
    if (!isComplete(progress, rec.id, byId)) return packFocus(station, rec, null);
  }
  return { done: true };
}

function pinStationForCard(explicitStationId) {
  if (explicitStationId) return explicitStationId;
  if (PAGE !== "commute" && active && active.id) return active.id;
  const focus = nextFocus(state.graph, state.resources, state.progress);
  return focus.done ? null : focus.stationId;
}

function packFocus(station, rec, part) {
  const title = (part && part.title) || rec.title;
  const url = (part && part.url) || rec.url;
  return {
    done: false,
    stationId: station.id,
    stationTitle: station.title,
    resourceId: rec.id,
    resourceTitle: rec.title,
    partId: part ? part.id : null,
    url,
    sitting: rec.sitting || "",
    label: part ? `${rec.title} · ${part.title}` : rec.title,
    title,
  };
}

function sittingsDone(graph, progress, byId) {
  return graph.nodes.filter((n) => n.do?.[0] && isComplete(progress, n.do[0], byId)).length;
}

function stationIndex(graph, stationId) {
  return graph.nodes.findIndex((n) => n.id === stationId) + 1;
}

function stationById(id) {
  return state.graph.nodes.find((n) => n.id === id);
}

function accessBadge(r) {
  if (r.access === "coursera") return `<span class="badge coursera">coursera</span>`;
  if (r.access === "pluralsight") return `<span class="badge pluralsight">pluralsight</span>`;
  return `<span class="badge">${r.access}</span>`;
}

function sittingMark(text) {
  return text ? `<span class="sitting">${text}</span>` : "";
}

function scoreLine(r) {
  if (!r.scores) return "";
  const s = r.scores;
  return `<div class="ev">Ranked for intuition ${s.intuition}/5 · exercises ${s.exercises}/5 · stack ${s.stack}/5 · depth ${s.depth}/5</div>`;
}

function doRankBadge(rail, rank) {
  if (rail !== "do") return "";
  if (rank === 0) return `<span class="badge start">start here</span>`;
  return `<span class="badge also">also</span>`;
}

function statusKinds(rail) {
  if (rail === "do" || rail === "project" || rail === "lesson" || rail === "commute" || rail === "podcast") {
    return ["doing", "done"];
  }
  return ["skimmed", "done"];
}

function staleBadge(url) {
  const row = state.linkStatus && state.linkStatus.urls && state.linkStatus.urls[url];
  if (!row) return "";
  if (row.error === "404" || row.error === "410") return `<span class="badge stale">dead link</span>`;
  if (row.last_ok) {
    const age = (Date.now() - Date.parse(row.last_ok)) / 86400000;
    if (age > 90) return `<span class="badge stale">unchecked 90d+</span>`;
  }
  return "";
}

function statusButtons(id, current, kinds) {
  return kinds
    .map(
      (s) =>
        `<button type="button" data-id="${id}" data-st="${s}" class="${s === current ? "on" : ""}" aria-label="Mark ${s}">${s}</button>`
    )
    .join("");
}

function coveredBadge(r, progress, byId) {
  const parent = r.parent_id ? byId[r.parent_id] : null;
  if (parent && isComplete(progress, parent.id, byId)) {
    return `<span class="badge start">covered by ${parent.title}</span>`;
  }
  if (r.parent_id && parent) return `<span class="badge also">lesson of ${parent.title}</span>`;
  return "";
}

function playButton(r) {
  if (!r.audio_url) return "";
  return `<button type="button" data-commute-play="${r.id}" aria-label="Play ${r.title}">Play</button>`;
}

function starButton(r, progress, stationId) {
  const sid = pinStationForCard(stationId);
  if (!sid) return "";
  const on = pinsOf(progress)[sid] === r.id;
  const label = on ? "Unpin start here" : "Pin as start here";
  return `<button type="button" class="star ${on ? "on" : ""}" data-pin="${r.id}" data-pin-station="${sid}" aria-pressed="${on}" aria-label="${label}">★</button>`;
}

function renderResource(r, progress, { rank = 0, rail = "do", stationId = null } = {}) {
  const st = progress[r.id] || "todo";
  const byId = state.byId;
  const hitRail = r.audio_url ? "commute" : rail;
  return `<article class="card">
    <div>
      <div class="title"><a href="${r.url}" target="_blank" rel="noreferrer">${r.title}</a></div>
      <div class="ev">${r.evidence || ""}</div>
      ${scoreLine(r)}
      <div class="prov">${doRankBadge(rail, rank)}${coveredBadge(r, progress, byId)}${staleBadge(r.url)}${accessBadge(r)}${r.kind} · ${r.provider} · ${r.level}${sittingMark(r.sitting)}</div>
    </div>
    <div class="status">${starButton(r, progress, stationId)}${playButton(r)}${statusButtons(r.id, st, statusKinds(hitRail))}</div>
  </article>`;
}

function renderParts(parent, progress) {
  const parts = parent.parts || [];
  if (!parts.length) return "";
  const rows = parts
    .map((p) => {
      const st = progress[p.id] || "todo";
      const href = p.url || parent.url;
      return `<article class="card part">
        <div class="title"><a href="${href}" target="_blank" rel="noreferrer">${p.title}</a></div>
        <div class="status">${statusButtons(p.id, st, ["doing", "done"])}</div>
      </article>`;
    })
    .join("");
  return `<div class="parts"><h5>Lessons</h5>${rows}</div>`;
}

function rail(title, ids, byId, progress, kind, { open = true, station = null } = {}) {
  const list = kind === "do" && station ? doIdsForStation(station, progress, byId) : ids;
  if (!list.length) return "";
  const cards = list
    .map((id, i) => {
      const r = byId[id];
      if (!r) return "";
      return (
        renderResource(r, progress, { rank: i, rail: kind, stationId: station && station.id }) +
        (kind === "do" ? renderParts(r, progress) : "")
      );
    })
    .join("");
  if (open) return `<div class="rail-block"><h4>${title}</h4>${cards}</div>`;
  return `<details class="rail-block extras"><summary>${title}</summary>${cards}</details>`;
}

function renderDrawer(node, byId, progress) {
  const el = $("drawer");
  if (!el || !node) return;
  el.hidden = false;
  if (PAGE === "commute") {
    const purpose = typeof node === "string" ? node : node && node.purpose;
    const meta = PURPOSES[purpose];
    if (!meta) return;
    const rows = commutePlaylist(state.graph, state.resources).filter((r) => r.purpose === purpose);
    const cards = rows
      .map((r, i) => {
        const on = state.nowPlaying && state.nowPlaying.id === r.id;
        const start = (r.rank ?? i) === 0 ? `<span class="badge start">start here</span>` : "";
        return `<article class="card ${on ? "playing" : ""}">
          <div>
            <div class="title"><a href="${r.url}" target="_blank" rel="noreferrer">${r.title}</a></div>
            <div class="ev">${r.evidence || ""}</div>
            <div class="prov">${start}${showName(r)} · ${r.kind}${sittingMark(r.sitting)}</div>
          </div>
          <div class="status">
            ${playButton(r)}
            ${statusButtons(r.id, progress[r.id] || "todo", ["doing", "done"])}
          </div>
        </article>`;
      })
      .join("");
    el.innerHTML = `
      <p class="kicker">${meta.title} · ${meta.rail} · eyes-off</p>
      <h3>${meta.title}</h3>
      <p class="why">${meta.why}</p>
      ${cards || `<p class="why">No episodes on this rail yet.</p>`}`;
    return;
  }
  const primary = byId[node.do[0]];
  const skip = primary
    ? `<p><button type="button" class="skip" data-skip="${primary.id}" aria-label="Skip this station, I already know it">I already know this station</button></p>`
    : "";
  el.innerHTML = `
    <p class="kicker">Stage ${node.stage} · ${node.rail} · ${node.branch}</p>
    <h3>${node.title}</h3>
    <p class="why">${node.why}</p>
    ${skip}
    ${rail("Do (ranked)", node.do, byId, progress, "do", { station: node })}
    ${rail("Build", node.project, byId, progress, "project")}
    ${rail("Parallel style", node.parallel, byId, progress, "parallel", { open: false })}
    ${rail("Skim — library, not homework", node.skim, byId, progress, "skim", { open: false })}
  `;
}

function stationButton(n, progress, activeId, byId) {
  const live = state.nowPlaying && state.nowPlaying.station_id === n.id ? " live" : "";
  const nDo = n.do.length;
  const nDone = n.do.filter((id) => isComplete(progress, id, byId)).length;
  return `<button class="station ${n.rail} ${n.id === activeId ? "active" : ""}${live}" data-node="${n.id}">
    ${n.title}
    <span class="meta">${n.branch} · ${nDone}/${nDo} do</span>
  </button>`;
}

function renderPurposeMap(progress, activePurpose, byId) {
  const map = $("map");
  if (!map) return;
  map.classList.add("purpose-map");
  const rows = commutePlaylist(state.graph, state.resources);
  map.innerHTML = PURPOSE_ORDER.map((name) => {
    const meta = PURPOSES[name];
    const eps = rows.filter((r) => r.purpose === name);
    const nDone = eps.filter((r) => isComplete(progress, r.id, byId)).length;
    const live = state.nowPlaying && state.nowPlaying.purpose === name ? " live" : "";
    const start = eps[0];
    return `<section class="stage purpose ${meta.rail}">
      <button type="button" class="station ${meta.rail} ${name === activePurpose ? "active" : ""}${live}" data-purpose="${name}">
        ${meta.title}
        <span class="meta">${eps.length} eps · ${nDone} done${start ? ` · start: ${start.title}` : ""}</span>
      </button>
      <p class="why">${meta.why}</p>
    </section>`;
  }).join("");
}

function renderMap(graph, progress, activeId, expanded, byId) {
  const map = $("map");
  if (!map) return;
  map.classList.remove("purpose-map");
  const stages = graph.stages;
  map.innerHTML = stages
    .map((stage) => {
      const nodes = graph.nodes.filter((n) => n.stage === stage.id);
      const theory = nodes.filter((n) => n.rail === "theory");
      const practice = nodes.filter((n) => n.rail === "practice");
      const later = stage.id >= 2;
      const open = expanded.has(stage.id);
      const caption = later && !open ? `later · ${nodes.length} stations` : stage.months;
      return `<section class="stage ${later ? "later" : ""} ${open ? "open" : ""}">
        <button type="button" class="stage-toggle" data-stage="${stage.id}" ${later ? "" : "disabled"}>
          <span class="stage-id">T${stage.id}</span>
          <h2>${stage.name}</h2>
          <div class="months">${caption}</div>
        </button>
        <div class="stations">
          <div class="rail-label theory">Theory</div>
          ${theory.map((n) => stationButton(n, progress, activeId, byId)).join("") || `<p class="months">—</p>`}
          <div class="rail-label practice">Practice</div>
          ${practice.map((n) => stationButton(n, progress, activeId, byId)).join("") || `<p class="months">—</p>`}
        </div>
      </section>`;
    })
    .join("");
}

function normalizeTopic(raw) {
  return (raw || "")
    .trim()
    .toLowerCase()
    .replace(/[,:;]+$/, "")
    .replace(/\s+/g, " ")
    .trim();
}

function topicContains(needle, ...parts) {
  const hay = parts.map((p) => (p == null ? "" : String(p))).join(" ").toLowerCase();
  if (!needle) return false;
  if (hay.includes(needle)) return true;
  const tokens = hay.split(/[^a-z0-9]+/).filter(Boolean);
  const need = needle.split(/\s+/).filter(Boolean);
  return tokens.includes(needle) || need.every((t) => tokens.includes(t));
}

function matchShelf(topic, harvestFiles, stations, resources) {
  const needle = normalizeTopic(topic);
  const harvest = [];
  const harvestNames = new Set();
  for (const row of harvestFiles || []) {
    const name = row.name || "";
    const stem = name.replace(/\.md$/, "").replace(/-/g, " ");
    if (topicContains(needle, name, row.role, stem)) {
      harvest.push({ name, role: row.role || "" });
      harvestNames.add(name);
    }
  }
  const stationHits = [];
  for (const st of stations || []) {
    if (topicContains(needle, st.id, st.title, st.branch, st.why)) {
      stationHits.push(st);
    }
  }
  const featured = [];
  const leftover = [];
  for (const rec of resources || []) {
    if (!topicContains(needle, rec.title, rec.evidence, (rec.branches || []).join(" "))) continue;
    if (harvestNames.has(rec.source)) continue;
    if (rec.featured && rec.source === "curated") featured.push(rec);
    else leftover.push(rec);
  }
  return {
    harvest,
    stations: stationHits,
    featured,
    resources: leftover.slice(0, 12),
  };
}

function shelfHasHits(hits) {
  return Boolean(
    (hits.harvest && hits.harvest.length) ||
      (hits.stations && hits.stations.length) ||
      (hits.featured && hits.featured.length) ||
      (hits.resources && hits.resources.length)
  );
}

function topicIssueHref(topic, repo) {
  const title = `topic: ${normalizeTopic(topic)}`;
  return `https://github.com/${repo}/issues/new?template=topic_request.yml&title=${encodeURIComponent(title)}`;
}

function renderTopicHits(topic, hits, progress) {
  const box = $("hits");
  if (!box) return;
  if (!normalizeTopic(topic)) {
    box.hidden = true;
    box.innerHTML = "";
    return;
  }
  box.hidden = false;
  const repo = (state.meta && state.meta.github_repo) || "sardul3/ai-sme-map";
  if (!shelfHasHits(hits)) {
    box.innerHTML = `<h3>Nothing on the shelf for “${topic}”</h3>
      <p class="why">File a topic request. Actions will comment if a list appears, or open a harvest PR. That never edits Tonight Do rails.</p>
      <p><a class="go" href="${topicIssueHref(topic, repo)}" target="_blank" rel="noreferrer">File a topic request</a></p>`;
    return;
  }
  const harvest = (hits.harvest || [])
    .map((h) => {
      const stem = h.name.replace(/\.md$/, "");
      return `<p><a href="library.html#${stem}">Harvest · ${stem}</a>${h.role ? ` — ${h.role}` : ""}</p>`;
    })
    .join("");
  const stations = (hits.stations || [])
    .map(
      (st) =>
        `<button type="button" class="station ${st.rail || "practice"}" data-node="${st.id}">${st.title}<span class="meta">${st.branch || ""}</span></button>`
    )
    .join("");
  const featured = (hits.featured || [])
    .map((r) => renderResource(r, progress, { rail: "skim" }))
    .join("");
  const extra = (hits.resources || [])
    .map((r) => renderResource(r, progress, { rail: r.audio_url ? "commute" : "skim" }))
    .join("");
  box.innerHTML = `<h3>Already on the shelf for “${topic}”</h3>
    ${harvest ? `<div class="rail-block"><h4>Harvest lists</h4>${harvest}</div>` : ""}
    ${stations ? `<div class="rail-block"><h4>Stations</h4>${stations}</div>` : ""}
    ${featured ? `<div class="rail-block"><h4>Featured</h4>${featured}</div>` : ""}
    ${extra ? `<div class="rail-block extras"><h4>Also cataloged</h4>${extra}</div>` : ""}`;
}

function askShelf(topic) {
  const harvest = (state.meta && state.meta.harvest_lists) || [];
  const hits = matchShelf(topic, harvest, state.graph.nodes, state.resources);
  renderTopicHits(topic, hits, state.progress);
  return hits;
}

function evalLog(event, extra) {
  if (localStorage.getItem("atlas_eval") !== "1") return;
  const rows = JSON.parse(localStorage.getItem(EVAL_KEY) || "[]");
  rows.push({ t: Date.now(), event, ...extra });
  localStorage.setItem(EVAL_KEY, JSON.stringify(rows.slice(-200)));
}

async function saveProgress(progress) {
  localStorage.setItem("atlas_progress", JSON.stringify(progress));
  try {
    const res = await fetch(dataHref("progress.json"), {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(progress),
    });
    if (!res.ok) return;
    const data = await res.json().catch(() => null);
    if (data && data.progress) state.progress = data.progress;
  } catch {
    /* static copy: localStorage only */
  }
}

const COMMUTE_POS_KEY = "atlas_commute_pos";

function commuteStore() {
  try {
    return JSON.parse(localStorage.getItem(COMMUTE_POS_KEY) || "{}") || {};
  } catch {
    return {};
  }
}

function saveCommutePos(id, time, speed) {
  const store = commuteStore();
  store.positions = store.positions || {};
  if (id) store.positions[id] = time;
  if (speed != null) store.speed = speed;
  localStorage.setItem(COMMUTE_POS_KEY, JSON.stringify(store));
}

const PURPOSES = {
  learn: { title: "Learn", why: "A concept you can finish on a walk. Teaching shows, not chat.", rail: "theory", mark: "L" },
  interview: { title: "Hear people", why: "Researchers and practitioners, in their own voice.", rail: "theory", mark: "H" },
  apply: { title: "Ship", why: "How teams put models, agents, and infra into production.", rail: "practice", mark: "S" },
  pulse: { title: "Stay current", why: "What moved this year — indexes, recsys, agent news.", rail: "practice", mark: "C" },
};
const PURPOSE_ORDER = ["learn", "interview", "apply", "pulse"];

function commutePlaylist(graph, resources) {
  const order = new Map(PURPOSE_ORDER.map((name, i) => [name, i]));
  return resources
    .filter((r) => r.audio_url && order.has(r.purpose))
    .sort(
      (a, b) =>
        order.get(a.purpose) - order.get(b.purpose) ||
        (a.rank ?? 99) - (b.rank ?? 99) ||
        a.title.localeCompare(b.title)
    );
}

function purposeOf(r) {
  return PURPOSES[r && r.purpose] || null;
}

function showName(r) {
  if (r.provider === "ocdevel") return "Machine Learning Guide";
  if (r.provider === "linear-digressions") return "Linear Digressions";
  if (r.provider === "talking-machines") return "Talking Machines";
  if (r.provider === "dataskeptic") return "Data Skeptic";
  if (r.provider === "practical-ai") return "Practical AI";
  if (r.provider === "twiml") return "TWIML";
  if (r.provider === "latent-space") return "Latent Space";
  return "Learning Machines 101";
}

function formatClock(sec) {
  if (!Number.isFinite(sec)) return "0:00";
  const s = Math.max(0, Math.floor(sec));
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
}

function renderCommute() {
  const el = $("commute");
  if (!el) return;
  const rows = commutePlaylist(state.graph, state.resources);
  if (!rows.length) {
    el.innerHTML = `<p class="kicker">Commute</p><h2>No episodes yet</h2>
      <p class="why">Eyes-off original enclosures only — not YouTube.</p>`;
    return;
  }
  const next = rows.filter((r) => !isComplete(state.progress, r.id, state.byId)).slice(0, 3);
  const pick = next.length ? next : rows.slice(0, 3);
  const cards = pick
    .map((r) => {
      const meta = purposeOf(r);
      const on = state.nowPlaying && state.nowPlaying.id === r.id;
      return `<article class="card ${on ? "playing" : ""}">
        <div>
          <div class="title"><a href="${r.url}" target="_blank" rel="noreferrer">${r.title}</a></div>
          <div class="prov">${showName(r)} · ${meta ? meta.title : ""}${sittingMark(r.sitting)}</div>
        </div>
        <div class="status">${playButton(r)}</div>
      </article>`;
    })
    .join("");
  el.innerHTML = `<p class="kicker">Next on the walk</p>
    <h2>${rows.length} episodes across four purposes</h2>
    <p class="why">Open a rail. Next/prev stays on that purpose. Harvest lists are below the map.</p>
    ${cards}`;
}

function unassignedResources(graph, resources) {
  const ids = new Set();
  for (const node of graph.nodes || []) {
    for (const rail of ["do", "parallel", "skim", "project"]) {
      for (const id of node[rail] || []) ids.add(id);
    }
  }
  const byId = Object.fromEntries(resources.map((r) => [r.id, r]));
  for (const id of [...ids]) {
    for (const part of (byId[id] && byId[id].parts) || []) {
      if (part.id) ids.add(part.id);
    }
  }
  for (const r of resources) {
    if (r.parent_id && ids.has(r.parent_id)) ids.add(r.id);
    if (r.audio_url && r.purpose) ids.add(r.id);
  }
  return resources.filter((r) => r.id && !ids.has(r.id));
}

function libraryCategory(r) {
  const src = r.source || "";
  if (src.endsWith(".md")) return `Harvest · ${src.replace(/\.md$/, "")}`;
  if (src === "curated" && r.featured) return "Curated · featured";
  if (src === "curated") return `Curated · ${r.kind || "other"}`;
  if (src === "commute") return "Commute inbox";
  return `Other · ${r.kind || "other"}`;
}

function libraryGroups(rows) {
  const buckets = new Map();
  for (const r of rows) {
    const cat = libraryCategory(r);
    if (!buckets.has(cat)) buckets.set(cat, []);
    buckets.get(cat).push(r);
  }
  const rank = (name) => {
    if (name === "Curated · featured") return 0;
    if (name.startsWith("Curated")) return 1;
    if (name === "Commute inbox") return 2;
    if (name.startsWith("Harvest")) return 3;
    return 4;
  };
  return [...buckets.entries()]
    .sort((a, b) => rank(a[0]) - rank(b[0]) || a[0].localeCompare(b[0]))
    .map(([category, list]) => ({
      category,
      rows: list.slice().sort((a, b) => a.title.localeCompare(b.title)),
    }));
}

function renderLibrary() {
  const el = $("library");
  if (!el) return;
  const rows = unassignedResources(state.graph, state.resources);
  const groups = libraryGroups(rows);
  const inbox = (state.inbox && state.inbox.commute_candidates) || [];
  const inboxCards = inbox
    .map((r) => {
      const fake = {
        ...r,
        id: r.audio_url || r.url,
        kind: "podcast",
        evidence: "Weekly inbox — not ranked. Copy into commute.py to play in-atlas.",
        source: "commute",
      };
      return renderResource(fake, state.progress, { rail: "skim" });
    })
    .join("");
  const inboxBlock = inbox.length
    ? `<details class="rail-block extras harvest-list" open>
        <summary data-category="Commute inbox">Commute inbox · ${inbox.length} not ranked</summary>
        <p class="why">Official RSS, sitting 12–75 min, original enclosure. A human still picks purpose and rank.</p>
        ${inboxCards}
      </details>`
    : "";
  const hash = (location.hash || "").replace(/^#/, "");
  const blocks = groups
    .map((g) => {
      const cards = g.rows
        .map((r) => renderResource(r, state.progress, { rail: r.audio_url ? "commute" : "skim" }))
        .join("");
      const stem = (g.category || "").replace(/^Harvest · /, "");
      const open = hash && (stem === hash || g.category.includes(hash));
      return `<details class="rail-block extras harvest-list"${open ? " open" : ""}>
        <summary data-category="${g.category}">${g.category} · ${g.rows.length}</summary>
        ${cards}
      </details>`;
    })
    .join("");
  el.innerHTML = `<p class="kicker">Not on a track</p>
    <h2>${rows.length} unassigned resources</h2>
    <p class="why">Tonight and Commute stay ranked. This shelf is the weekly scrape plus leftover curated rows.</p>
    ${inboxBlock}
    ${blocks || `<p class="why">Every catalog URL already sits on a track.</p>`}`;
}

function harvestGroups(resources) {
  const groups = new Map();
  for (const r of resources) {
    const src = r.source || "";
    if (!src.endsWith(".md")) continue;
    if (!groups.has(src)) groups.set(src, []);
    groups.get(src).push(r);
  }
  return [...groups.entries()].sort((a, b) => a[0].localeCompare(b[0]));
}

function renderHarvest() {
  const el = $("harvest");
  if (!el) return;
  const groups = harvestGroups(state.resources);
  const blocks = groups
    .map(([src, rows]) => {
      const label = src.replace(/\.md$/, "").replace(/-/g, " ");
      const cards = rows
        .slice()
        .sort((a, b) => a.title.localeCompare(b.title))
        .map((r) => renderResource(r, state.progress, { rail: r.audio_url ? "commute" : "skim" }))
        .join("");
      return `<details class="rail-block extras harvest-list">
        <summary>${label} · ${rows.length}</summary>
        ${cards}
      </details>`;
    })
    .join("");
  el.innerHTML = `<p class="kicker">Harvest library</p>
    <h2>All awesome resources</h2>
    <p class="why">Sourced lists. Skim, not tonight’s Do rail. Ask the shelf above to jump in.</p>
    ${blocks || `<p class="why">No harvest files in this catalog yet.</p>`}`;
}

function bindPlayer() {
  const audio = $("player-audio");
  if (!audio || audio.dataset.bound) return;
  audio.dataset.bound = "1";
  audio.addEventListener("timeupdate", () => {
    if (!state.nowPlaying) return;
    saveCommutePos(state.nowPlaying.id, audio.currentTime, audio.playbackRate);
    const seek = $("player-seek");
    if (seek && audio.duration) seek.value = String((audio.currentTime / audio.duration) * 100);
    const toggle = $("player-toggle");
    if (toggle) toggle.textContent = audio.paused ? "Play" : "Pause";
    const elapsed = $("player-elapsed");
    const remain = $("player-remain");
    if (elapsed) elapsed.textContent = formatClock(audio.currentTime);
    if (remain) remain.textContent = formatClock((audio.duration || 0) - (audio.currentTime || 0));
  });
  audio.addEventListener("loadedmetadata", () => {
    const store = commuteStore();
    const t = store.positions && state.nowPlaying && store.positions[state.nowPlaying.id];
    if (typeof t === "number" && !Number.isNaN(t)) audio.currentTime = t;
    audio.playbackRate = store.speed || 1;
    markSpeed(audio.playbackRate);
  });
  audio.addEventListener("play", syncMediaSession);
  audio.addEventListener("pause", syncMediaSession);
  audio.addEventListener("ended", () => playCommuteRelative(1));
}

function markSpeed(rate) {
  document.querySelectorAll("[data-speed]").forEach((btn) => {
    btn.classList.toggle("on", Number(btn.dataset.speed) === rate);
  });
}

function setupMediaSession(rec) {
  if (!navigator.mediaSession) return;
  const audio = $("player-audio");
  const meta = purposeOf(rec);
  navigator.mediaSession.metadata = new MediaMetadata({
    title: rec.title,
    artist: "SME Atlas commute",
    album: meta ? meta.title : "Commute",
  });
  navigator.mediaSession.setActionHandler("play", () => audio.play());
  navigator.mediaSession.setActionHandler("pause", () => audio.pause());
  navigator.mediaSession.setActionHandler("seekforward", () => {
    audio.currentTime = Math.min(audio.duration || audio.currentTime + 10, audio.currentTime + 10);
  });
  navigator.mediaSession.setActionHandler("seekbackward", () => {
    audio.currentTime = Math.max(0, audio.currentTime - 10);
  });
  navigator.mediaSession.setActionHandler("previoustrack", () => playCommuteRelative(-1));
  navigator.mediaSession.setActionHandler("nexttrack", () => playCommuteRelative(1));
}

function syncMediaSession() {
  if (!navigator.mediaSession || !state.nowPlaying) return;
  navigator.mediaSession.playbackState = $("player-audio")?.paused ? "paused" : "playing";
}

function playCommute(id) {
  const rec = state.byId[id];
  if (!rec || !rec.audio_url) return;
  const audio = $("player-audio");
  const box = $("player");
  const title = $("player-title");
  if (!audio || !box) return;
  state.nowPlaying = rec;
  if (rec.purpose) activePurpose = rec.purpose;
  box.hidden = false;
  bindPlayer();
  if (audio.getAttribute("src") !== rec.audio_url) {
    audio.src = rec.audio_url;
  }
  const store = commuteStore();
  audio.playbackRate = store.speed || 1;
  markSpeed(audio.playbackRate);
  if (title) title.textContent = rec.title;
  const show = $("player-show");
  const stLine = $("player-station");
  const art = $("player-art");
  const meta = purposeOf(rec);
  if (show) show.textContent = showName(rec);
  if (stLine) stLine.textContent = meta ? `${meta.title} · ${meta.why}` : "Commute";
  if (art) {
    art.className = `player-art ${meta ? meta.rail : "theory"}`;
    art.textContent = meta ? meta.mark : "▶";
  }
  setupMediaSession(rec);
  audio.play().catch(() => {});
  if (PAGE === "commute") redraw();
}

function playCommuteRelative(delta) {
  const all = commutePlaylist(state.graph, state.resources);
  const purpose = state.nowPlaying && state.nowPlaying.purpose;
  const rows = purpose ? all.filter((r) => r.purpose === purpose) : all;
  if (!rows.length) return;
  const i = state.nowPlaying ? rows.findIndex((r) => r.id === state.nowPlaying.id) : -1;
  const next = rows[(Math.max(i, 0) + delta + rows.length) % rows.length];
  if (next) playCommute(next.id);
}

function renderFocus(focus) {
  const el = $("focus");
  if (!el) return;
  if (focus.done) {
    el.innerHTML = `<p class="kicker">Focus</p><h2>Beginner path complete</h2>
      <p>Every station’s first Do item is done. Open later stations when you want the rest of the rail.
      <button type="button" data-reopen>Reopen last station</button></p>`;
    return;
  }
  const markId = focus.partId || focus.resourceId;
  el.innerHTML = `
    <p class="kicker">Tonight · ${focus.stationTitle}</p>
    <h2>${focus.label}</h2>
    <p class="focus-meta">${sittingMark(focus.sitting)}</p>
    <p class="focus-actions">
      <a class="go" href="${focus.url}" target="_blank" rel="noreferrer" aria-label="Open tonight's resource">Open</a>
      <button type="button" data-focus-st="doing" data-id="${markId}" aria-label="Mark tonight's item as doing">Doing</button>
      <button type="button" data-focus-st="done" data-id="${markId}" aria-label="Mark tonight's item done">Mark done</button>
    </p>`;
}

function paintCounts(graph, progress, focus, meta) {
  if (!$("counts") || !$("meta")) return;
  const nextLabel = focus.done ? "Path complete" : focus.stationTitle;
  const idx = focus.done ? graph.nodes.length : stationIndex(graph, focus.stationId);
  $("counts").innerHTML = `
    <div><dt>Station</dt><dd>${idx} / ${graph.nodes.length}</dd></div>
    <div><dt>Sittings done</dt><dd>${sittingsDone(graph, progress, state.byId)}</dd></div>
    <div><dt>Next</dt><dd><button type="button" class="next-jump" data-jump="${focus.stationId || ""}">${nextLabel}</button></dd></div>
  `;
  const compiled = graph.compiled_at || meta.compiled_at || "";
  const sha = meta.git_sha || "";
  const ranked = graph.ranking_pass || meta.ranking_pass || "";
  $("meta").textContent = [
    compiled && `Compiled ${compiled.slice(0, 10)}`,
    meta.resource_count && `${meta.resource_count} URLs`,
    ranked && `ranked ${ranked}`,
    sha && `git ${sha}`,
  ]
    .filter(Boolean)
    .join(" · ");
}

const state = await load();
const expanded = new Set(state.graph.stages.filter((s) => s.id < 2).map((s) => s.id));
const history = [];
const firstFocus = nextFocus(state.graph, state.resources, state.progress);
let active = stationById(firstFocus.stationId) || state.graph.nodes[0];
let activePurpose = "learn";
let lastTopic = "";
evalLog("load", { focus: firstFocus.label || "done" });

function ensureStageOpen(station) {
  if (station && station.stage >= 2) expanded.add(station.stage);
}

function snapshot() {
  history.push(JSON.stringify(state.progress));
  if (history.length > 20) history.shift();
}

function setProgressToggle(id, st) {
  snapshot();
  if (state.progress[id] === st) {
    state.progress = applyStatus(state.progress, state.byId, id, "todo");
    delete state.progress[id];
  } else {
    state.progress = applyStatus(state.progress, state.byId, id, st);
  }
}

function renderPlacement() {
  const el = $("placement");
  if (!el) return;
  const qs = (state.placement && state.placement.questions) || [];
  el.innerHTML = qs
    .map((q) => {
      const st = state.graph.nodes.find((n) => n.id === q.skip_station);
      const primary = st && st.do[0];
      const on = primary && isComplete(state.progress, primary, state.byId);
      return `<label class="place-row"><input type="checkbox" data-place="${primary || ""}" ${on ? "checked" : ""}/> ${q.prompt}</label>`;
    })
    .join("");
}

async function persistAndRedraw() {
  await saveProgress(state.progress);
  redraw();
  if (lastTopic) askShelf(lastTopic);
}

function redraw() {
  const focus = nextFocus(state.graph, state.resources, state.progress);
  if (!focus.done) ensureStageOpen(stationById(focus.stationId));
  ensureStageOpen(active);
  paintCounts(state.graph, state.progress, focus, state.meta);
  renderFocus(focus);
  renderCommute();
  renderHarvest();
  renderLibrary();
  if (PAGE === "commute") {
    renderPurposeMap(state.progress, activePurpose, state.byId);
    renderDrawer(activePurpose, state.byId, state.progress);
  } else {
    renderMap(state.graph, state.progress, active && active.id, expanded, state.byId);
    renderDrawer(active, state.byId, state.progress);
  }
  renderPlacement();
  const undo = $("undo");
  if (undo) undo.hidden = history.length === 0;
}

redraw();

document.body.addEventListener("click", async (ev) => {
  const pinBtn = ev.target.closest("[data-pin]");
  if (pinBtn) {
    const sid = pinBtn.dataset.pinStation;
    const rid = pinBtn.dataset.pin;
    if (!sid || !rid) return;
    snapshot();
    state.progress = togglePin(state.progress, sid, rid);
    await persistAndRedraw();
    return;
  }
  const playBtn = ev.target.closest("[data-commute-play]");
  if (playBtn) {
    playCommute(playBtn.dataset.commutePlay);
    return;
  }
  if (ev.target.id === "player-toggle") {
    const audio = $("player-audio");
    if (!audio || !audio.src) return;
    if (audio.paused) audio.play().catch(() => {});
    else audio.pause();
    return;
  }
  if (ev.target.id === "player-next") {
    playCommuteRelative(1);
    return;
  }
  if (ev.target.id === "player-prev") {
    playCommuteRelative(-1);
    return;
  }
  const skipBtn = ev.target.closest("[data-skip]");
  if (skipBtn && skipBtn.dataset.skip) {
    const audio = $("player-audio");
    if (!audio) return;
    audio.currentTime = Math.max(0, (audio.currentTime || 0) + Number(skipBtn.dataset.skip));
    return;
  }
  const speedBtn = ev.target.closest("[data-speed]");
  if (speedBtn) {
    const audio = $("player-audio");
    const rate = Number(speedBtn.dataset.speed);
    if (audio) audio.playbackRate = rate;
    saveCommutePos(state.nowPlaying && state.nowPlaying.id, audio ? audio.currentTime : 0, rate);
    markSpeed(rate);
    return;
  }
  if (ev.target.id === "undo") {
    if (!history.length) return;
    state.progress = JSON.parse(history.pop());
    await persistAndRedraw();
    return;
  }
  const place = ev.target.closest("[data-place]");
  if (place) {
    const id = place.dataset.place;
    if (!id) return;
    snapshot();
    if (place.checked) state.progress = applyStatus(state.progress, state.byId, id, "done");
    else {
      state.progress = applyStatus(state.progress, state.byId, id, "todo");
      delete state.progress[id];
    }
    evalLog("placement", { id, on: place.checked });
    const focus = nextFocus(state.graph, state.resources, state.progress);
    if (!focus.done) active = stationById(focus.stationId) || active;
    await persistAndRedraw();
    return;
  }
  if (ev.target.closest("[data-reopen]")) {
    active = state.graph.nodes[0];
    redraw();
    $("drawer")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const skip = ev.target.closest("[data-skip]");
  if (skip) {
    snapshot();
    state.progress = applyStatus(state.progress, state.byId, skip.dataset.skip, "done");
    evalLog("skip_station", { id: skip.dataset.skip });
    const focus = nextFocus(state.graph, state.resources, state.progress);
    if (!focus.done) active = stationById(focus.stationId) || active;
    await persistAndRedraw();
    return;
  }
  const jump = ev.target.closest("[data-jump]");
  if (jump && jump.dataset.jump) {
    active = stationById(jump.dataset.jump) || active;
    redraw();
    $("focus")?.scrollIntoView({ behavior: "smooth", block: "start" });
    return;
  }
  const stageBtn = ev.target.closest("[data-stage]");
  if (stageBtn && !stageBtn.disabled) {
    const id = Number(stageBtn.dataset.stage);
    if (expanded.has(id)) expanded.delete(id);
    else expanded.add(id);
    redraw();
    return;
  }
  const focusBtn = ev.target.closest("[data-focus-st]");
  if (focusBtn) {
    setProgressToggle(focusBtn.dataset.id, focusBtn.dataset.focusSt);
    evalLog("focus_status", { id: focusBtn.dataset.id, st: focusBtn.dataset.focusSt });
    const focus = nextFocus(state.graph, state.resources, state.progress);
    if (!focus.done) active = stationById(focus.stationId) || active;
    await persistAndRedraw();
    return;
  }
  const stBtn = ev.target.closest("[data-st]");
  if (stBtn) {
    setProgressToggle(stBtn.dataset.id, stBtn.dataset.st);
    await persistAndRedraw();
    return;
  }
  const purposeBtn = ev.target.closest("[data-purpose]");
  if (purposeBtn) {
    activePurpose = purposeBtn.dataset.purpose;
    redraw();
    return;
  }
  const station = ev.target.closest("[data-node]");
  if (station) {
    active = stationById(station.dataset.node);
    redraw();
  }
});

$("player-seek")?.addEventListener("input", (ev) => {
  const audio = $("player-audio");
  if (!audio || !audio.duration) return;
  audio.currentTime = (Number(ev.target.value) / 100) * audio.duration;
});

document.addEventListener("keydown", async (ev) => {
  if (ev.target.matches("input, textarea")) return;
  if (ev.code === "Space" || ev.key === " ") {
    const audio = $("player-audio");
    if (audio && audio.src && $("player") && !$("player").hidden) {
      ev.preventDefault();
      if (audio.paused) audio.play().catch(() => {});
      else audio.pause();
      return;
    }
  }
  if (ev.key === "d" || ev.key === "D") {
    const focus = nextFocus(state.graph, state.resources, state.progress);
    if (focus.done) return;
    const id = focus.partId || focus.resourceId;
    setProgressToggle(id, "done");
    evalLog("keyboard_done", { id });
    const next = nextFocus(state.graph, state.resources, state.progress);
    if (!next.done) active = stationById(next.stationId) || active;
    await persistAndRedraw();
  }
});

$("find")?.addEventListener("submit", (ev) => {
  ev.preventDefault();
  const q = $("q");
  lastTopic = q ? q.value : "";
  askShelf(lastTopic);
  $("hits")?.scrollIntoView({ behavior: "smooth", block: "start" });
});
