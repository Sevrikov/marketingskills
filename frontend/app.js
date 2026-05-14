const state = {
  apiBase: initialApiBase(),
  tasks: [],
  selectedTaskId: null,
  registryLoaded: false,
  marketLoaded: false,
  opportunitiesLoaded: false,
  schedulerLoaded: false,
  settingsLoaded: false,
  busy: false,
};

const els = {
  apiBaseInput: document.querySelector("#apiBaseInput"),
  apiDocsBtn: document.querySelector("#apiDocsBtn"),
  healthLine: document.querySelector("#healthLine"),
  refreshBtn: document.querySelector("#refreshBtn"),
  syncSkillsBtn: document.querySelector("#syncSkillsBtn"),
  loadPromptsBtn: document.querySelector("#loadPromptsBtn"),
  createTaskForm: document.querySelector("#createTaskForm"),
  taskTypeInput: document.querySelector("#taskTypeInput"),
  topicInput: document.querySelector("#topicInput"),
  taskList: document.querySelector("#taskList"),
  detailTitle: document.querySelector("#detailTitle"),
  detailMeta: document.querySelector("#detailMeta"),
  qaStrip: document.querySelector("#qaStrip"),
  enqueueBtn: document.querySelector("#enqueueBtn"),
  notifyBtn: document.querySelector("#notifyBtn"),
  approveBtn: document.querySelector("#approveBtn"),
  rewriteBtn: document.querySelector("#rewriteBtn"),
  exportBtn: document.querySelector("#exportBtn"),
  draftsPanel: document.querySelector("#draftsPanel"),
  articleStudioPanel: document.querySelector("#articleStudioPanel"),
  productProfilePanel: document.querySelector("#productProfilePanel"),
  researchPanel: document.querySelector("#researchPanel"),
  eventsPanel: document.querySelector("#eventsPanel"),
  packagesPanel: document.querySelector("#packagesPanel"),
  marketPanel: document.querySelector("#marketPanel"),
  opportunitiesPanel: document.querySelector("#opportunitiesPanel"),
  schedulerPanel: document.querySelector("#schedulerPanel"),
  settingsPanel: document.querySelector("#settingsPanel"),
  registryPanel: document.querySelector("#registryPanel"),
  toast: document.querySelector("#toast"),
};

function apiUrl(path) {
  return `${state.apiBase.replace(/\/$/, "")}${path}`;
}

function initialApiBase() {
  const params = new URLSearchParams(window.location.search);
  return params.get("api") || "http://localhost:8000";
}

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const responseText = await response.text();
    try {
      const payload = JSON.parse(responseText);
      const detail = payload.detail ? JSON.stringify(payload.detail) : JSON.stringify(payload);
      throw new Error(detail || `HTTP ${response.status}`);
    } catch (error) {
      if (error instanceof SyntaxError) {
        throw new Error(responseText || `HTTP ${response.status}`);
      }
      throw error;
    }
  }
  return response.json();
}

function showToast(message) {
  els.toast.textContent = message;
  els.toast.classList.add("visible");
  window.setTimeout(() => els.toast.classList.remove("visible"), 2400);
}

function statusClass(status) {
  if (status === "waiting_approval" || status === "rewriting") return "review";
  if (status === "approved" || status === "done") return "ready";
  if (status === "failed" || status === "cancelled") return "failed";
  return "";
}

function statusLabel(status) {
  if (status === "waiting_approval") return "Ready for review";
  if (status === "approved") return "Approved";
  if (status === "rewriting") return "Rewrite requested";
  if (status === "failed") return "Failed";
  if (status === "queued") return "Queued";
  if (status === "draft") return "Draft";
  return status;
}

function selectedTask() {
  return state.tasks.find((task) => task.id === state.selectedTaskId) || null;
}

async function checkHealth() {
  try {
    const health = await request("/health");
    els.healthLine.textContent = `Backend: ${health.status} / ${health.env}`;
  } catch (error) {
    els.healthLine.textContent = "Backend: offline";
  }
}

async function loadTasks() {
  state.tasks = await request("/api/tasks");
  if (state.selectedTaskId && !state.tasks.some((task) => task.id === state.selectedTaskId)) {
    state.selectedTaskId = null;
  }
  if (!state.selectedTaskId && state.tasks.length) {
    state.selectedTaskId = state.tasks[0].id;
  }
  renderTasks();
  await renderSelectedTask();
}

function renderTasks() {
  if (!state.tasks.length) {
    els.taskList.innerHTML = `<div class="empty">The queue is empty.</div>`;
    return;
  }
  els.taskList.innerHTML = state.tasks
    .map((task) => {
      const title = escapeHtml(task.topic || task.product_id || task.id);
      const active = task.id === state.selectedTaskId ? " active" : "";
      return `
        <button class="task-row${active}" data-task-id="${task.id}" type="button">
          <strong>${title}</strong>
          <span class="status-line">
            <span class="badge ${statusClass(task.status)}">${statusLabel(task.status)}</span>
            <span class="badge">${task.task_type}</span>
            <span class="badge">${task.language}</span>
          </span>
        </button>
      `;
    })
    .join("");
}

async function renderSelectedTask() {
  const task = selectedTask();
  if (!task) {
    els.detailTitle.textContent = "No task selected";
    els.detailMeta.textContent = "Create a task or refresh the queue.";
    els.qaStrip.innerHTML = "";
    setActionState(null);
    renderEmptyPanels();
    return;
  }

  els.detailTitle.textContent = task.topic || task.product_id || task.id;
  els.detailMeta.textContent = `${task.task_type} / ${task.status} / ${
    task.current_step || "no step"
  }`;
  setActionState(task);
  renderQaStrip(task, null, null);

  const [drafts, research, events, packages, productProfile, articleCheckpoints, articleAssets] =
    await Promise.all([
      request(`/api/tasks/${task.id}/drafts`),
      request(`/api/tasks/${task.id}/research`),
      request(`/api/tasks/${task.id}/events`),
      request(`/api/tasks/${task.id}/packages`),
      loadProductProfile(task),
      loadArticleCheckpoints(task),
      loadArticleAssets(task),
    ]);
  const [publicationPreviews, mediaBriefs] = await Promise.all([
    loadPublicationPreviews(packages),
    loadMediaBriefs(packages),
  ]);
  renderDrafts(drafts);
  renderArticleStudio(
    task,
    drafts,
    research,
    packages,
    publicationPreviews,
    mediaBriefs,
    articleCheckpoints,
    articleAssets,
  );
  renderProductProfile(task, productProfile);
  renderResearch(research);
  renderEvents(events);
  renderPackages(packages, publicationPreviews, mediaBriefs);
  renderQaStrip(task, drafts, research);
  if (!state.registryLoaded) {
    await renderRegistry();
  }
  if (!state.marketLoaded) {
    await renderMarket();
  }
  if (!state.schedulerLoaded) {
    await renderScheduler();
  }
  if (!state.settingsLoaded) {
    await renderSettings();
  }
  if (!state.opportunitiesLoaded) {
    await renderOpportunities();
  }
}

function setActionState(task) {
  els.enqueueBtn.disabled = state.busy || !task || !["draft", "queued"].includes(task.status);
  els.notifyBtn.disabled = state.busy || !task || task.status !== "waiting_approval";
  els.approveBtn.disabled = state.busy || !task || task.status !== "waiting_approval";
  els.rewriteBtn.disabled = state.busy || !task || task.status !== "waiting_approval";
  els.exportBtn.disabled = state.busy || !task || task.status !== "approved";
}

function renderQaStrip(task, drafts, research) {
  const draftCount = drafts ? drafts.length : "-";
  const researchCount = research ? research.length : "-";
  const finalReady = drafts ? drafts.some((draft) => draft.kind === "final") : false;
  const qaState =
    task.status === "waiting_approval" && finalReady
      ? "Human review is ready"
      : statusLabel(task.status);
  els.qaStrip.innerHTML = `
    <span><strong>Status:</strong> ${escapeHtml(qaState)}</span>
    <span><strong>Research:</strong> ${researchCount}</span>
    <span><strong>Drafts:</strong> ${draftCount}</span>
    <span><strong>Step:</strong> ${escapeHtml(task.current_step || "none")}</span>
  `;
}

function renderDrafts(drafts) {
  if (!drafts.length) {
    els.draftsPanel.innerHTML = `<div class="empty">Drafts appear after worker processing.</div>`;
    return;
  }
  els.draftsPanel.innerHTML = sortDraftsForReview(drafts).map(renderRecord).join("");
}

async function loadProductProfile(task) {
  if (!task.product_id) {
    return { status: "no_product", profile: null };
  }
  const response = await fetch(apiUrl(`/api/products/${task.product_id}/content-profile`), {
    headers: { "Content-Type": "application/json" },
  });
  if (response.status === 404) {
    return { status: "missing", profile: null };
  }
  if (!response.ok) {
    throw new Error(`Product profile load failed: HTTP ${response.status}`);
  }
  return { status: "ready", profile: await response.json() };
}

async function loadArticleCheckpoints(task) {
  if (task.task_type !== "seo_article") {
    return [];
  }
  try {
    return await request(`/api/tasks/${task.id}/article-checkpoints`);
  } catch {
    return [];
  }
}

async function loadArticleAssets(task) {
  if (task.task_type !== "seo_article") {
    return [];
  }
  try {
    return await request(`/api/tasks/${task.id}/article-assets`);
  } catch {
    return [];
  }
}

