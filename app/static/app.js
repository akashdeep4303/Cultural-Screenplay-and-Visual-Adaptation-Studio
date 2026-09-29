const steps = [
  ["upload", "Upload"],
  ["extract", "Extraction"],
  ["plan", "Approval"],
  ["compare", "Adapted script"],
  ["visuals", "Visuals"],
  ["export", "Export"],
];

let project = null;
let sourceText = "";

const $ = (id) => document.getElementById(id);

function show(name) {
  document.querySelectorAll("main > section").forEach((s) => s.classList.add("hidden"));
  $("view-" + (name === "extract" ? "extract" : name)).classList.remove("hidden");
  if (name === "upload") $("view-upload").classList.remove("hidden");
  document.querySelectorAll("nav.steps button").forEach((b) => {
    b.classList.toggle("on", b.dataset.step === name);
  });
}

function renderSteps() {
  $("steps").innerHTML = steps
    .map(([id, label]) => `<button data-step="${id}">${label}</button>`)
    .join("");
  $("steps").onclick = (e) => {
    const b = e.target.closest("button");
    if (b) show(b.dataset.step);
  };
}

async function loadCultures() {
  const rows = await (await fetch("/api/cultures")).json();
  $("culture").innerHTML = rows
    .map((c) => `<option value="${c.id}">${c.label} — ${c.dialect}</option>`)
    .join("");
  $("regionHint").textContent = rows[0]?.region || "";
  $("culture").onchange = () => {
    const hit = rows.find((c) => c.id === $("culture").value);
    $("regionHint").textContent = hit ? hit.region : "";
  };
}

$("loadSample").onclick = async () => {
  const data = await (await fetch("/api/sample")).json();
  $("script").value = data.text;
  sourceText = data.text;
};

$("file").onchange = async (e) => {
  const file = e.target.files[0];
  if (!file) return;
  $("script").value = await file.text();
};

$("extract").onclick = async () => {
  sourceText = $("script").value;
  const body = new FormData();
  body.append("text", sourceText);
  body.append("culture_id", $("culture").value);
  body.append("setting", $("setting").value);
  body.append("script", $("scriptChoice").value);
  const res = await fetch("/api/projects", { method: "POST", body });
  project = await res.json();
  if (!res.ok) return alert(project.detail || "Extract failed");
  paintExtract();
  paintPlan();
  $("srcPre").textContent = sourceText;
  show("extract");
};

$("merge").onclick = async () => {
  const res = await fetch(`/api/projects/${project.project_id}/merge`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ keep: $("keep").value, drop: $("drop").value }),
  });
  project = await res.json();
  paintExtract();
};

$("demoDup").onclick = async () => {
  project = await (await fetch(`/api/projects/${project.project_id}/demo/duplicate-alias`, { method: "POST" })).json();
  $("keep").value = "Adam";
  $("drop").value = "Elder Son";
  paintExtract();
};

$("demoBreak").onclick = async () => {
  project = await (await fetch(`/api/projects/${project.project_id}/demo/break-letter`, { method: "POST" })).json();
  paintExtract();
};

$("approveExtract").onclick = async () => {
  project = await (await fetch(`/api/projects/${project.project_id}/approve-extraction`, { method: "POST" })).json();
  paintExtract();
  show("plan");
};

$("approvePlan").onclick = async () => {
  project = await (await fetch(`/api/projects/${project.project_id}/approve-plan`, { method: "POST" })).json();
  paintPlan();
};

$("adapt").onclick = async () => {
  project = await (await fetch(`/api/projects/${project.project_id}/adapt`, { method: "POST" })).json();
  $("adPre").textContent = project.adapted_screenplay;
  const rows = (project.change_log || []).slice(0, 40).map(
    (c) => `<tr><td>${c.scene_id}</td><td>${c.kind}</td><td>${esc(c.source)}</td><td>${esc(c.adapted)}</td><td>${esc(c.reason)}</td></tr>`
  );
  $("changeTable").innerHTML = `<tr><th>Scene</th><th>Kind</th><th>Source</th><th>Adapted</th><th>Why</th></tr>${rows.join("")}`;
  show("compare");
};

$("goVisuals").onclick = () => show("visuals");

$("fixApply").onclick = async () => {
  if (!project) return alert("Extract a screenplay first.");
  $("fixStatus").textContent = "Correcting…";
  const res = await fetch(`/api/projects/${project.project_id}/correct`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      kind: $("fixKind").value,
      target_id: $("fixId").value.trim(),
      field: $("fixField").value.trim(),
      value: $("fixValue").value,
      regenerate: true,
    }),
  });
  const data = await res.json();
  if (!res.ok) {
    $("fixStatus").textContent = data.detail || "Correction failed";
    $("fixStatus").className = "warn";
    return;
  }
  project = data;
  $("fixStatus").textContent =
    "Regenerated only: " + (data.affected_ids || []).join(", ") + ". Other plates were left untouched.";
  $("fixStatus").className = "ok";
  paintGallery();
  paintExtract();
  paintPlan();
  if (project.adapted_screenplay) $("adPre").textContent = project.adapted_screenplay;
};

