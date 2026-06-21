const collectButton = document.getElementById("collect-btn");
const newsletterButton = document.getElementById("newsletter-btn");
const statusNode = document.getElementById("collect-status");
const newsListNode = document.getElementById("news-list");
const themeFilter = document.getElementById("theme-filter");
const searchFilter = document.getElementById("search-filter");
const minScoreFilter = document.getElementById("min-score-filter");
const applyFilterButton = document.getElementById("apply-filter-btn");
const exportCsvLink = document.getElementById("export-csv");
const exportXlsxLink = document.getElementById("export-xlsx");
const prevPageButton = document.getElementById("prev-page-btn");
const nextPageButton = document.getElementById("next-page-btn");
const pageStatusNode = document.getElementById("page-status");
const timezoneInput = document.getElementById("timezone-input");
const newsletterHourInput = document.getElementById("newsletter-hour-input");
const newsletterMinuteInput = document.getElementById("newsletter-minute-input");
const newsletterMinScoreInput = document.getElementById("newsletter-min-score-input");
const saveSettingsButton = document.getElementById("save-settings-btn");
const resetSettingsButton = document.getElementById("reset-settings-btn");
const settingsStatusNode = document.getElementById("settings-status");
const timezoneErrorNode = document.getElementById("timezone-error");
const hourErrorNode = document.getElementById("hour-error");
const minuteErrorNode = document.getElementById("minute-error");
const scoreErrorNode = document.getElementById("score-error");
const sourcesTableBody = document.getElementById("sources-table-body");

const PAGE_SIZE = 10;
let currentOffset = 0;
let totalItems = 0;

function currentFilterParams() {
  const params = new URLSearchParams();
  const theme = themeFilter.value.trim();
  const searchTerm = searchFilter.value.trim();
  const minScore = minScoreFilter.value.trim();

  if (theme) {
    params.set("theme", theme);
  }
  if (minScore && Number(minScore) > 0) {
    params.set("min_score", minScore);
  }
  if (searchTerm) {
    params.set("q", searchTerm);
  }

  params.set("limit", String(PAGE_SIZE));
  params.set("offset", String(currentOffset));

  return params;
}

function refreshExportLinks() {
  const params = currentFilterParams();
  params.delete("limit");
  params.delete("offset");
  const query = params.toString();
  exportCsvLink.href = query ? `/export/csv?${query}` : "/export/csv";
  exportXlsxLink.href = query ? `/export/xlsx?${query}` : "/export/xlsx";
}

function currentSourceMetricsParams() {
  const params = new URLSearchParams();
  const searchTerm = searchFilter.value.trim();
  const minScore = minScoreFilter.value.trim();

  if (minScore && Number(minScore) > 0) {
    params.set("min_score", minScore);
  }
  if (searchTerm) {
    params.set("q", searchTerm);
  }
  return params;
}