function renderProductProfile(task, result) {
  if (!task.product_id) {
    els.productProfilePanel.innerHTML = `<div class="empty">Selected task is not linked to a product.</div>`;
    return;
  }
  if (!result.profile) {
    els.productProfilePanel.innerHTML = `
      <div class="empty">No structured product card yet.</div>
      <div class="toolbar">
        <button class="inline-action" data-generate-product-profile-id="${escapeHtml(
          task.product_id,
        )}" type="button">Generate product card</button>
      </div>
    `;
    return;
  }
  const profile = result.profile;
  els.productProfilePanel.innerHTML = renderRecord({
    kind: profile.status,
    title: profile.generated_title,
    body: [
      profile.short_description,
      "",
      profile.long_description,
      "",
      "SEO:",
      JSON.stringify(
        {
          seo_title: profile.seo_title,
          meta_description: profile.meta_description,
          alt_texts: profile.alt_texts_json,
        },
        null,
        2,
      ),
      "",
      "Specifications:",
      JSON.stringify(profile.specifications_json, null, 2),
      "",
      "FAQ:",
      JSON.stringify(profile.faq_json, null, 2),
      "",
      "Schema.org Product:",
      JSON.stringify(profile.schema_json, null, 2),
    ].join("\n"),
    model: profile.updated_at,
    actionHtml: `<button class="inline-action" data-generate-product-profile-id="${escapeHtml(
      task.product_id,
    )}" type="button">Regenerate</button><button class="inline-action" data-approve-product-profile-id="${escapeHtml(
      task.product_id,
    )}" type="button">Approve card</button>`,
  });
}

function sortDraftsForReview(drafts) {
  const order = { final: 0, critique: 1, initial: 2 };
  return [...drafts].sort((left, right) => {
    return (order[left.kind] ?? 9) - (order[right.kind] ?? 9);
  });
}

function renderResearch(reports) {
  if (!reports.length) {
    els.researchPanel.innerHTML = `<div class="empty">No research report yet.</div>`;
    return;
  }
  els.researchPanel.innerHTML = reports
    .map((report) => {
      const sources = report.sources_json
        .map((source) => `- ${source.title}${source.url ? ` (${source.url})` : ""}`)
        .join("\n");
      return renderRecord({
        kind: report.provider,
        title: report.title,
        body: `${report.markdown}\n\nSources:\n${sources}`,
        model: report.external_id || "local",
      });
    })
    .join("");
}

function renderEvents(events) {
  if (!events.length) {
    els.eventsPanel.innerHTML = `<div class="empty">No events yet.</div>`;
    return;
  }
  els.eventsPanel.innerHTML = events
    .map((event) =>
      renderRecord({
        kind: event.event_type,
        title: event.step || event.to_status || "event",
        body: JSON.stringify(event, null, 2),
        model: event.created_at,
      }),
    )
    .join("");
}

async function loadPublicationPreviews(packages) {
  const entries = await Promise.all(
    packages.map(async (item) => {
      const previews = await request(`/api/tasks/packages/${item.id}/publication-previews`);
      return [item.id, previews];
    }),
  );
  return Object.fromEntries(entries);
}

async function loadMediaBriefs(packages) {
  const entries = await Promise.all(
    packages.map(async (item) => {
      const briefs = await request(`/api/tasks/packages/${item.id}/media-briefs`);
      return [item.id, briefs];
    }),
  );
  return Object.fromEntries(entries);
}

function renderPackages(packages, publicationPreviews = {}, mediaBriefs = {}) {
  if (!packages.length) {
    els.packagesPanel.innerHTML = `<div class="empty">No export package yet.</div>`;
    return;
  }
  els.packagesPanel.innerHTML = packages
    .map((item) => {
      const previews = publicationPreviews[item.id] || [];
      const briefs = mediaBriefs[item.id] || [];
      const previewText = previews.length
        ? `\n\nPublication previews:\n${JSON.stringify(previews, null, 2)}`
        : "\n\nPublication previews: none";
      const mediaText = briefs.length
        ? `\n\nMedia briefs:\n${JSON.stringify(briefs, null, 2)}`
        : "\n\nMedia briefs: none";
      return renderRecord({
        kind: item.status,
        title: item.title,
        body: `${item.markdown}\n\nPackage JSON:\n${JSON.stringify(
          item.package_json,
          null,
          2,
        )}${previewText}${mediaText}`,
        model: item.slug,
        provider: item.package_type,
        actionHtml: `<button class="inline-action" data-publication-preview-id="${escapeHtml(
          item.id,
        )}" type="button">Prepare CMS payload</button><button class="inline-action" data-media-brief-id="${escapeHtml(
          item.id,
        )}" type="button">Prepare video brief</button>`,
      });
    })
    .join("");
}

function renderArticleStudio(
  task,
  drafts,
  research,
  packages,
  publicationPreviews = {},
  mediaBriefs = {},
  articleCheckpoints = [],
  articleAssets = [],
) {
  if (task.task_type !== "seo_article") {
    els.articleStudioPanel.innerHTML = `<div class="empty">Article Studio is available for SEO article tasks.</div>`;
    return;
  }

  const draft = activeArticleDraft(drafts);
  const rewriteDiff = buildFinalDraftDiff(drafts);
  const sources = extractResearchSources(research);
  const previews = Object.values(publicationPreviews).flat();
  const briefs = Object.values(mediaBriefs).flat();
  const checkpointByType = articleCheckpointMap(articleCheckpoints);
  const articleBrief = checkpointBodyValue(
    checkpointByType,
    task.id,
    "articleBrief",
    buildArticleBriefText(task, research),
  );
  const editorNotes = checkpointBodyValue(
    checkpointByType,
    task.id,
    "editorNotes",
    buildEditorNotesText(task, draft),
  );
  const imageBrief = checkpointBodyValue(
    checkpointByType,
    task.id,
    "imageBrief",
    buildImageBriefText(task, research),
  );
  const draftText = draft?.body || "Draft will appear after the worker reaches the writing step.";
  const packageStatus = packages.length ? `${packages.length} package(s)` : "No package";
  const cmsStatus = previews.length ? `${previews.length} CMS preview(s)` : "No CMS preview";
  const mediaStatus = briefs.length ? `${briefs.length} media brief(s)` : "No media brief";
  const assetStatus = articleAssets.length ? `${articleAssets.length} asset(s)` : "Pending";

  els.articleStudioPanel.innerHTML = `
    <section class="article-studio" data-article-studio-task-id="${escapeHtml(task.id)}">
      <div class="studio-header">
        <div>
          <h3>Article Studio</h3>
          <p>${escapeHtml(task.topic || task.product_id || task.id)}</p>
        </div>
        <div class="record-actions">
          <button class="inline-action" data-article-studio-save="${escapeHtml(
            task.id,
          )}" type="button">Save checkpoints</button>
          <button class="inline-action" data-article-studio-rewrite="${escapeHtml(
            task.id,
          )}" type="button" ${task.status === "waiting_approval" && draft ? "" : "disabled"}>
            Rewrite from notes
          </button>
          <button class="inline-action" data-article-studio-reset="${escapeHtml(
            task.id,
          )}" type="button">Reset generated</button>
        </div>
      </div>
      <div class="article-flow">
        ${renderArticleFlowStep(1, "Data pack", research.length ? "Ready" : "Pending")}
        ${renderArticleFlowStep(2, "Brief", articleBrief.trim() ? "Review" : "Pending")}
        ${renderArticleFlowStep(3, "Draft", draft ? "Ready" : "Pending")}
        ${renderArticleFlowStep(4, "Assets", assetStatus)}
        ${renderArticleFlowStep(5, "Package", packageStatus)}
        ${renderArticleFlowStep(6, "CMS", cmsStatus)}
      </div>
      <div class="checkpoint-grid">
        <article class="checkpoint-card">
          <div class="checkpoint-head">
            <strong>Research data pack</strong>
            <span class="badge ${research.length ? "ready" : ""}">${research.length} report(s)</span>
          </div>
          <pre class="studio-preview">${escapeHtml(buildResearchPreview(research, sources))}</pre>
        </article>
        <article class="checkpoint-card">
          <div class="checkpoint-head">
            <strong>Article brief</strong>
            <span class="badge review">editable</span>
          </div>
          <textarea class="studio-textarea" data-article-field="articleBrief">${escapeHtml(
            articleBrief,
          )}</textarea>
        </article>
        <article class="checkpoint-card wide">
          <div class="checkpoint-head">
            <strong>Draft preview</strong>
            <span class="badge ${draft ? "ready" : ""}">${escapeHtml(draft?.kind || "pending")}</span>
          </div>
          <pre class="studio-preview article-preview">${escapeHtml(draftText)}</pre>
        </article>
        <article class="checkpoint-card wide">
          <div class="checkpoint-head">
            <strong>Rewrite diff</strong>
            <div class="record-actions">
              ${renderDraftDecisionControls(task.id, rewriteDiff)}
              <span class="badge ${rewriteDiff.ready ? "ready" : ""}">${escapeHtml(
                rewriteDiff.label,
              )}</span>
            </div>
          </div>
          ${renderRewriteDiff(rewriteDiff)}
        </article>
        <article class="checkpoint-card">
          <div class="checkpoint-head">
            <strong>Editor checkpoint</strong>
            <span class="badge review">editable</span>
          </div>
          <textarea class="studio-textarea" data-article-field="editorNotes">${escapeHtml(
            editorNotes,
          )}</textarea>
        </article>
        <article class="checkpoint-card">
          <div class="checkpoint-head">
            <strong>Image and infographic brief</strong>
            <span class="badge review">editable</span>
          </div>
          <textarea class="studio-textarea" data-article-field="imageBrief">${escapeHtml(
            imageBrief,
          )}</textarea>
        </article>
        <article class="checkpoint-card wide">
          <div class="checkpoint-head">
            <strong>Image assets</strong>
            <div class="record-actions">
              <button class="inline-action" data-article-assets-generate="${escapeHtml(
                task.id,
              )}" type="button" ${draft ? "" : "disabled"}>Prepare image assets</button>
              <span class="badge ${articleAssets.length ? "ready" : ""}">${escapeHtml(
                assetStatus,
              )}</span>
            </div>
          </div>
          ${renderArticleAssets(task, articleAssets)}
        </article>
        <article class="checkpoint-card wide">
          <div class="checkpoint-head">
            <strong>Publication handoff</strong>
            <span class="badge">${escapeHtml(packageStatus)}</span>
          </div>
          <div class="asset-slot-list">
            <span><strong>CMS:</strong> ${escapeHtml(cmsStatus)}</span>
            <span><strong>Media:</strong> ${escapeHtml(mediaStatus)}</span>
            <span><strong>Sources:</strong> ${escapeHtml(sources.length)}</span>
            <span><strong>Status:</strong> ${escapeHtml(statusLabel(task.status))}</span>
          </div>
        </article>
      </div>
    </section>
  `;
}