$("generate").onclick = async () => {
  if (!project) return alert("Extract a screenplay first.");
  $("genStatus").textContent = "Generating…";
  const res = await fetch(`/api/projects/${project.project_id}/generate`, { method: "POST" });
  const data = await res.json();
  if (!res.ok) {
    $("genStatus").textContent = data.detail || "Blocked";
    $("genStatus").className = "warn";
    return;
  }
  project = data;
  $("genStatus").textContent = "Visual pack ready. Canonical IDs are linked under each figure.";
  $("genStatus").className = "ok";
  paintGallery();
  paintExport();
  show("visuals");
};

function paintExtract() {
  $("extractProblems").textContent = (project.extraction_problems || []).join(" ") || "No extraction problems.";
  $("sceneTable").innerHTML =
    `<tr><th>ID</th><th>Heading</th><th>Chars</th><th>Props</th><th>Continuity</th><th>Purpose</th></tr>` +
    project.scenes
      .map(
        (s) => `<tr>
        <td>${s.scene_id}</td>
        <td>${s.int_ext}. ${s.location} — ${s.time}<div class="muted">${esc(s.summary)}</div></td>
        <td>${s.characters.join(", ")}</td>
        <td>${s.props_present.join(", ")}</td>
        <td class="${s.continuity_warnings.length ? "warn" : "ok"}">${s.continuity_warnings.join("; ") || "ok"}</td>
        <td>${esc(s.dramatic_purpose)}</td>
      </tr>`
      )
      .join("");
  $("charTable").innerHTML =
    `<tr><th>ID</th><th>Source</th><th>Adapted</th><th>Aliases</th><th>Role</th><th>Approved</th></tr>` +
    project.characters
      .map(
        (c) => `<tr><td>${c.character_id}</td><td>${c.source_name}</td><td>${c.adapted_name}</td><td>${c.aliases.join(", ")}</td><td>${c.role}</td><td>${c.approved}</td></tr>`
      )
      .join("");
  const prod = [...(project.locations || []), ...(project.props || [])];
  $("prodTable").innerHTML =
    `<tr><th>ID</th><th>Kind</th><th>Source</th><th>Scenes</th></tr>` +
    prod.map((e) => `<tr><td>${e.element_id}</td><td>${e.kind}</td><td>${e.source_name}</td><td>${(e.scenes || []).join(", ")}</td></tr>`).join("");
  $("extractCont").innerHTML = (project.continuity || [])
    .map(
      (c) =>
        `<p><b>${c.scene_id}</b> wearing=${esc(JSON.stringify(c.wearing))} carrying=${esc(JSON.stringify(c.carrying))}<br/><span class="muted">${(c.notes || []).join(" | ")}</span></p>`
    )
    .join("");
}

function paintPlan() {
  const p = project.adaptation_plan;
  $("planBox").innerHTML = `<p>${esc(p.summary)}</p>` + p.decisions.map((d) => `<p><b>${d.topic}:</b> ${esc(d.reason)} <span class="muted">${esc(d.adapted)}</span></p>`).join("") +
    `<p class="warn">Uncertain: ${(p.uncertain_choices || []).join(" ")}</p>` +
    `<p>extraction_approved=${project.extraction_approved} plan_approved=${project.plan_approved}</p>`;
  $("costumeTable").innerHTML =
    `<tr><th>ID</th><th>Character</th><th>Garments</th><th>Scenes</th><th>Change reason</th></tr>` +
    project.costumes
      .map((c) => `<tr><td>${c.costume_id}</td><td>${c.character_id}</td><td>${esc(c.garments)}</td><td>${c.scenes.join(", ")}</td><td>${esc(c.change_reason)}</td></tr>`)
      .join("");
}

function paintGallery() {
  const pid = project.project_id;
  const fig = (v) => {
    const file = v.path.split(/[/\\]/).pop();
    const kind = v.kind === "character" ? "character_bible" : v.kind === "costume" ? "costume_bible" : "scene_keyframes";
    return `<figure><img src="/api/projects/${pid}/svg/${kind}/${file}?v=${v.seed}" alt="${v.title}"/><figcaption>${v.canonical_id}<br/>${esc(v.title)} · ${v.status}<br/><button class="ghost retry" data-asset="${v.asset_id}">Retry this asset</button></figcaption></figure>`;
  };
  $("galChars").innerHTML = project.visuals.filter((v) => v.kind === "character").map(fig).join("");
  $("galCost").innerHTML = project.visuals.filter((v) => v.kind === "costume").map(fig).join("");
  $("galScenes").innerHTML = project.visuals.filter((v) => v.kind === "scene").map(fig).join("");
  document.querySelectorAll("button.retry").forEach((btn) => {
    btn.onclick = async () => {
      const res = await fetch(`/api/projects/${pid}/assets/${btn.dataset.asset}/retry`, { method: "POST" });
      project = await res.json();
      paintGallery();
    };
  });
}

function paintExport() {
  const pid = project.project_id;
  $("dlScript").href = `/api/projects/${pid}/files/adapted_screenplay.pdf`;
  $("dlCont").href = `/api/projects/${pid}/files/continuity_report.pdf`;
  $("dlScenes").href = `/api/projects/${pid}/files/scene_breakdown.json`;
  $("contBox").innerHTML = project.continuity
    .map(
      (c) => `<p><b>${c.scene_id}</b> carrying=${JSON.stringify(c.carrying)} emotion=${JSON.stringify(c.emotion)}<br/><span class="muted">${(c.notes || []).join(" | ")}</span></p>`
    )
    .join("");
}

function esc(s) {
  return String(s || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

renderSteps();
loadCultures();
show("upload");