function renderSourcesMetrics(sources) {
  if (!sourcesTableBody) {
    return;
  }

  if (!Array.isArray(sources) || sources.length === 0) {
    sourcesTableBody.innerHTML = '<tr><td colspan="6">Nenhuma metrica disponivel.</td></tr>';
    return;
  }

  sourcesTableBody.innerHTML = "";
  for (const item of sources) {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${item.source || "n/a"}</td>
      <td>${Number(item.total || 0)}</td>
      <td>${Number(item.avg_relevance_score || 0)}</td>
      <td>${Number(item.translated_items || 0)}</td>
      <td>${Number(item.untranslated_items || 0)}</td>
      <td>${item.last_collected_at || "n/a"}</td>
    `;
    sourcesTableBody.appendChild(row);
  }
}

async function loadSourcesMetrics() {
  if (!sourcesTableBody) {
    return;
  }

  sourcesTableBody.innerHTML = '<tr><td colspan="6">Carregando metricas...</td></tr>';
  try {
    const params = currentSourceMetricsParams();
    const response = await fetch(`/api/news/sources?${params.toString()}`);
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "erro desconhecido";
      sourcesTableBody.innerHTML = `<tr><td colspan="6">Falha ao carregar metricas (${response.status}): ${detail}</td></tr>`;
      return;
    }
    renderSourcesMetrics(data.sources);
  } catch (_error) {
    sourcesTableBody.innerHTML = '<tr><td colspan="6">Falha ao carregar metricas.</td></tr>';
  }
}

async function loadNews() {
  const params = currentFilterParams();
  const response = await fetch(`/api/news?${params.toString()}`);
  const news = await response.json();

  const countParams = new URLSearchParams(params);
  countParams.delete("limit");
  countParams.delete("offset");
  const countResponse = await fetch(`/api/news/count?${countParams.toString()}`);
  const countPayload = await countResponse.json();
  totalItems = Number(countPayload.total || 0);

  refreshExportLinks();
  refreshPagination();
  await loadSourcesMetrics();

  newsListNode.innerHTML = "";
  if (!Array.isArray(news) || news.length === 0) {
    newsListNode.innerHTML = "<p>Nenhuma noticia coletada ainda.</p>";
    return;
  }

  for (const item of news) {
    const article = document.createElement("article");
    article.className = "card";
    article.innerHTML = `
      <h3>${item.title}</h3>
      <p class="meta">Fonte: ${item.source} | Tema: ${item.theme} | Score: ${item.relevance_score}</p>
      <p class="meta">Publicado: ${item.published_at || "n/a"}</p>
      <pre class="summary">${item.summary}</pre>
      <a href="${item.url}" target="_blank" rel="noreferrer">Abrir materia</a>
    `;
    newsListNode.appendChild(article);
  }
}

function refreshPagination() {
  const page = Math.floor(currentOffset / PAGE_SIZE) + 1;
  const totalPages = Math.max(1, Math.ceil(totalItems / PAGE_SIZE));
  pageStatusNode.textContent = `Pagina ${page} de ${totalPages} (${totalItems} itens)`;

  prevPageButton.disabled = currentOffset === 0;
  nextPageButton.disabled = currentOffset + PAGE_SIZE >= totalItems;
}

async function runCollect() {
  statusNode.textContent = "Coletando...";
  collectButton.disabled = true;

  try {
    const response = await fetch("/collect", { method: "POST" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "erro desconhecido";
      statusNode.textContent = `Falha na coleta (${response.status}): ${detail}`;
      return;
    }
    if (
      typeof data.feeds_checked !== "number" ||
      typeof data.entries_found !== "number" ||
      typeof data.entries_saved !== "number"
    ) {
      statusNode.textContent = "Falha na coleta: resposta inesperada da API.";
      return;
    }
    statusNode.textContent = `Feeds: ${data.feeds_checked} | Encontradas: ${data.entries_found} | Salvas: ${data.entries_saved}`;
    await loadNews();
  } catch (_error) {
    statusNode.textContent = "Falha na coleta.";
  } finally {
    collectButton.disabled = false;
  }
}

async function runNewsletter() {
  statusNode.textContent = "Gerando newsletter...";
  newsletterButton.disabled = true;

  try {
    const response = await fetch("/newsletter/run", { method: "POST" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const detail = typeof data.detail === "string" ? data.detail : "erro desconhecido";
      statusNode.textContent = `Falha ao gerar newsletter (${response.status}): ${detail}`;
      return;
    }
    if (typeof data.generated_items !== "number" || typeof data.file_path !== "string") {
      statusNode.textContent = "Falha ao gerar newsletter: resposta inesperada da API.";
      return;
    }
    statusNode.textContent = `Newsletter gerada com ${data.generated_items} itens em ${data.file_path}`;
  } catch (_error) {
    statusNode.textContent = "Falha ao gerar newsletter.";
  } finally {
    newsletterButton.disabled = false;
  }
}

async function loadSettings() {
  try {
    const response = await fetch("/api/settings");
    const settings = await response.json();
    timezoneInput.value = settings.timezone || "";
    newsletterHourInput.value = String(settings.newsletter_hour ?? "");
    newsletterMinuteInput.value = String(settings.newsletter_minute ?? "");
    newsletterMinScoreInput.value = String(settings.newsletter_min_score ?? "");
    clearSettingsValidation();
    settingsStatusNode.textContent = "Configuracoes carregadas.";
  } catch (_error) {
    settingsStatusNode.textContent = "Falha ao carregar configuracoes.";
  }
}

function setFieldError(inputNode, errorNode, message) {
  if (message) {
    inputNode.classList.add("field-invalid");
    errorNode.textContent = message;
    return;
  }
  inputNode.classList.remove("field-invalid");
  errorNode.textContent = "";
}

function clearSettingsValidation() {
  setFieldError(timezoneInput, timezoneErrorNode, "");
  setFieldError(newsletterHourInput, hourErrorNode, "");
  setFieldError(newsletterMinuteInput, minuteErrorNode, "");
  setFieldError(newsletterMinScoreInput, scoreErrorNode, "");
}

function validateSettingsForm() {
  clearSettingsValidation();

  let valid = true;
  const timezone = timezoneInput.value.trim();
  const hour = Number(newsletterHourInput.value);
  const minute = Number(newsletterMinuteInput.value);
  const score = Number(newsletterMinScoreInput.value);

  if (!timezone) {
    setFieldError(timezoneInput, timezoneErrorNode, "Informe um timezone.");
    valid = false;
  }
  if (!Number.isInteger(hour) || hour < 0 || hour > 23) {
    setFieldError(newsletterHourInput, hourErrorNode, "Use um valor entre 0 e 23.");
    valid = false;
  }
  if (!Number.isInteger(minute) || minute < 0 || minute > 59) {
    setFieldError(newsletterMinuteInput, minuteErrorNode, "Use um valor entre 0 e 59.");
    valid = false;
  }
  if (!Number.isInteger(score) || score < 0 || score > 100) {
    setFieldError(newsletterMinScoreInput, scoreErrorNode, "Use um valor entre 0 e 100.");
    valid = false;
  }

  return valid;
}

async function saveSettings() {
  if (!validateSettingsForm()) {
    settingsStatusNode.textContent = "Revise os campos destacados.";
    return;
  }

  settingsStatusNode.textContent = "Salvando configuracoes...";
  saveSettingsButton.disabled = true;
  resetSettingsButton.disabled = true;

  try {
    const payload = {
      timezone: timezoneInput.value.trim(),
      newsletter_hour: Number(newsletterHourInput.value),
      newsletter_minute: Number(newsletterMinuteInput.value),
      newsletter_min_score: Number(newsletterMinScoreInput.value),
    };

    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!response.ok) {
      throw new Error("save failed");
    }

    const data = await response.json();
    settingsStatusNode.textContent = `Configuracoes salvas (${data.timezone}, ${data.newsletter_hour}:${String(data.newsletter_minute).padStart(2, "0")}).`;
  } catch (_error) {
    settingsStatusNode.textContent = "Falha ao salvar configuracoes.";
  } finally {
    saveSettingsButton.disabled = false;
    resetSettingsButton.disabled = false;
  }
}

async function resetSettings() {
  const confirmed = window.confirm(
    "Tem certeza que deseja restaurar as configuracoes padrao? Essa acao sobrescreve os valores atuais."
  );
  if (!confirmed) {
    settingsStatusNode.textContent = "Restauracao cancelada.";
    return;
  }

  settingsStatusNode.textContent = "Restaurando padrao...";
  saveSettingsButton.disabled = true;
  resetSettingsButton.disabled = true;

  try {
    const response = await fetch("/api/settings/reset", { method: "POST" });
    if (!response.ok) {
      throw new Error("reset failed");
    }
    const data = await response.json();
    timezoneInput.value = data.timezone;
    newsletterHourInput.value = String(data.newsletter_hour);
    newsletterMinuteInput.value = String(data.newsletter_minute);
    newsletterMinScoreInput.value = String(data.newsletter_min_score);
    clearSettingsValidation();
    settingsStatusNode.textContent = "Configuracoes padrao restauradas.";
  } catch (_error) {
    settingsStatusNode.textContent = "Falha ao restaurar configuracoes padrao.";
  } finally {
    saveSettingsButton.disabled = false;
    resetSettingsButton.disabled = false;
  }
}

collectButton.addEventListener("click", runCollect);
newsletterButton.addEventListener("click", runNewsletter);
applyFilterButton.addEventListener("click", () => {
  currentOffset = 0;
  loadNews();
});
prevPageButton.addEventListener("click", () => {
  currentOffset = Math.max(0, currentOffset - PAGE_SIZE);
  loadNews();
});
nextPageButton.addEventListener("click", () => {
  if (currentOffset + PAGE_SIZE < totalItems) {
    currentOffset += PAGE_SIZE;
    loadNews();
  }
});
saveSettingsButton.addEventListener("click", saveSettings);
resetSettingsButton.addEventListener("click", resetSettings);
loadSettings();
loadNews();