function renderArticleFlowStep(index, title, status) {
  const ready = ["Ready", "Review"].includes(status) || /^\d+ /.test(status);
  return `
    <div class="article-flow-step ${ready ? "ready" : ""}">
      <span class="step-index">${index}</span>
      <strong>${escapeHtml(title)}</strong>
      <small>${escapeHtml(status)}</small>
    </div>
  `;
}

function activeArticleDraft(drafts) {
  return (
    drafts.find((draft) => draft.kind === "final") ||
    drafts.find((draft) => draft.kind === "initial") ||
    null
  );
}

function finalDraftsForDiff(drafts) {
  return drafts.filter((draft) => draft.kind === "final");
}

function buildFinalDraftDiff(drafts) {
  const finalDrafts = finalDraftsForDiff(drafts);
  if (finalDrafts.length < 2) {
    return {
      ready: false,
      label: "Needs 2 final drafts",
      lines: [],
    };
  }
  const previous = finalDrafts[finalDrafts.length - 2];
  const current = finalDrafts[finalDrafts.length - 1];
  return {
    ready: true,
    label: draftDecisionLabel(current),
    currentDraftId: current.id,
    decision: draftVersionDecision(current),
    lines: diffLines(previous.body || "", current.body || ""),
  };
}

function renderDraftDecisionControls(taskId, diff) {
  if (!diff.ready || !diff.currentDraftId) {
    return "";
  }
  const decision = diff.decision;
  const approvedDisabled = decision === "approved" ? "disabled" : "";
  const rejectedDisabled = decision === "rejected" ? "disabled" : "";
  return `
    <button class="inline-action" data-draft-version-decision="approved" data-task-id="${escapeHtml(
      taskId,
    )}" data-draft-id="${escapeHtml(diff.currentDraftId)}" type="button" ${approvedDisabled}>
      Accept rewrite
    </button>
    <button class="inline-action danger-action" data-draft-version-decision="rejected" data-task-id="${escapeHtml(
      taskId,
    )}" data-draft-id="${escapeHtml(diff.currentDraftId)}" type="button" ${rejectedDisabled}>
      Reject rewrite
    </button>
  `;
}

function draftDecisionLabel(draft) {
  const decision = draftVersionDecision(draft);
  if (decision === "approved") return "latest accepted";
  if (decision === "rejected") return "latest rejected";
  return "previous vs latest";
}

function draftVersionDecision(draft) {
  return draft?.metadata_json?.version_decision?.decision || null;
}

function renderRewriteDiff(diff) {
  if (!diff.ready) {
    return `<div class="empty compact">No rewrite diff yet.</div>`;
  }
  const rows = diff.lines
    .map(
      (line) => `
        <div class="diff-line ${escapeHtml(line.type)}">
          <span class="diff-prefix">${escapeHtml(diffPrefix(line.type))}</span>
          <span class="diff-text">${escapeHtml(line.text || " ")}</span>
        </div>
      `,
    )
    .join("");
  return `<div class="diff-view" aria-label="Rewrite diff">${rows}</div>`;
}

function renderArticleAssets(task, assets) {
  if (!assets.length) {
    return `
      <div class="empty compact">
        No assets prepared yet. Save the image brief, then prepare image assets from the final draft slots.
      </div>
    `;
  }
  return `
    <div class="article-assets-list">
      ${assets
        .map(
          (asset) => `
            <article class="article-asset-card ${escapeHtml(asset.status)}">
              <div class="article-asset-head">
                <div>
                  <strong>${escapeHtml(asset.slot)}</strong>
                  <small>${escapeHtml(asset.asset_type)} / ${escapeHtml(asset.storage_uri)}</small>
                </div>
                <span class="badge ${asset.status === "approved" ? "ready" : ""}">${escapeHtml(
                  asset.status,
                )}</span>
              </div>
              ${renderAssetVisual(asset)}
              <div class="asset-slot-list">
                <span><strong>Alt:</strong> ${escapeHtml(asset.alt_text)}</span>
                <span><strong>Caption:</strong> ${escapeHtml(asset.caption)}</span>
                <span><strong>Dimensions:</strong> ${escapeHtml(
                  asset.brief_json?.dimensions || "n/a",
                )}</span>
              </div>
              <pre class="asset-brief-preview">${escapeHtml(
                JSON.stringify(asset.brief_json || {}, null, 2),
              )}</pre>
              <div class="asset-upload-row">
                <input
                  data-article-asset-upload-uri="${escapeHtml(asset.id)}"
                  placeholder="Paste image URL, storage:// URI or data URI"
                  type="text"
                />
                <button class="inline-action" data-article-asset-upload="${escapeHtml(
                  asset.id,
                )}" data-task-id="${escapeHtml(task.id)}" type="button">Attach URL</button>
              </div>
              <div class="record-actions asset-actions">
                <button class="inline-action" data-article-asset-generate-image="${escapeHtml(
                  asset.id,
                )}" data-task-id="${escapeHtml(task.id)}" type="button">Generate mock image</button>
                <button class="inline-action" data-article-asset-status="approved" data-task-id="${escapeHtml(
                  task.id,
                )}" data-asset-id="${escapeHtml(asset.id)}" type="button" ${
                  asset.status === "approved" ? "disabled" : ""
                }>Approve asset</button>
                <button class="inline-action danger-action" data-article-asset-status="rejected" data-task-id="${escapeHtml(
                  task.id,
                )}" data-asset-id="${escapeHtml(asset.id)}" type="button" ${
                  asset.status === "rejected" ? "disabled" : ""
                }>Reject asset</button>
              </div>
            </article>
          `,
        )
        .join("")}
    </div>
  `;
}

function renderAssetVisual(asset) {
  if (assetHasRenderableUri(asset)) {
    return `
      <figure class="asset-rendered-preview ${escapeHtml(asset.status)}">
        <img src="${escapeHtml(asset.storage_uri)}" alt="${escapeHtml(asset.alt_text)}" />
        <figcaption>${escapeHtml(asset.caption)}</figcaption>
      </figure>
    `;
  }
  return `
    <div class="asset-visual-placeholder ${escapeHtml(asset.status)}">
      <div class="asset-loader"></div>
      <strong>${escapeHtml(assetVisualTitle(asset))}</strong>
      <small>${escapeHtml(assetVisualStatus(asset))}</small>
    </div>
  `;
}

function assetHasRenderableUri(asset) {
  const uri = String(asset.storage_uri || "");
  return Boolean(uri) && !uri.startsWith("mock://") && !uri.startsWith("storage://");
}

function assetVisualTitle(asset) {
  if (asset.asset_type === "infographic") {
    return "Infographic block";
  }
  return "Image block";
}

function assetVisualStatus(asset) {
  if (asset.status === "approved" && String(asset.storage_uri || "").startsWith("mock://")) {
    return "Approved, waiting for real image upload or generator output";
  }
  if (asset.status === "approved") {
    return "Approved and ready for CMS placement";
  }
  if (asset.status === "rejected") {
    return "Rejected, regenerate or revise the brief";
  }
  return "Generated as empty online slot, waiting for review/upload";
}

function diffPrefix(type) {
  if (type === "added") return "+";
  if (type === "removed") return "-";
  return " ";
}

function diffLines(previousText, currentText) {
  const previousLines = splitDiffLines(previousText);
  const currentLines = splitDiffLines(currentText);
  const lcs = Array.from({ length: previousLines.length + 1 }, () =>
    Array(currentLines.length + 1).fill(0),
  );
  for (let i = previousLines.length - 1; i >= 0; i -= 1) {
    for (let j = currentLines.length - 1; j >= 0; j -= 1) {
      lcs[i][j] =
        previousLines[i] === currentLines[j]
          ? lcs[i + 1][j + 1] + 1
          : Math.max(lcs[i + 1][j], lcs[i][j + 1]);
    }
  }

  const result = [];
  let i = 0;
  let j = 0;
  while (i < previousLines.length && j < currentLines.length) {
    if (previousLines[i] === currentLines[j]) {
      result.push({ type: "same", text: previousLines[i] });
      i += 1;
      j += 1;
    } else if (lcs[i + 1][j] >= lcs[i][j + 1]) {
      result.push({ type: "removed", text: previousLines[i] });
      i += 1;
    } else {
      result.push({ type: "added", text: currentLines[j] });
      j += 1;
    }
  }
  while (i < previousLines.length) {
    result.push({ type: "removed", text: previousLines[i] });
    i += 1;
  }
  while (j < currentLines.length) {
    result.push({ type: "added", text: currentLines[j] });
    j += 1;
  }
  return result;
}

