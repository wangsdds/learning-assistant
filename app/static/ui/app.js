"use strict";

const TOKEN_KEY = "learning-assistant.token";
const state = {
  user: null,
  plans: [],
  documents: [],
  currentDocId: null,
  questions: [],
  answerQuestionId: null,
  answerStartedAt: null,
  answerTimer: null,
  toastTimer: null,
  view: "dashboard",
};

const $ = (selector, root = document) => root.querySelector(selector);
const $$ = (selector, root = document) => Array.from(root.querySelectorAll(selector));

const VIEW_META = {
  dashboard: { kicker: "TODAY", title: "工作台" },
  plans: { kicker: "PLAN", title: "学习计划" },
  documents: { kicker: "LIBRARY", title: "资料与题目" },
};

function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#039;",
  })[character]);
}

function localToday() {
  const now = new Date();
  const local = new Date(now.getTime() - now.getTimezoneOffset() * 60000);
  return local.toISOString().slice(0, 10);
}

function formatDateParts(value) {
  const match = String(value ?? "").match(/^(\d{4})-(\d{2})-(\d{2})/);
  if (match) {
    return { year: match[1], month: match[2], day: match[3] };
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return { year: "", month: "--", day: "--" };
  }
  return {
    year: String(date.getFullYear()),
    month: String(date.getMonth() + 1).padStart(2, "0"),
    day: String(date.getDate()).padStart(2, "0"),
  };
}