function splitDiffLines(text) {
  const lines = String(text || "").split(/\r?\n/);
  return lines.length ? lines : [""];
}

function buildArticleBriefText(task, research) {
  const sources = extractResearchSources(research).slice(0, 6);
  const painLine = extractPainLine(research);
  return [
    "ARTICLE BRIEF",
    `Topic: ${task.topic || task.product_id || task.id}`,
    `Language: ${task.language || "ru"}`,
    "Intent: answer buyer questions, compare options, and connect facts to the main buyer pain.",
    `Primary pain: ${painLine}`,
    "",
    "Required structure:",
    "1. H1 with product/group/search intent.",
    "2. Short problem-led intro.",
    "3. What the buyer should compare before purchase.",
    "4. Product/group facts and selection criteria.",
    "5. Competitor or alternative comparison where facts exist.",
    "6. FAQ for AEO snippets.",
    "7. CTA and next step.",
    "",
    "Asset slots:",
    "- {{image:hero}} product/use-case visual.",
    "- {{infographic:comparison}} controlled overlay with facts and source notes.",
    "- {{image:detail}} detail or scenario visual.",
    "",
    "Sources:",
    sources.length
      ? sources.map((source) => `- ${source.title}${source.url ? `: ${source.url}` : ""}`).join("\n")
      : "- Research sources pending.",
    "",
    "Forbidden claims:",
    "- Do not invent prices, ratings, warranty terms, certifications, or availability.",
    "- Do not state medical, legal, or safety guarantees without cited evidence.",
    "- Do not let generated images create factual labels, tables, logos, or prices.",
  ].join("\n");
}

function buildEditorNotesText(task, draft) {
  return [
    "EDITOR CHECKPOINT",
    `Task: ${task.id}`,
    `Current status: ${statusLabel(task.status)}`,
    "",
    "Operator notes:",
    "- ",
    "",
    "Rewrite request:",
    "- ",
    "",
    "Approval checklist:",
    `- Draft present: ${draft ? "yes" : "no"}`,
    "- Pain/problem is explicit and supported.",
    "- Sources are enough for factual claims.",
    "- Image slots match article logic.",
    "- No unsupported prices, ratings, or guarantees.",
  ].join("\n");
}

function buildImageBriefText(task, research) {
  const painLine = extractPainLine(research);
  return [
    "IMAGE AND INFOGRAPHIC BRIEF",
    `Article: ${task.topic || task.product_id || task.id}`,
    `Buyer pain to visualize: ${painLine}`,
    "",
    "Slots:",
    "1. {{image:hero}}",
    "   Purpose: show the product/group in the buyer's real use context.",
    "   Format: 16:9, clean ecommerce editorial style, no factual text overlays.",
    "   Alt text: describe product, context, and buyer problem.",
    "",
    "2. {{infographic:comparison}}",
    "   Purpose: compare choice criteria, tradeoffs, and fit by use case.",
    "   Format: HTML/SVG or designed layout with controlled text overlays.",
    "   Data rule: charts, scores, prices, tables, source notes must come from structured data.",
    "",
    "3. {{image:detail}}",
    "   Purpose: show material/detail/port/scale/use-case angle.",
    "   Format: 4:3 or 1:1, no invented labels.",
    "",
    "4. {{image:social_cover}}",
    "   Purpose: article and Shorts cover.",
    "   Format: 9:16 safe-area composition, title text rendered by layout layer.",
    "",
    "QA:",
    "- Every asset has purpose, dimensions, alt text, caption, source note, and approval status.",
    "- Bitmap generation must not be trusted for factual tables or exact numbers.",
  ].join("\n");
}

function buildResearchPreview(research, sources) {
  if (!research.length) {
    return "Research report pending.";
  }
  const report = research[0];
  const sourceLines = sources
    .slice(0, 8)
    .map((source) => `- ${source.title}${source.url ? ` (${source.url})` : ""}`)
    .join("\n");
  return [
    report.title || "Research report",
    "",
    trimText(report.markdown || "", 1800),
    "",
    "Sources:",
    sourceLines || "- none",
  ].join("\n");
}

function extractPainLine(research) {
  const report = research[0];
  if (!report?.markdown) {
    return "Confirm the main buyer problem during research.";
  }
  const line =
    report.markdown
      .split("\n")
      .map((item) => item.replace(/^#+\s*/, "").trim())
      .find((item) => item.length > 24 && !item.toLowerCase().startsWith("sources")) || "";
  return trimText(line, 220);
}

function extractResearchSources(research) {
  return research.flatMap((report) =>
    Array.isArray(report.sources_json)
      ? report.sources_json.map((source) => ({
          title: source.title || source.url || "source",
          url: source.url || "",
        }))
      : [],
  );
}

function articleStudioStorageKey(taskId, field) {
  return `articleStudio:${taskId}:${field}`;
}

function articleCheckpointTypeByField(field) {
  return {
    articleBrief: "article_brief",
    editorNotes: "editor_notes",
    imageBrief: "image_brief",
  }[field];
}

function articleCheckpointMap(checkpoints) {
  return Object.fromEntries(
    checkpoints.map((checkpoint) => [checkpoint.checkpoint_type, checkpoint]),
  );
}

function checkpointBodyValue(checkpointByType, taskId, field, fallback) {
  const checkpointType = articleCheckpointTypeByField(field);
  const checkpoint = checkpointType ? checkpointByType[checkpointType] : null;
  return checkpoint?.body_markdown || getStoredArticleStudioValue(taskId, field, fallback);
}

function getStoredArticleStudioValue(taskId, field, fallback) {
  try {
    return window.localStorage.getItem(articleStudioStorageKey(taskId, field)) || fallback;
  } catch {
    return fallback;
  }
}

async function saveArticleStudioCheckpoints(taskId) {
  try {
    await persistArticleStudioCheckpoints(taskId);
    showToast("Article checkpoints saved to backend");
    await renderSelectedTask();
  } catch (error) {
    showToast(`Backend save failed, local copy kept: ${error.message}`);
  }
}

async function persistArticleStudioCheckpoints(taskId) {
  const fields = [...els.articleStudioPanel.querySelectorAll("[data-article-field]")];
  fields.forEach((field) => {
    window.localStorage.setItem(
      articleStudioStorageKey(taskId, field.dataset.articleField),
      field.value,
    );
  });
  await Promise.all(
    fields.map((field) =>
      request(
        `/api/tasks/${taskId}/article-checkpoints/${articleCheckpointTypeByField(
          field.dataset.articleField,
        )}`,
        {
          method: "PUT",
          body: JSON.stringify({
            body_markdown: field.value || " ",
            status: "draft",
            reviewer: "operator",
            metadata_json: {
              source: "article_studio",
              field: field.dataset.articleField,
            },
          }),
        },
      ),
    ),
  );
}

async function rewriteArticleFromCheckpoints(taskId) {
  await runAction("Article rewrite generated", async () => {
    await persistArticleStudioCheckpoints(taskId);
    const draft = await request(`/api/tasks/${taskId}/rewrite-from-checkpoints`, {
      method: "POST",
    });
    return `Rewrite ready: ${draft.kind}`;
  });
}

async function prepareArticleAssets(taskId) {
  await runAction("Article assets prepared", async () => {
    await persistArticleStudioCheckpoints(taskId);
    const assets = await request(`/api/tasks/${taskId}/article-assets/generate`, {
      method: "POST",
    });
    return `Prepared ${assets.length} asset(s)`;
  });
}

async function updateArticleAssetStatus(taskId, assetId, status) {
  const label = status === "approved" ? "Asset approved" : "Asset rejected";
  await runAction(label, async () => {
    const asset = await request(`/api/tasks/${taskId}/article-assets/${assetId}/status`, {
      method: "POST",
      body: JSON.stringify({
        status,
        reviewer: "operator",
        comment: `${label} in Article Studio.`,
      }),
    });
    return `${label}: ${asset.slot}`;
  });
}

async function generateArticleAssetImage(taskId, assetId) {
  await runAction("Mock image generated", async () => {
    const asset = await request(`/api/tasks/${taskId}/article-assets/${assetId}/generate-image`, {
      method: "POST",
      body: JSON.stringify({
        reviewer: "operator",
        comment: "Generated through Article Studio mock image provider.",
      }),
    });
    return `Image ready for review: ${asset.slot}`;
  });
}

async function uploadArticleAssetUri(taskId, assetId) {
  const input = els.articleStudioPanel.querySelector(
    `[data-article-asset-upload-uri="${cssEscape(assetId)}"]`,
  );
  const storageUri = input?.value?.trim();
  if (!storageUri) {
    showToast("Paste image URL first");
    return;
  }
  await runAction("Image URL attached", async () => {
    const asset = await request(`/api/tasks/${taskId}/article-assets/${assetId}/upload`, {
      method: "POST",
      body: JSON.stringify({
        storage_uri: storageUri,
        reviewer: "operator",
        comment: "Attached image URI through Article Studio.",
      }),
    });
    return `Image attached: ${asset.slot}`;
  });
}

async function setDraftVersionDecision(taskId, draftId, decision) {
  const label = decision === "approved" ? "Rewrite accepted" : "Rewrite rejected";
  await runAction(label, async () => {
    const draft = await request(`/api/tasks/${taskId}/drafts/${draftId}/version-decision`, {
      method: "POST",
      body: JSON.stringify({
        decision,
        reviewer: "operator",
        comment:
          decision === "approved"
            ? "Rewrite accepted in Article Studio."
            : "Rewrite rejected in Article Studio.",
      }),
    });
    return `${label}: ${draft.kind}`;
  });
}

async function resetArticleStudioCheckpoints(taskId) {
  try {
    const fields = ["articleBrief", "editorNotes", "imageBrief"];
    fields.forEach((field) => {
      window.localStorage.removeItem(articleStudioStorageKey(taskId, field));
    });
    await Promise.all(fields.map((field) => deleteArticleCheckpoint(taskId, field)));
    showToast("Article checkpoints reset");
    await renderSelectedTask();
  } catch (error) {
    showToast(`Reset failed: ${error.message}`);
  }
}

async function deleteArticleCheckpoint(taskId, field) {
  const checkpointType = articleCheckpointTypeByField(field);
  if (!checkpointType) return;
  const response = await fetch(apiUrl(`/api/tasks/${taskId}/article-checkpoints/${checkpointType}`), {
    method: "DELETE",
  });
  if (![204, 404].includes(response.status)) {
    throw new Error(`HTTP ${response.status}`);
  }
}

function trimText(value, maxLength) {
  const text = String(value || "").trim();
  return text.length > maxLength ? `${text.slice(0, maxLength - 1)}...` : text;
}

function cssEscape(value) {
  if (window.CSS?.escape) {
    return window.CSS.escape(value);
  }
  return String(value).replace(/"/g, '\\"');
}

async function renderMarket() {
  try {
    const [groups, sources, trends, policies, batches, changes] = await Promise.all([
      request("/api/price-monitor/groups"),
      request("/api/price-monitor/sources"),
      request("/api/price-monitor/trend-events"),
      request("/api/price-monitor/notification-policies"),
      request("/api/price-monitor/trend-digests/batches"),
      request("/api/price-monitor/changes"),
    ]);
    const indexEntries = await Promise.all(
      groups.slice(0, 12).map(async (group) => {
        const indexes = await request(`/api/price-monitor/groups/${group.id}/market-indexes`);
        return [group.id, indexes[0] || null];
      }),
    );
    state.marketLoaded = true;
    const latestIndexByGroup = Object.fromEntries(indexEntries);
    els.marketPanel.innerHTML = [
      renderMarketActions(groups),
      renderMarketMetrics(groups, sources, trends, batches, changes),
      renderMarketForms(groups),
      renderMarketGroups(groups, latestIndexByGroup),
      renderMarketTrends(trends),
      renderMarketPolicies(policies),
      renderMarketBatches(batches),
      renderMarketSources(sources),
    ].join("");
  } catch (error) {
    els.marketPanel.innerHTML = `<div class="empty">Market data failed: ${escapeHtml(
      error.message,
    )}</div>`;
  }
}

function renderMarketActions(groups) {
  const groupButtons = groups
    .slice(0, 6)
    .map(
      (group) =>
        `<button class="inline-action" data-build-market-index-id="${escapeHtml(
          group.id,
        )}" type="button">Index: ${escapeHtml(group.name)}</button>`,
    )
    .join("");
  return `
    <div class="workspace-actions">
      <button class="inline-action" data-market-action="run-monitor" type="button">Run monitor</button>
      <button class="inline-action" data-market-action="evaluate-policies" type="button">Evaluate policies</button>
      <button class="inline-action" data-market-action="send-alerts" type="button">Send alerts</button>
      <button class="inline-action" data-market-action="run-digest" type="button">Run digest</button>
      ${groupButtons}
    </div>
  `;
}

function renderMarketMetrics(groups, sources, trends, batches, changes) {
  const readyAlerts = trends.filter((item) => item.notify_status === "ready_immediate").length;
  const queuedDigest = trends.filter((item) => item.notify_status === "queued_digest").length;
  return `
    <div class="metric-grid">
      ${renderMetric("Groups", groups.length)}
      ${renderMetric("Sources", sources.length)}
      ${renderMetric("Trends", trends.length)}
      ${renderMetric("Ready alerts", readyAlerts)}
      ${renderMetric("Digest queue", queuedDigest)}
      ${renderMetric("Changes", changes.length)}
      ${renderMetric("Batches", batches.length)}
    </div>
  `;
}

function renderMarketForms(groups) {
  const groupOptions = [
    `<option value="">No group</option>`,
    ...groups.map((group) => `<option value="${escapeHtml(group.id)}">${escapeHtml(group.name)}</option>`),
  ].join("");
  return `
    <div class="workspace-grid">
      <form class="mini-form" data-market-form="group">
        <h3>New group</h3>
        <input name="name" placeholder="Group name" required />
        <input name="category" placeholder="Category" />
        <input name="brand" placeholder="Brand" />
        <input name="keywords" placeholder="Keywords" />
        <button type="submit">Create group</button>
      </form>
      <form class="mini-form" data-market-form="source">
        <h3>New source</h3>
        <select name="price_group_id">${groupOptions}</select>
        <input name="url" placeholder="Product URL" required />
        <input name="label" placeholder="Label" />
        <input name="competitor_name" placeholder="Competitor" />
        <input name="expected_currency" placeholder="Currency" maxlength="8" />
        <button type="submit">Add source</button>
      </form>
      <form class="mini-form" data-market-form="policy">
        <h3>New policy</h3>
        <input name="name" placeholder="Policy name" required />
        <select name="delivery_mode">
          <option value="digest">Digest</option>
          <option value="immediate">Immediate</option>
          <option value="stored_only">Stored only</option>
        </select>
        <select name="min_severity">
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="critical">Critical</option>
          <option value="low">Low</option>
        </select>
        <input name="min_affected_sources" type="number" min="1" value="3" />
        <input name="min_percent_change" type="number" min="0" step="0.1" value="10.0" />
        <button type="submit">Create policy</button>
      </form>
    </div>
  `;
}

function renderMarketGroups(groups, latestIndexByGroup) {
  if (!groups.length) {
    return `<div class="empty">No market groups yet.</div>`;
  }
  const rows = groups
    .map((group) => {
      const index = latestIndexByGroup[group.id];
      return `
        <tr>
          <td>${escapeHtml(group.name)}</td>
          <td>${escapeHtml(group.category || "-")}</td>
          <td>${escapeHtml(group.brand || "-")}</td>
          <td>${index ? escapeHtml(index.avg_price || "-") : "-"}</td>
          <td>${index ? escapeHtml(index.source_count) : "-"}</td>
          <td>${formatDate(index?.created_at)}</td>
        </tr>
      `;
    })
    .join("");
  return renderTable("Groups and latest indexes", ["Group", "Category", "Brand", "Avg", "Sources", "Indexed"], rows);
}

function renderMarketTrends(trends) {
  if (!trends.length) {
    return `<div class="empty">No trend events yet.</div>`;
  }
  const rows = trends
    .slice(0, 20)
    .map(
      (trend) => `
        <tr>
          <td><span class="badge ${trend.severity === "high" || trend.severity === "critical" ? "failed" : "review"}">${escapeHtml(
            trend.severity,
          )}</span></td>
          <td>${escapeHtml(trend.event_type)}</td>
          <td>${escapeHtml(trend.percent_change || "-")}</td>
          <td>${escapeHtml(trend.affected_sources_count)}</td>
          <td>${escapeHtml(trend.notify_status)}</td>
          <td>${escapeHtml(trend.summary)}</td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Trend events", ["Severity", "Type", "Change %", "Sources", "Notify", "Summary"], rows);
}

function renderMarketPolicies(policies) {
  if (!policies.length) {
    return `<div class="empty">No notification policies yet.</div>`;
  }
  const rows = policies
    .map(
      (policy) => `
        <tr>
          <td>${escapeHtml(policy.name)}</td>
          <td>${escapeHtml(policy.delivery_mode)}</td>
          <td>${escapeHtml(policy.min_severity)}</td>
          <td>${escapeHtml(policy.min_affected_sources)}</td>
          <td>${escapeHtml(policy.min_percent_change)}</td>
          <td>${escapeHtml(policy.status)}</td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Notification policies", ["Name", "Mode", "Severity", "Sources", "Change %", "Status"], rows);
}

function renderMarketBatches(batches) {
  if (!batches.length) {
    return `<div class="empty">No market digest batches yet.</div>`;
  }
  const rows = batches
    .slice(0, 12)
    .map(
      (batch) => `
        <tr>
          <td>${escapeHtml(batch.status)}</td>
          <td>${escapeHtml(batch.event_count)}</td>
          <td>${escapeHtml(batch.title)}</td>
          <td>${formatDate(batch.created_at)}</td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Digest batches", ["Status", "Events", "Title", "Created"], rows);
}

function renderMarketSources(sources) {
  if (!sources.length) {
    return `<div class="empty">No monitored sources yet.</div>`;
  }
  const rows = sources
    .slice(0, 30)
    .map(
      (source) => `
        <tr>
          <td>${escapeHtml(source.label || source.competitor_name || "source")}</td>
          <td>${escapeHtml(source.last_price || "-")} ${escapeHtml(source.last_currency || "")}</td>
          <td>${escapeHtml(source.last_availability || "-")}</td>
          <td>${escapeHtml(source.last_status || "-")}</td>
          <td>${formatDate(source.next_check_at)}</td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Monitored sources", ["Source", "Price", "Availability", "Status", "Next check"], rows);
}

async function renderScheduler() {
  try {
    const [jobs, runs] = await Promise.all([
      request("/api/scheduler/jobs"),
      request("/api/scheduler/runs"),
    ]);
    state.schedulerLoaded = true;
    els.schedulerPanel.innerHTML = [
      renderSchedulerActions(jobs),
      renderSchedulerMetrics(jobs, runs),
      renderSchedulerJobs(jobs),
      renderSchedulerRuns(runs),
    ].join("");
  } catch (error) {
    els.schedulerPanel.innerHTML = `<div class="empty">Scheduler data failed: ${escapeHtml(
      error.message,
    )}</div>`;
  }
}

async function renderOpportunities() {
  try {
    const [opportunities, products, groups] = await Promise.all([
      request("/api/content-opportunities"),
      request("/api/products"),
      request("/api/price-monitor/groups"),
    ]);
    state.opportunitiesLoaded = true;
    els.opportunitiesPanel.innerHTML = [
      renderOpportunityForm(products, groups),
      renderOpportunityMetrics(opportunities),
      renderOpportunityTable(opportunities),
    ].join("");
  } catch (error) {
    els.opportunitiesPanel.innerHTML = `<div class="empty">Opportunities data failed: ${escapeHtml(
      error.message,
    )}</div>`;
  }
}

function renderOpportunityForm(products, groups) {
  const productOptions = [
    `<option value="">No product</option>`,
    ...products.map((product) => `<option value="${escapeHtml(product.id)}">${escapeHtml(product.title)}</option>`),
  ].join("");
  const groupOptions = [
    `<option value="">No group</option>`,
    ...groups.map((group) => `<option value="${escapeHtml(group.id)}">${escapeHtml(group.name)}</option>`),
  ].join("");
  return `
    <form class="mini-form opportunity-form" data-opportunity-form="discover">
      <h3>Discover article topics</h3>
      <select name="product_id">${productOptions}</select>
      <select name="price_group_id">${groupOptions}</select>
      <input name="brand" placeholder="Brand or trademark" />
      <input name="category" placeholder="Category" />
      <input name="query" placeholder="Extra research query" />
      <input name="market" placeholder="Market, e.g. UA" />
      <input name="limit" type="number" min="1" max="20" value="6" />
      <button type="submit">Discover topics</button>
    </form>
  `;
}

function renderOpportunityMetrics(opportunities) {
  const newItems = opportunities.filter((item) => item.status === "new").length;
  const tasks = opportunities.filter((item) => item.status === "task_created").length;
  const avgPriority = opportunities.length
    ? Math.round(
        opportunities.reduce((sum, item) => sum + Number(item.priority_score || 0), 0) /
          opportunities.length,
      )
    : 0;
  return `
    <div class="metric-grid">
      ${renderMetric("Opportunities", opportunities.length)}
      ${renderMetric("New", newItems)}
      ${renderMetric("Tasks", tasks)}
      ${renderMetric("Avg priority", avgPriority)}
    </div>
  `;
}

function renderOpportunityTable(opportunities) {
  if (!opportunities.length) {
    return `<div class="empty">No article topic opportunities yet.</div>`;
  }
  const rows = opportunities
    .slice(0, 40)
    .map(
      (item) => `
        <tr>
          <td>
            <strong>${escapeHtml(item.title)}</strong>
            <small>${escapeHtml(item.reason)}</small>
          </td>
          <td>${escapeHtml(item.scope_type)}</td>
          <td>${escapeHtml(item.intent)}</td>
          <td>${escapeHtml(item.priority_score)}</td>
          <td><span class="badge ${item.status === "task_created" ? "ready" : ""}">${escapeHtml(
            item.status,
          )}</span></td>
          <td>${escapeHtml((item.sources_json || []).length)}</td>
          <td>
            ${
              item.created_task_id
                ? `<span class="badge ready">task created</span>`
                : `<button class="inline-action" data-opportunity-create-task="${escapeHtml(
                    item.id,
                  )}" type="button">Create article task</button>`
            }
          </td>
        </tr>
      `,
    )
    .join("");
  return renderTable(
    "Article topic opportunities",
    ["Topic", "Scope", "Intent", "Score", "Status", "Sources", ""],
    rows,
  );
}

function renderSchedulerActions() {
  return `
    <div class="workspace-actions">
      <button class="inline-action" data-scheduler-action="run-due" type="button">Run due jobs</button>
      <button class="inline-action" data-scheduler-action="refresh" type="button">Refresh scheduler</button>
    </div>
  `;
}

function renderSchedulerMetrics(jobs, runs) {
  const active = jobs.filter((job) => job.is_active && job.status === "active").length;
  const failed = runs.filter((run) => run.status === "failed").length;
  return `
    <div class="metric-grid">
      ${renderMetric("Jobs", jobs.length)}
      ${renderMetric("Active", active)}
      ${renderMetric("Runs", runs.length)}
      ${renderMetric("Failed runs", failed)}
    </div>
  `;
}

function renderSchedulerJobs(jobs) {
  if (!jobs.length) {
    return `<div class="empty">No scheduled jobs yet.</div>`;
  }
  const rows = jobs
    .map(
      (job) => `
        <tr>
          <td>
            <strong>${escapeHtml(job.name)}</strong>
            <small>${escapeHtml(job.job_key)}</small>
          </td>
          <td>${escapeHtml(job.job_type)}</td>
          <td>${escapeHtml(job.interval_minutes)}m</td>
          <td>${formatDate(job.next_run_at)}</td>
          <td><span class="badge ${job.last_status === "failed" ? "failed" : ""}">${escapeHtml(
            job.last_status || "never",
          )}</span></td>
          <td><button class="inline-action" data-scheduler-run-now="${escapeHtml(
            job.job_key,
          )}" type="button">Run now</button></td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Scheduled jobs", ["Job", "Type", "Interval", "Next", "Last", ""], rows);
}