function shortDate(value) {
  const parts = formatDateParts(value);
  return `${parts.month}/${parts.day}`;
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return String(value ?? "");
  return date.toLocaleString("zh-CN", {
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatElapsed(totalSeconds) {
  const seconds = Math.max(0, Number(totalSeconds) || 0);
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function safeHost(value) {
  try {
    return new URL(value).hostname || value;
  } catch {
    return String(value ?? "");
  }
}

function safeHttpUrl(value) {
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.href : null;
  } catch {
    return null;
  }
}

function initials(name) {
  const parts = Array.from(String(name ?? "").trim());
  return parts.slice(0, 2).join("").toUpperCase() || "L";
}

function greeting() {
  const hour = new Date().getHours();
  if (hour < 6) return "夜深了";
  if (hour < 12) return "早上好";
  if (hour < 18) return "下午好";
  return "晚上好";
}

function showToast(message, type = "success") {
  const toast = $("#toast");
  window.clearTimeout(state.toastTimer);
  toast.textContent = message;
  toast.className = `toast show${type === "error" ? " error" : ""}`;
  state.toastTimer = window.setTimeout(() => {
    toast.className = "toast";
  }, 3200);
}

function formatApiError(payload) {
  if (!payload) return "请求失败，请稍后再试";
  if (Array.isArray(payload.detail)) {
    return payload.detail.map((item) => {
      const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "字段";
      return `${field}: ${item.msg}`;
    }).join("；");
  }
  const messages = {
    "invalid email or password": "邮箱或密码不正确",
    "email already registered": "这个邮箱已经注册过了",
    "document not found": "没有找到这份资料",
    "question not found": "没有找到这道题",
    "docments or websites is required": "资料内容与来源网址至少填写一项",
  };
  return messages[payload.detail] || payload.detail || "请求失败，请稍后再试";
}

async function api(path, options = {}) {
  const headers = new Headers(options.headers || {});
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const token = sessionStorage.getItem(TOKEN_KEY);
  if (token) headers.set("Authorization", `Bearer ${token}`);

  let response;
  try {
    response = await fetch(path, { ...options, headers });
  } catch {
    throw new Error("无法连接服务，请检查网络后重试");
  }

  const raw = await response.text();
  let payload = null;
  if (raw) {
    try {
      payload = JSON.parse(raw);
    } catch {
      payload = raw;
    }
  }

  if (!response.ok) {
    const error = new Error(formatApiError(payload));
    error.status = response.status;
    throw error;
  }
  return payload;
}

function setFormBusy(form, busy) {
  const button = $('button[type="submit"]', form);
  if (!button) return;
  if (busy) {
    button.dataset.originalLabel = button.textContent;
    button.textContent = "处理中…";
    button.disabled = true;
  } else {
    button.textContent = button.dataset.originalLabel || "提交";
    button.disabled = false;
  }
}

function setAuthTab(tabName) {
  $$(".auth-tab").forEach((button) => {
    const active = button.dataset.authTab === tabName;
    button.classList.toggle("active", active);
    button.setAttribute("aria-selected", String(active));
  });
  $("#login-form").classList.toggle("hidden", tabName !== "login");
  $("#register-form").classList.toggle("hidden", tabName !== "register");
}

function showAuth() {
  $("#auth-screen").classList.remove("hidden");
  $("#app-shell").classList.add("hidden");
  setAuthTab("login");
}

function showApp() {
  $("#auth-screen").classList.add("hidden");
  $("#app-shell").classList.remove("hidden");
}

function renderUser() {
  if (!state.user) return;
  $("#user-nickname").textContent = state.user.nickname;
  $("#user-email").textContent = state.user.email;
  $("#user-initial").textContent = initials(state.user.nickname);
  $("#stat-user").textContent = state.user.nickname;
  $("#dash-greeting").textContent = `${greeting()}，${state.user.nickname}`;
}

async function enterApp() {
  state.user = await api("/me");
  showApp();
  renderUser();
  await refreshData();
  setView("dashboard");
}

function logout() {
  sessionStorage.removeItem(TOKEN_KEY);
  state.user = null;
  state.plans = [];
  state.documents = [];
  state.currentDocId = null;
  state.questions = [];
  stopAnswerTimer();
  $$("dialog[open]").forEach((dialog) => dialog.close());
  showAuth();
}

async function refreshData() {
  const [plans, documents] = await Promise.all([
    api("/plan_days"),
    api("/documents"),
  ]);
  state.plans = plans;
  state.documents = documents;

  if (state.currentDocId && !documents.some((document) => document.id === state.currentDocId)) {
    state.currentDocId = null;
    state.questions = [];
  }

  renderDashboard();
  renderPlans();
  renderDocuments();

  if (state.currentDocId) {
    await loadQuestions(state.currentDocId);
  } else {
    renderDocDetail();
  }
}

function renderDashboard() {
  $("#stat-plans").textContent = String(state.plans.length);
  $("#stat-documents").textContent = String(state.documents.length);

  const planList = $("#dash-plan-list");
  if (!state.plans.length) {
    planList.innerHTML = '<div class="empty-inline">还没有计划。先写下一件今天真正要完成的事。</div>';
  } else {
    planList.innerHTML = state.plans.slice(-3).reverse().map((plan) => `
      <div class="compact-row">
        <span class="row-date">${escapeHtml(shortDate(plan.add_date))}</span>
        <span class="row-body"><strong>${escapeHtml(plan.calender)}</strong><small>${escapeHtml(plan.add_date)}</small></span>
      </div>
    `).join("");
  }

  const docList = $("#dash-doc-list");
  if (!state.documents.length) {
    docList.innerHTML = '<div class="empty-inline">资料库还是空的。把正在读的文章或笔记收进来。</div>';
  } else {
    docList.innerHTML = state.documents.slice(-3).reverse().map((document) => `
      <div class="compact-row">
        <span class="row-date">DOC</span>
        <span class="row-body"><strong>${escapeHtml(document.documents_name)}</strong><small>${escapeHtml(document.websites ? safeHost(document.websites) : "本地资料")}</small></span>
      </div>
    `).join("");
  }
}

function renderPlans() {
  const list = $("#plans-list");
  if (!state.plans.length) {
    list.innerHTML = '<div class="empty-block">还没有学习计划。今天可以先写一条。</div>';
    return;
  }
  list.innerHTML = state.plans.map((plan) => {
    const parts = formatDateParts(plan.add_date);
    return `
      <article class="plan-card">
        <div class="plan-date-badge"><strong>${escapeHtml(parts.day)}</strong><span>${escapeHtml(parts.month)} 月</span></div>
        <div><h3>${escapeHtml(plan.calender)}</h3><p>${escapeHtml(plan.add_date)} · 计划 #${plan.plan_id}</p></div>
      </article>
    `;
  }).join("");
}

function renderDocuments() {
  $("#doc-count").textContent = String(state.documents.length);
  const list = $("#documents-list");
  if (!state.documents.length) {
    list.innerHTML = '<div class="empty-block">资料库为空。点击右上角“收录资料”。</div>';
    return;
  }
  list.innerHTML = state.documents.map((document) => {
    const subtitle = document.websites ? safeHost(document.websites) : (document.docments || "本地资料");
    return `
      <button class="document-item${document.id === state.currentDocId ? " active" : ""}" type="button" data-document-id="${document.id}">
        <strong>${escapeHtml(document.documents_name)}</strong>
        <span>${escapeHtml(subtitle)}</span>
      </button>
    `;
  }).join("");
}

function renderDocDetail(loading = false) {
  const container = $("#doc-detail");
  const document = state.documents.find((item) => item.id === state.currentDocId);
  if (!document) {
    container.innerHTML = `
      <div class="detail-empty">
        <div><div class="empty-mark">L</div><p>从左边选一份资料，或者先收录一份新资料。</p></div>
      </div>
    `;
    return;
  }

  const sourceUrl = safeHttpUrl(document.websites);
  const source = sourceUrl
    ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener">${escapeHtml(safeHost(sourceUrl))} ↗</a>`
    : document.websites
      ? `<span>${escapeHtml(document.websites)}</span>`
      : "";
  const preview = document.docments
    ? `<div class="source-preview">${escapeHtml(document.docments)}</div>`
    : "";

  const questions = loading
    ? '<div class="empty-block">正在读取题目…</div>'
    : state.questions.length
      ? state.questions.map((question) => `
          <article class="question-item">
            <div class="question-body"><p>${escapeHtml(question.que)}</p><span>题目 #${question.id}</span></div>
            <button class="button button-secondary" type="button" data-answer-question="${question.id}">开始答题</button>
          </article>
        `).join("")
      : '<div class="empty-block">这份资料还没有题目。为它出一道能检验理解的题。</div>';

  container.innerHTML = `
    <div class="detail-head">
      <div><span class="card-kicker">MATERIAL</span><h2>${escapeHtml(document.documents_name)}</h2><p>资料 #${document.id} · ${document.websites ? "网址资料" : "本地资料"}</p></div>
      <button class="button button-primary button-small" type="button" data-add-question>新增题目</button>
    </div>
    <div class="source-block"><span class="source-label">SOURCE</span>${source || '<span>没有外部链接</span>'}</div>
    ${preview}
    <section class="detail-section">
      <div class="detail-section-head"><h3>练习题</h3><span class="count-pill">${loading ? "…" : state.questions.length}</span></div>
      <div class="question-list">${questions}</div>
    </section>
  `;
}

async function selectDocument(documentId) {
  state.currentDocId = documentId;
  state.questions = [];
  renderDocuments();
  renderDocDetail(true);
  try {
    await loadQuestions(documentId);
  } catch (error) {
    showToast(error.message, "error");
    renderDocDetail();
  }
}

async function loadQuestions(documentId) {
  state.questions = await api(`/documents/${documentId}/questions`);
  if (state.currentDocId === documentId) renderDocDetail();
}

function setView(view) {
  if (!VIEW_META[view]) return;
  state.view = view;
  $$(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  $$(".view").forEach((section) => section.classList.toggle("active", section.id === `view-${view}`));
  $("#page-kicker").textContent = VIEW_META[view].kicker;
  $("#page-title").textContent = VIEW_META[view].title;
  $("#app-shell").classList.remove("menu-open");
  window.scrollTo({ top: 0, behavior: "smooth" });

  if (view === "documents" && !state.currentDocId && state.documents.length) {
    selectDocument(state.documents[0].id);
  }
}

function openPlanDialog() {
  $("#plan-date").value = $("#plan-date").value || localToday();
  $("#plan-dialog").showModal();
  $("#plan-content").focus();
}

function openDocumentDialog() {
  $("#document-form").reset();
  $("#document-dialog").showModal();
  $("#doc-name").focus();
}

function openQuestionDialog() {
  if (!state.currentDocId) return;
  $("#question-form").reset();
  $("#question-dialog").showModal();
  $("#question-text").focus();
}

function startAnswerTimer() {
  stopAnswerTimer();
  state.answerStartedAt = Date.now();
  const tick = () => {
    const seconds = Math.floor((Date.now() - state.answerStartedAt) / 1000);
    $("#answer-timer").textContent = formatElapsed(seconds);
  };
  tick();
  state.answerTimer = window.setInterval(tick, 1000);
}

function stopAnswerTimer() {
  if (state.answerTimer) window.clearInterval(state.answerTimer);
  state.answerTimer = null;
}

async function openAnswerDialog(questionId) {
  const question = state.questions.find((item) => item.id === questionId);
  if (!question) return;
  state.answerQuestionId = questionId;
  $("#answer-question-text").textContent = question.que;
  $("#answer-input").value = "";
  $("#answer-history").innerHTML = '<div class="empty-inline">正在读取作答记录…</div>';
  startAnswerTimer();
  $("#answer-dialog").showModal();
  $("#answer-input").focus();
  try {
    await loadAnswerHistory(questionId);
  } catch (error) {
    $("#answer-history").innerHTML = `<div class="empty-inline">${escapeHtml(error.message)}</div>`;
  }
}

async function loadAnswerHistory(questionId) {
  const answers = await api(`/questions/${questionId}/answers`);
  if (state.answerQuestionId !== questionId) return;
  renderAnswerHistory(answers);
}

function renderAnswerHistory(answers) {
  const container = $("#answer-history");
  if (!answers.length) {
    container.innerHTML = '<div class="empty-inline">这是第一次作答。认真写下你的答案。</div>';
    return;
  }
  container.innerHTML = answers.map((answer) => {
    const correct = answer.scores === "1";
    return `
      <div class="history-item">
        <span class="score-dot${correct ? " correct" : ""}"></span>
        <div class="history-body">
          <p>${escapeHtml(answer.user_answer)}</p>
          <span>${correct ? "答对" : "未答对"} · ${escapeHtml(formatDateTime(answer.answer_time))} · ${answer.costtime} 秒</span>
        </div>
      </div>
    `;
  }).join("");
}

function bindEvents() {
  $$(".auth-tab").forEach((button) => {
    button.addEventListener("click", () => setAuthTab(button.dataset.authTab));
  });

  $("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const email = $("#login-email").value.trim();
    const password = $("#login-password").value;
    if (!email || !password) return showToast("请填写邮箱和密码", "error");
    setFormBusy(form, true);
    try {
      const payload = await api("/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      sessionStorage.setItem(TOKEN_KEY, payload.access_token);
      await enterApp();
      form.reset();
      showToast("登录成功");
    } catch (error) {
      sessionStorage.removeItem(TOKEN_KEY);
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });

  $("#register-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const nickname = $("#register-nickname").value.trim();
    const email = $("#register-email").value.trim();
    const password = $("#register-password").value;
    if (!nickname || !email || !password) return showToast("请完整填写注册信息", "error");
    setFormBusy(form, true);
    try {
      await api("/users", {
        method: "POST",
        body: JSON.stringify({ nickname, email, password }),
      });
      const payload = await api("/login", {
        method: "POST",
        body: JSON.stringify({ email, password }),
      });
      sessionStorage.setItem(TOKEN_KEY, payload.access_token);
      await enterApp();
      form.reset();
      showToast("账号已创建，欢迎开始学习");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });

  $("#logout-button").addEventListener("click", logout);
  $$(".nav-item").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.view));
  });
  $$("[data-go-view]").forEach((button) => {
    button.addEventListener("click", () => setView(button.dataset.goView));
  });

  $("#menu-toggle").addEventListener("click", () => $("#app-shell").classList.add("menu-open"));
  $("#sidebar-scrim").addEventListener("click", () => $("#app-shell").classList.remove("menu-open"));

  $("#dash-add-plan").addEventListener("click", openPlanDialog);
  $("#add-plan-button").addEventListener("click", openPlanDialog);
  $("#dash-add-doc").addEventListener("click", openDocumentDialog);
  $("#add-doc-button").addEventListener("click", openDocumentDialog);

  $("#documents-list").addEventListener("click", (event) => {
    const button = event.target.closest("[data-document-id]");
    if (button) selectDocument(Number(button.dataset.documentId));
  });

  $("#doc-detail").addEventListener("click", (event) => {
    if (event.target.closest("[data-add-question]")) {
      openQuestionDialog();
      return;
    }
    const answerButton = event.target.closest("[data-answer-question]");
    if (answerButton) openAnswerDialog(Number(answerButton.dataset.answerQuestion));
  });

  document.addEventListener("click", (event) => {
    const closeButton = event.target.closest("[data-close-dialog]");
    if (closeButton) closeButton.closest("dialog")?.close();
  });

  $$("dialog").forEach((dialog) => {
    dialog.addEventListener("click", (event) => {
      if (event.target === dialog) dialog.close();
    });
  });
  $("#answer-dialog").addEventListener("close", stopAnswerTimer);

  $("#plan-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const calender = $("#plan-content").value.trim();
    const addDate = $("#plan-date").value;
    if (!calender || !addDate) return showToast("请填写计划内容和日期", "error");
    setFormBusy(form, true);
    try {
      await api("/plan_days", {
        method: "POST",
        body: JSON.stringify({ calender, add_date: addDate }),
      });
      form.reset();
      $("#plan-dialog").close();
      await refreshData();
      showToast("计划已保存");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });

  $("#document-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const documentsName = $("#doc-name").value.trim();
    const content = $("#doc-content").value.trim();
    const website = $("#doc-url").value.trim();
    if (!documentsName) return showToast("请填写资料名称", "error");
    if (!content && !website) return showToast("资料内容与来源网址至少填写一项", "error");
    setFormBusy(form, true);
    try {
      const created = await api("/documents", {
        method: "POST",
        body: JSON.stringify({
          documents_name: documentsName,
          docments: content || null,
          websites: website || null,
        }),
      });
      state.currentDocId = created.id;
      state.questions = [];
      form.reset();
      $("#document-dialog").close();
      setView("documents");
      await refreshData();
      renderDocuments();
      showToast("资料已收录");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });

  $("#question-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const que = $("#question-text").value.trim();
    const answer = Number($("#system-answer").value);
    if (!state.currentDocId) return showToast("请先选择资料", "error");
    if (!que) return showToast("请填写题目", "error");
    if (!Number.isInteger(answer)) return showToast("标准答案必须是整数", "error");
    setFormBusy(form, true);
    try {
      await api(`/documents/${state.currentDocId}/questions`, {
        method: "POST",
        body: JSON.stringify({ que, system_answer: answer }),
      });
      form.reset();
      $("#question-dialog").close();
      await loadQuestions(state.currentDocId);
      showToast("题目已保存");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });

  $("#answer-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const userAnswer = $("#answer-input").value.trim();
    if (!state.answerQuestionId || !userAnswer) return showToast("请先写下答案", "error");
    const costtime = Math.max(0, Math.floor((Date.now() - state.answerStartedAt) / 1000));
    setFormBusy(form, true);
    try {
      const result = await api(`/questions/${state.answerQuestionId}/answers`, {
        method: "POST",
        body: JSON.stringify({ user_answer: userAnswer, costtime }),
      });
      $("#answer-input").value = "";
      startAnswerTimer();
      await loadAnswerHistory(state.answerQuestionId);
      showToast(result.scores === "1" ? "回答正确" : "已记录，再回看一遍资料");
    } catch (error) {
      showToast(error.message, "error");
    } finally {
      setFormBusy(form, false);
    }
  });
}

async function init() {
  bindEvents();
  $("#plan-date").value = localToday();
  if (!sessionStorage.getItem(TOKEN_KEY)) {
    showAuth();
    return;
  }
  try {
    await enterApp();
  } catch (error) {
    sessionStorage.removeItem(TOKEN_KEY);
    showAuth();
    if (error.status !== 401) showToast(error.message, "error");
  }
}

document.addEventListener("DOMContentLoaded", init);