function renderSchedulerRuns(runs) {
  if (!runs.length) {
    return `<div class="empty">No scheduler runs yet.</div>`;
  }
  const rows = runs
    .slice(0, 30)
    .map(
      (run) => `
        <tr>
          <td>${escapeHtml(run.job_key)}</td>
          <td>${escapeHtml(run.trigger)}</td>
          <td><span class="badge ${run.status === "failed" ? "failed" : run.status === "succeeded" ? "ready" : ""}">${escapeHtml(
            run.status,
          )}</span></td>
          <td>${formatDate(run.started_at)}</td>
          <td>${escapeHtml(shortJson(run.summary_json || run.error_message || {}))}</td>
        </tr>
      `,
    )
    .join("");
  return renderTable("Run history", ["Job", "Trigger", "Status", "Started", "Summary"], rows);
}

async function renderSettings() {
  try {
    const settings = await request("/api/runtime-settings");
    state.settingsLoaded = true;
    els.settingsPanel.innerHTML = `
      <form class="settings-form" data-runtime-settings-form>
        <div class="studio-header">
          <div>
            <h3>API Settings</h3>
            <p>Providers, models and write-only API keys for local runtime tests.</p>
          </div>
          <div class="record-actions">
            <button class="inline-action" type="submit">Save settings</button>
            <button class="inline-action" data-settings-refresh type="button">Refresh</button>
          </div>
        </div>
        <div class="settings-grid">
          ${settings.sections
            .map((section) => renderSettingsSection(section, settings.fields))
            .join("")}
        </div>
      </form>
    `;
  } catch (error) {
    els.settingsPanel.innerHTML = `<div class="empty">Settings load failed: ${escapeHtml(
      error.message,
    )}</div>`;
  }
}

function renderSettingsSection(section, fields) {
  const sectionFields = fields.filter((field) => field.section === section);
  return `
    <section class="settings-section">
      <h3>${escapeHtml(section)}</h3>
      ${sectionFields.map(renderSettingsField).join("")}
    </section>
  `;
}

function renderSettingsField(field) {
  const status = field.configured ? "configured" : "not configured";
  const input = settingsInput(field);
  return `
    <label class="settings-field">
      <span>
        <strong>${escapeHtml(field.label)}</strong>
        <small>${escapeHtml(field.description || status)}</small>
      </span>
      ${input}
      <em>${escapeHtml(field.kind === "secret" ? field.masked_value || status : status)}</em>
    </label>
  `;
}

function settingsInput(field) {
  const key = escapeHtml(field.key);
  if (field.kind === "select") {
    const value = String(field.value ?? "");
    return `
      <select data-runtime-setting="${key}" data-setting-kind="${escapeHtml(field.kind)}">
        ${field.options
          .map(
            (option) =>
              `<option value="${escapeHtml(option)}" ${option === value ? "selected" : ""}>${escapeHtml(
                option,
              )}</option>`,
          )
          .join("")}
      </select>
    `;
  }
  if (field.kind === "boolean") {
    return `
      <input data-runtime-setting="${key}" data-setting-kind="${escapeHtml(
        field.kind,
      )}" type="checkbox" ${field.value ? "checked" : ""} />
    `;
  }
  if (field.kind === "secret") {
    return `
      <input data-runtime-setting="${key}" data-setting-kind="${escapeHtml(
        field.kind,
      )}" type="password" autocomplete="off" placeholder="${
        field.configured ? "configured, paste to replace" : "paste key/token"
      }" />
    `;
  }
  return `
    <input data-runtime-setting="${key}" data-setting-kind="${escapeHtml(
      field.kind,
    )}" type="text" value="${escapeHtml(field.value ?? "")}" />
  `;
}

async function submitRuntimeSettings(form) {
  const values = {};
  form.querySelectorAll("[data-runtime-setting]").forEach((input) => {
    const key = input.dataset.runtimeSetting;
    if (input.dataset.settingKind === "secret" && !input.value.trim()) {
      return;
    }
    values[key] = input.type === "checkbox" ? input.checked : input.value;
  });
  await runAction("Runtime settings saved", async () => {
    await request("/api/runtime-settings", {
      method: "PUT",
      body: JSON.stringify({ values }),
    });
  });
  state.settingsLoaded = false;
  await renderSettings();
}

async function renderRegistry() {
  const [skills, prompts] = await Promise.all([
    request("/api/skills?status="),
    request("/api/prompts"),
  ]);
  state.registryLoaded = true;
  els.registryPanel.innerHTML = `
    <div class="record">
      <div class="record-head"><strong>Skills</strong><span>${skills.length}</span></div>
      <pre class="record-body">${escapeHtml(JSON.stringify(skills, null, 2))}</pre>
    </div>
    <div class="record">
      <div class="record-head"><strong>Prompts</strong><span>${prompts.length}</span></div>
      <pre class="record-body">${escapeHtml(JSON.stringify(prompts, null, 2))}</pre>
    </div>
  `;
}

function renderRecord(record) {
  const recordClass = record.kind === "final" || record.kind === "critique" ? ` ${record.kind}` : "";
  return `
    <article class="record${recordClass}">
      <div class="record-head">
        <div>
          <strong>${escapeHtml(record.title || record.kind)}</strong>
          <small>${escapeHtml(record.prompt_template_key || record.provider || "")}</small>
        </div>
        <div class="record-actions">
          <span class="badge">${escapeHtml(record.kind)} / ${escapeHtml(record.model || "")}</span>
          ${record.actionHtml || ""}
        </div>
      </div>
      <pre class="record-body">${escapeHtml(record.body)}</pre>
    </article>
  `;
}

function renderMetric(label, value) {
  return `
    <div class="metric">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </div>
  `;
}

function renderTable(title, headers, rows) {
  return `
    <section class="data-section">
      <h3>${escapeHtml(title)}</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>${headers.map((header) => `<th>${escapeHtml(header)}</th>`).join("")}</tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      </div>
    </section>
  `;
}

function formatDate(value) {
  if (!value) return "-";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "-";
  return date.toLocaleString(undefined, {
    month: "short",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function shortJson(value) {
  const text = typeof value === "string" ? value : JSON.stringify(value);
  if (!text || text === "{}") return "-";
  return text.length > 140 ? `${text.slice(0, 139)}…` : text;
}

function renderEmptyPanels() {
  els.draftsPanel.innerHTML = `<div class="empty">No selected task.</div>`;
  els.articleStudioPanel.innerHTML = `<div class="empty">No selected task.</div>`;
  els.productProfilePanel.innerHTML = `<div class="empty">No selected task.</div>`;
  els.researchPanel.innerHTML = `<div class="empty">No selected task.</div>`;
  els.eventsPanel.innerHTML = `<div class="empty">No selected task.</div>`;
  els.packagesPanel.innerHTML = `<div class="empty">No selected task.</div>`;
  if (!state.marketLoaded) {
    els.marketPanel.innerHTML = `<div class="empty">Market data has not loaded yet.</div>`;
  }
  if (!state.opportunitiesLoaded) {
    els.opportunitiesPanel.innerHTML = `<div class="empty">Opportunities data has not loaded yet.</div>`;
  }
  if (!state.schedulerLoaded) {
    els.schedulerPanel.innerHTML = `<div class="empty">Scheduler data has not loaded yet.</div>`;
  }
  if (!state.settingsLoaded) {
    els.settingsPanel.innerHTML = `<div class="empty">API settings have not loaded yet.</div>`;
  }
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

async function createTask(event) {
  event.preventDefault();
  const topic = els.topicInput.value.trim();
  if (!topic) return;
  await runAction("Task created", async () => {
    const task = await request("/api/tasks", {
      method: "POST",
      body: JSON.stringify({
        task_type: els.taskTypeInput.value,
        language: "ru",
        topic,
      }),
    });
    state.selectedTaskId = task.id;
    els.topicInput.value = "";
  });
}

async function enqueueSelectedTask() {
  const task = selectedTask();
  if (!task) return;
  await runAction("Task processed and enqueued", async () => {
    await request(`/api/tasks/${task.id}/enqueue`, { method: "POST" });
  });
}

async function approveSelectedTask() {
  const task = selectedTask();
  if (!task) return;
  await runAction("Task approved", async () => {
    await request(`/api/tasks/${task.id}/approve`, {
      method: "POST",
      body: JSON.stringify({ reviewer: "operator", comment: "Approved in console." }),
    });
  });
}

async function notifyReview() {
  const task = selectedTask();
  if (!task) return;
  await runAction("Review notification sent", async () => {
    const result = await request(`/api/tasks/${task.id}/notify-approval`, { method: "POST" });
    return `Notification sent via ${result.channel}`;
  });
}

async function requestRewrite() {
  const task = selectedTask();
  if (!task) return;
  await runAction("Rewrite requested", async () => {
    await request(`/api/tasks/${task.id}/request-rewrite`, {
      method: "POST",
      body: JSON.stringify({ reviewer: "operator", comment: "Rewrite requested in console." }),
    });
  });
}

async function exportPackage() {
  const task = selectedTask();
  if (!task) return;
  await runAction("Publish package exported", async () => {
    await request(`/api/tasks/${task.id}/export-package`, { method: "POST" });
  });
}

async function prepareCmsPayload(packageId) {
  await runAction("CMS dry-run payload prepared", async () => {
    const preview = await request(`/api/tasks/packages/${packageId}/publication-preview`, {
      method: "POST",
    });
    return `CMS payload ready: ${preview.provider}`;
  });
}

async function prepareVideoBrief(packageId) {
  await runAction("Video brief prepared", async () => {
    const brief = await request(`/api/tasks/packages/${packageId}/media-brief`, {
      method: "POST",
    });
    return `Video brief ready: ${brief.brief_type}`;
  });
}

async function generateProductProfile(productId) {
  const task = selectedTask();
  await runAction("Structured product card generated", async () => {
    const payload = {
      language: task?.language || "ru",
      source_task_id: task?.id || null,
    };
    const profile = await request(`/api/products/${productId}/content-profile/generate`, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    return `Product card ready: ${profile.status}`;
  });
}

async function approveProductProfile(productId) {
  await runAction("Structured product card approved", async () => {
    const profile = await request(`/api/products/${productId}/content-profile/approve`, {
      method: "POST",
    });
    return `Product card status: ${profile.status}`;
  });
}

async function runMarketAction(action) {
  const actionMap = {
    "run-monitor": {
      path: "/api/price-monitor/run-once",
      message: "Price monitor run complete",
      label: (result) => `Checked ${result.checked}, changes ${result.changes}`,
    },
    "evaluate-policies": {
      path: "/api/price-monitor/notification-policies/evaluate",
      message: "Policies evaluated",
      label: (result) => `Evaluated ${result.evaluated}, digest ${result.queued_digest}`,
    },
    "send-alerts": {
      path: "/api/price-monitor/trend-alerts/send",
      message: "Immediate alerts sent",
      label: (result) => `Alerts ${result.events}, deliveries ${result.deliveries}`,
    },
    "run-digest": {
      path: "/api/price-monitor/trend-digests/run-batch",
      message: "Market digest batch run",
      label: (result) => `Digest ${result.status}, events ${result.events}`,
    },
  };
  const selected = actionMap[action];
  if (!selected) return;
  await runAction(selected.message, async () => {
    const result = await request(selected.path, { method: "POST" });
    state.marketLoaded = false;
    await renderMarket();
    return selected.label(result);
  });
}

async function buildMarketIndex(groupId) {
  await runAction("Market index built", async () => {
    const index = await request(`/api/price-monitor/groups/${groupId}/market-indexes`, {
      method: "POST",
    });
    state.marketLoaded = false;
    await renderMarket();
    return `Index avg: ${index.avg_price || "-"}`;
  });
}

async function submitMarketForm(form) {
  const formData = new FormData(form);
  const formType = form.dataset.marketForm;
  const payload = Object.fromEntries(
    [...formData.entries()].filter(([, value]) => String(value).trim() !== ""),
  );
  if (payload.min_affected_sources) {
    payload.min_affected_sources = Number(payload.min_affected_sources);
  }
  if (payload.min_percent_change) {
    payload.min_percent_change = String(payload.min_percent_change);
  }
  const config = {
    group: { path: "/api/price-monitor/groups", message: "Market group created" },
    source: { path: "/api/price-monitor/sources", message: "Monitored source added" },
    policy: {
      path: "/api/price-monitor/notification-policies",
      message: "Notification policy created",
    },
  }[formType];
  if (!config) return;
  await runAction(config.message, async () => {
    await request(config.path, {
      method: "POST",
      body: JSON.stringify(payload),
    });
    form.reset();
    state.marketLoaded = false;
    await renderMarket();
  });
}

async function runSchedulerAction(action) {
  if (action === "refresh") {
    state.schedulerLoaded = false;
    await renderScheduler();
    showToast("Scheduler refreshed");
    return;
  }
  if (action !== "run-due") return;
  await runAction("Due scheduler jobs run", async () => {
    const result = await request("/api/scheduler/run-due", { method: "POST" });
    state.schedulerLoaded = false;
    state.marketLoaded = false;
    await Promise.all([renderScheduler(), renderMarket()]);
    return `Started ${result.started}, succeeded ${result.succeeded}`;
  });
}

async function runSchedulerJobNow(jobKey) {
  await runAction("Scheduled job run", async () => {
    const run = await request(`/api/scheduler/jobs/${jobKey}/run-now`, { method: "POST" });
    state.schedulerLoaded = false;
    state.marketLoaded = false;
    await Promise.all([renderScheduler(), renderMarket()]);
    return `${run.job_key}: ${run.status}`;
  });
}

async function submitOpportunityDiscovery(form) {
  const formData = new FormData(form);
  const payload = Object.fromEntries(
    [...formData.entries()].filter(([, value]) => String(value).trim() !== ""),
  );
  if (payload.limit) {
    payload.limit = Number(payload.limit);
  }
  await runAction("Article topics discovered", async () => {
    const result = await request("/api/content-opportunities/discover", {
      method: "POST",
      body: JSON.stringify(payload),
    });
    state.opportunitiesLoaded = false;
    await renderOpportunities();
    return `Created ${result.created} opportunities`;
  });
}

async function createArticleTaskFromOpportunity(opportunityId) {
  await runAction("Article task created", async () => {
    const result = await request(`/api/content-opportunities/${opportunityId}/create-task`, {
      method: "POST",
    });
    state.opportunitiesLoaded = false;
    await renderOpportunities();
    return `Task created: ${result.task_id}`;
  });
}

async function syncSkills() {
  await runAction("Skills synced", async () => {
    const result = await request("/api/skills/sync", { method: "POST" });
    state.registryLoaded = false;
    await renderRegistry();
    return `Skills synced: ${result.upserted}`;
  });
}

async function runAction(successMessage, action) {
  state.busy = true;
  setActionState(selectedTask());
  try {
    const customMessage = await action();
    showToast(customMessage || successMessage);
    await loadTasks();
  } catch (error) {
    showToast(`Action failed: ${error.message}`);
  } finally {
    state.busy = false;
    setActionState(selectedTask());
  }
}

function bindEvents() {
  els.apiBaseInput.addEventListener("change", async () => {
    state.apiBase = els.apiBaseInput.value.trim() || state.apiBase;
    await checkHealth();
    await loadTasks();
  });
  els.refreshBtn.addEventListener("click", loadTasks);
  els.apiDocsBtn.addEventListener("click", () => {
    window.open(apiUrl("/docs"), "_blank", "noopener,noreferrer");
  });
  els.createTaskForm.addEventListener("submit", createTask);
  els.enqueueBtn.addEventListener("click", enqueueSelectedTask);
  els.notifyBtn.addEventListener("click", notifyReview);
  els.approveBtn.addEventListener("click", approveSelectedTask);
  els.rewriteBtn.addEventListener("click", requestRewrite);
  els.exportBtn.addEventListener("click", exportPackage);
  els.syncSkillsBtn.addEventListener("click", syncSkills);
  els.loadPromptsBtn.addEventListener("click", renderRegistry);

  els.taskList.addEventListener("click", async (event) => {
    const row = event.target.closest("[data-task-id]");
    if (!row) return;
    state.selectedTaskId = row.dataset.taskId;
    renderTasks();
    await renderSelectedTask();
  });

  els.packagesPanel.addEventListener("click", async (event) => {
    const publicationButton = event.target.closest("[data-publication-preview-id]");
    if (publicationButton) {
      await prepareCmsPayload(publicationButton.dataset.publicationPreviewId);
      return;
    }
    const mediaButton = event.target.closest("[data-media-brief-id]");
    if (mediaButton) {
      await prepareVideoBrief(mediaButton.dataset.mediaBriefId);
    }
  });

  els.productProfilePanel.addEventListener("click", async (event) => {
    const generateButton = event.target.closest("[data-generate-product-profile-id]");
    if (generateButton) {
      await generateProductProfile(generateButton.dataset.generateProductProfileId);
      return;
    }
    const approveButton = event.target.closest("[data-approve-product-profile-id]");
    if (approveButton) {
      await approveProductProfile(approveButton.dataset.approveProductProfileId);
    }
  });

  els.articleStudioPanel.addEventListener("click", async (event) => {
    const saveButton = event.target.closest("[data-article-studio-save]");
    if (saveButton) {
      await saveArticleStudioCheckpoints(saveButton.dataset.articleStudioSave);
      return;
    }
    const rewriteButton = event.target.closest("[data-article-studio-rewrite]");
    if (rewriteButton) {
      await rewriteArticleFromCheckpoints(rewriteButton.dataset.articleStudioRewrite);
      return;
    }
    const assetGenerateButton = event.target.closest("[data-article-assets-generate]");
    if (assetGenerateButton) {
      await prepareArticleAssets(assetGenerateButton.dataset.articleAssetsGenerate);
      return;
    }
    const assetStatusButton = event.target.closest("[data-article-asset-status]");
    if (assetStatusButton) {
      await updateArticleAssetStatus(
        assetStatusButton.dataset.taskId,
        assetStatusButton.dataset.assetId,
        assetStatusButton.dataset.articleAssetStatus,
      );
      return;
    }
    const assetGenerateImageButton = event.target.closest("[data-article-asset-generate-image]");
    if (assetGenerateImageButton) {
      await generateArticleAssetImage(
        assetGenerateImageButton.dataset.taskId,
        assetGenerateImageButton.dataset.articleAssetGenerateImage,
      );
      return;
    }
    const assetUploadButton = event.target.closest("[data-article-asset-upload]");
    if (assetUploadButton) {
      await uploadArticleAssetUri(
        assetUploadButton.dataset.taskId,
        assetUploadButton.dataset.articleAssetUpload,
      );
      return;
    }
    const decisionButton = event.target.closest("[data-draft-version-decision]");
    if (decisionButton) {
      await setDraftVersionDecision(
        decisionButton.dataset.taskId,
        decisionButton.dataset.draftId,
        decisionButton.dataset.draftVersionDecision,
      );
      return;
    }
    const resetButton = event.target.closest("[data-article-studio-reset]");
    if (resetButton) {
      await resetArticleStudioCheckpoints(resetButton.dataset.articleStudioReset);
    }
  });

  els.marketPanel.addEventListener("click", async (event) => {
    const actionButton = event.target.closest("[data-market-action]");
    if (actionButton) {
      await runMarketAction(actionButton.dataset.marketAction);
      return;
    }
    const indexButton = event.target.closest("[data-build-market-index-id]");
    if (indexButton) {
      await buildMarketIndex(indexButton.dataset.buildMarketIndexId);
    }
  });

  els.marketPanel.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-market-form]");
    if (!form) return;
    event.preventDefault();
    await submitMarketForm(form);
  });

  els.schedulerPanel.addEventListener("click", async (event) => {
    const actionButton = event.target.closest("[data-scheduler-action]");
    if (actionButton) {
      await runSchedulerAction(actionButton.dataset.schedulerAction);
      return;
    }
    const runNowButton = event.target.closest("[data-scheduler-run-now]");
    if (runNowButton) {
      await runSchedulerJobNow(runNowButton.dataset.schedulerRunNow);
    }
  });

  els.settingsPanel.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-runtime-settings-form]");
    if (!form) return;
    event.preventDefault();
    await submitRuntimeSettings(form);
  });

  els.settingsPanel.addEventListener("click", async (event) => {
    const refreshButton = event.target.closest("[data-settings-refresh]");
    if (refreshButton) {
      state.settingsLoaded = false;
      await renderSettings();
    }
  });

  els.opportunitiesPanel.addEventListener("submit", async (event) => {
    const form = event.target.closest("[data-opportunity-form]");
    if (!form) return;
    event.preventDefault();
    await submitOpportunityDiscovery(form);
  });

  els.opportunitiesPanel.addEventListener("click", async (event) => {
    const createButton = event.target.closest("[data-opportunity-create-task]");
    if (createButton) {
      await createArticleTaskFromOpportunity(createButton.dataset.opportunityCreateTask);
    }
  });

  document.querySelectorAll(".tab").forEach((tab) => {
    tab.addEventListener("click", () => {
      document.querySelectorAll(".tab").forEach((item) => item.classList.remove("active"));
      document.querySelectorAll(".tab-panel").forEach((item) => item.classList.remove("active"));
      tab.classList.add("active");
      document.querySelector(`#${tab.dataset.tab}Panel`).classList.add("active");
      if (tab.dataset.tab === "market" && !state.marketLoaded) {
        renderMarket();
      }
      if (tab.dataset.tab === "scheduler" && !state.schedulerLoaded) {
        renderScheduler();
      }
      if (tab.dataset.tab === "settings" && !state.settingsLoaded) {
        renderSettings();
      }
      if (tab.dataset.tab === "opportunities" && !state.opportunitiesLoaded) {
        renderOpportunities();
      }
    });
  });
}

async function boot() {
  els.apiBaseInput.value = state.apiBase;
  bindEvents();
  await checkHealth();
  try {
    await loadTasks();
    await Promise.all([renderMarket(), renderScheduler(), renderOpportunities(), renderSettings()]);
  } catch (error) {
    showToast(`Load failed: ${error.message}`);
    renderEmptyPanels();
  }
}

boot();
