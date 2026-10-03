const chatThread = document.getElementById("chat-thread");

const composer = document.getElementById("chat-composer");
const answerForm = document.getElementById("chat-answer-form");
const answerInput = document.getElementById("chat-answer");
const sendButton = document.getElementById("chat-send-button");

const planCta = document.getElementById("plan-cta");
const generatePlanButton = document.getElementById(
  "generate-plan-button"
);

const plannerRequest = JSON.parse(
  sessionStorage.getItem("planner_request") || "null"
);

const TOKEN_KEY = "token";
const THEME_KEY = "evolution_theme";

const CHAT_KEY = "evolution_chat";
const EXTRACTION_KEY = "planner_extraction";
const CLARIFICATION_ANSWERS_KEY =
  "clarification_answers";
const CHAT_STAGE_KEY = "chat_stage";

const TYPE_SPEED = 32;
const MESSAGE_DELAY = 650;


/* =========================================================
   Session state
   ========================================================= */

function getExtraction() {
  return JSON.parse(
    sessionStorage.getItem(EXTRACTION_KEY) || "null"
  );
}


function saveExtraction(extraction) {
  sessionStorage.setItem(
    EXTRACTION_KEY,
    JSON.stringify(extraction)
  );
}


function getClarificationAnswers() {
  return JSON.parse(
    sessionStorage.getItem(
      CLARIFICATION_ANSWERS_KEY
    ) || "[]"
  );
}


function saveClarificationAnswers(answers) {
  sessionStorage.setItem(
    CLARIFICATION_ANSWERS_KEY,
    JSON.stringify(answers)
  );
}


function clearClarificationAnswers() {
  sessionStorage.removeItem(
    CLARIFICATION_ANSWERS_KEY
  );
}


function setStage(stage) {
  sessionStorage.setItem(
    CHAT_STAGE_KEY,
    stage
  );
}


function getStage() {
  return sessionStorage.getItem(
    CHAT_STAGE_KEY
  );
}


/* =========================================================
   Conversation persistence
   ========================================================= */

function saveChat(
  messages,
  backendComplete = false
) {
  sessionStorage.setItem(
    CHAT_KEY,
    JSON.stringify({
      messages,
      backend_complete: backendComplete,
    })
  );
}


function getCurrentMessages() {
  const state = JSON.parse(
    sessionStorage.getItem(CHAT_KEY) || "null"
  );

  return state?.messages || [];
}


/* =========================================================
   Timing
   ========================================================= */

function sleep(milliseconds) {
  return new Promise((resolve) => {
    setTimeout(resolve, milliseconds);
  });
}


/* =========================================================
   Conversation rendering
   ========================================================= */

function createMessage(role, label) {
  const wrapper = document.createElement("article");

  wrapper.className =
    `chat-message chat-message--${role}`;

  const meta = document.createElement("div");

  meta.className = "chat-message-meta";
  meta.textContent = label;

  const bubble = document.createElement("div");

  bubble.className = "chat-bubble";

  wrapper.appendChild(meta);
  wrapper.appendChild(bubble);

  chatThread.appendChild(wrapper);

  return {
    wrapper,
    bubble,
  };
}


function scrollToLatest() {
  requestAnimationFrame(() => {
    chatThread.scrollTo({
      top: chatThread.scrollHeight,
      behavior: "smooth",
    });
  });
}


async function typeText(element, text) {
  element.textContent = "";

  for (const character of text) {
    element.textContent += character;

    scrollToLatest();

    await sleep(TYPE_SPEED);
  }
}


function saveMessage(
  role,
  label,
  text,
  backendComplete = false
) {
  const messages = getCurrentMessages();

  messages.push({
    role,
    label,
    text,
  });

  saveChat(
    messages,
    backendComplete
  );
}


async function typeMessage(
  role,
  label,
  text,
  backendComplete = false
) {
  const message = createMessage(
    role,
    label
  );

  await typeText(
    message.bubble,
    text
  );

  saveMessage(
    role,
    label,
    text,
    backendComplete
  );

  await sleep(MESSAGE_DELAY);

  return message;
}


function renderSavedMessages() {
  chatThread.innerHTML = "";

  const state = JSON.parse(
    sessionStorage.getItem(CHAT_KEY) || "null"
  );

  if (!state?.messages?.length) {
    return;
  }

  for (const message of state.messages) {
    const rendered = createMessage(
      message.role,
      message.label
    );

    rendered.bubble.textContent =
      message.text;
  }

  scrollToLatest();
}


/* =========================================================
   Typing indicator
   ========================================================= */

function createTypingIndicator() {
  const wrapper = document.createElement("article");

  wrapper.className =
    "chat-message chat-message--assistant chat-message--typing";

  const meta = document.createElement("div");

  meta.className =
    "chat-message-meta";

  meta.textContent =
    "Evolution";

  const bubble = document.createElement("div");

  bubble.className =
    "chat-bubble chat-bubble--typing";

  bubble.innerHTML = `
    <span></span>
    <span></span>
    <span></span>
  `;

  wrapper.appendChild(meta);
  wrapper.appendChild(bubble);

  chatThread.appendChild(wrapper);

  scrollToLatest();

  return wrapper;
}


/* =========================================================
   User's original submission
   ========================================================= */

function buildInitialUserMessage() {
  return [
    `Goal\n${plannerRequest.goal}`,
    `Starting point\n${plannerRequest.current_level}`,
    `Timeframe\n${plannerRequest.timeframe}`,
  ].join("\n\n");
}


async function showInitialUserSubmission() {
  await typeMessage(
    "user",
    "You",
    buildInitialUserMessage()
  );
}


/* =========================================================
   /plan
   ========================================================= */

async function requestPlannerExtraction() {
  if (!plannerRequest) {
    window.location.href = "/plan.html";
    return null;
  }

  const token = localStorage.getItem(
    TOKEN_KEY
  );

  if (!token) {
    window.location.href = "/";
    return null;
  }

  try {
    const response = await fetch(
      "/plan",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify(
          plannerRequest
        ),
      }
    );

    if (response.status === 401) {
      localStorage.removeItem(
        TOKEN_KEY
      );

      localStorage.removeItem(
        "evolution_user"
      );

      window.location.href = "/";

      return null;
    }

    let data = null;

    try {
      data = await response.json();
    } catch (_) {
      // Keep data as null.
    }

    if (!response.ok) {
      let detail =
        "Something went wrong while reading your answers.";

      if (data?.detail) {
        if (
          typeof data.detail === "string"
        ) {
          detail = data.detail;
        } else if (
          Array.isArray(data.detail)
        ) {
          detail = data.detail
            .map(
              (item) => item.msg
            )
            .join(". ");
        }
      }

      throw new Error(detail);
    }

    return data;

  } catch (error) {
    console.error(
      "Planner request failed:",
      error
    );

    return {
      error: true,
      message:
        error.message ||
        "Something went wrong while understanding your answers.",
    };
  }
}


/* =========================================================
   Clarification questions
   ========================================================= */

function getClarificationQuestions(
  extraction
) {
  if (!extraction) {
    return [];
  }

  return [
    ...(extraction.goal?.clarification_questions || [])
      .map((question) => ({
        category: "goal",
        question,
      })),

    ...(extraction.starting_point?.clarification_questions || [])
      .map((question) => ({
        category: "starting_point",
        question,
      })),

    ...(extraction.time_period?.clarification_questions || [])
      .map((question) => ({
        category: "time_period",
        question,
      })),
  ].filter(
    (item) =>
      typeof item.question === "string" &&
      item.question.trim()
  );
}


function normalizeQuestion(question) {
  return question
    .trim()
    .toLowerCase()
    .replace(/\s+/g, " ");
}


function questionKey(category, question) {
  return `${category}::${normalizeQuestion(question)}`;
}


function getPendingQuestions() {
  const extraction =
    getExtraction();

  const answers =
    getClarificationAnswers();

  const answeredQuestions =
    new Set(
      answers.map(
        (answer) =>
          questionKey(
            answer.category,
            answer.question
          )
      )
    );

  return getClarificationQuestions(
    extraction
  ).filter(
    (item) =>
      !answeredQuestions.has(
        questionKey(
          item.category,
          item.question
        )
      )
  );
}


/* =========================================================
   Composer
   ========================================================= */

function showComposer() {
  composer.hidden = false;

  answerInput.disabled = false;
  sendButton.disabled = false;

  requestAnimationFrame(() => {
    answerInput.focus();
  });
}


function hideComposer() {
  composer.hidden = true;

  answerInput.value = "";
  answerInput.disabled = true;
  sendButton.disabled = true;
}


function setComposerLoading(
  loading
) {
  answerInput.disabled = loading;
  sendButton.disabled = loading;

  if (loading) {
    sendButton.setAttribute(
      "aria-busy",
      "true"
    );
  } else {
    sendButton.removeAttribute(
      "aria-busy"
    );
  }
}


/* =========================================================
   Ask one clarification question
   ========================================================= */

async function askQuestion(question) {
  setStage("awaiting_answer");

  await typeMessage(
    "assistant",
    "Evolution",
    question.question
  );

  showComposer();
}


/* =========================================================
   /clarify
   ========================================================= */

function readError(data) {
  if (!data?.detail) {
    return (
      "Something went wrong while processing your answer."
    );
  }

  if (
    typeof data.detail === "string"
  ) {
    return data.detail;
  }

  if (
    Array.isArray(data.detail)
  ) {
    return data.detail
      .map(
        (item) => item.msg
      )
      .join(". ");
  }

  return (
    "Something went wrong while processing your answer."
  );
}


async function requestClarificationProcessing() {
  const extraction =
    getExtraction();

  const answers =
    getClarificationAnswers();

  if (!extraction) {
    throw new Error(
      "The planner context is missing."
    );
  }

  if (!answers.length) {
    return extraction;
  }

  const token =
    localStorage.getItem(
      TOKEN_KEY
    );

  if (!token) {
    window.location.href = "/";
    return null;
  }

  try {
    const response = await fetch(
      "/clarify",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${token}`,
        },
        body: JSON.stringify({
          extraction,
          answers,
        }),
      }
    );

    if (response.status === 401) {
      localStorage.removeItem(
        TOKEN_KEY
      );

      localStorage.removeItem(
        "evolution_user"
      );

      window.location.href = "/";

      return null;
    }

    let data = null;

    try {
      data = await response.json();
    } catch (_) {
      // Keep data as null.
    }

    if (!response.ok) {
      throw new Error(
        readError(data)
      );
    }

    return data;

  } catch (error) {
    console.error(
      "Clarification request failed:",
      error
    );

    throw error;
  }
}


/* =========================================================
   Process the current clarification batch
   ========================================================= */

async function processClarificationBatch() {
  hideComposer();

  setStage("clarifying");

  const typingIndicator =
    createTypingIndicator();

  try {
    const updatedExtraction =
      await requestClarificationProcessing();

    typingIndicator.remove();

    if (!updatedExtraction) {
      return;
    }

    /*
     * The new extraction becomes the only
     * source of truth from this point onward.
     */
    saveExtraction(
      updatedExtraction
    );

    /*
     * Those answers have now been consumed
     * by /clarify.
     */
    clearClarificationAnswers();

    await continueClarificationLoop();

  } catch (error) {
    typingIndicator.remove();

    await typeMessage(
      "assistant",
      "Evolution",
      error.message ||
        "I could not process that answer."
    );

    /*
     * Keep the answers in sessionStorage so
     * the current state is not silently lost.
     */
    setStage("awaiting_answer");

    const pending =
      getPendingQuestions();

    if (pending.length) {
      showComposer();
    }
  }
}


/* =========================================================
   Continue the clarification loop
   ========================================================= */

async function continueClarificationLoop() {
  const pending =
    getPendingQuestions();

  if (pending.length) {
    await askQuestion(
      pending[0]
    );

    return;
  }

  await finishClarification();
}


/* =========================================================
   Final state
   ========================================================= */

async function finishClarification() {
  hideComposer();

  setStage("complete");

  await typeMessage(
    "assistant",
    "Evolution",
    "We have enough to understand where you are going and where you are beginning."
  );

  await typeMessage(
    "assistant",
    "Evolution",
    "We can make your plan now."
  );

  showPlanCta();

  saveChat(
    getCurrentMessages(),
    true
  );
}


function showPlanCta() {
  planCta.hidden = false;

  requestAnimationFrame(() => {
    planCta.classList.add(
      "is-visible"
    );
  });
}


/* =========================================================
   Answer submission
   ========================================================= */

async function submitAnswer(event) {
  event.preventDefault();

  const answer =
    answerInput.value.trim();

  if (!answer) {
    return;
  }

  const pending =
    getPendingQuestions();

  if (!pending.length) {
    return;
  }

  const currentQuestion =
    pending[0];

  /*
   * Save the answer immediately.
   */
  const answers =
    getClarificationAnswers();

  answers.push({
    category:
      currentQuestion.category,

    question:
      currentQuestion.question,

    answer,
  });

  saveClarificationAnswers(
    answers
  );

  setComposerLoading(true);


  /*
   * Show the user's answer only after
   * it has been stored.
   */
  answerInput.value = "";

  await typeMessage(
    "user",
    "You",
    answer
  );


  /*
   * See whether there are more questions
   * in this current extraction.
   */
  const remaining =
    getPendingQuestions();

  if (remaining.length) {
    await askQuestion(
      remaining[0]
    );

    return;
  }


  /*
   * No questions remain in this batch.
   * Now — and only now — call /clarify.
   */
  await processClarificationBatch();
}


/* =========================================================
   Generate plan CTA
   ========================================================= */

generatePlanButton.addEventListener(
  "click",
  () => {
    /*
     * The plan-generation route does not exist
     * yet, so this button is intentionally only
     * the completed frontend state for now.
     *
     * The next backend step can connect it to
     * the actual plan-generation endpoint.
     */
    sessionStorage.setItem(
      "plan_generation_requested",
      "true"
    );
  }
);


/* =========================================================
   Theme
   ========================================================= */

function getSavedTheme() {
  const saved =
    localStorage.getItem(
      THEME_KEY
    );

  if (
    saved === "light" ||
    saved === "dark"
  ) {
    return saved;
  }

  return window.matchMedia(
    "(prefers-color-scheme: dark)"
  ).matches
    ? "dark"
    : "light";
}


function applyTheme(theme) {
  document.documentElement.dataset.theme =
    theme;

  localStorage.setItem(
    THEME_KEY,
    theme
  );

  const dark =
    theme === "dark";

  const toggle =
    document.getElementById(
      "chat-theme-toggle"
    );

  const label =
    document.getElementById(
      "chat-theme-label"
    );

  const icon =
    toggle.querySelector(
      ".theme-icon"
    );

  label.textContent =
    dark ? "Dark" : "Light";

  icon.textContent =
    dark ? "◐" : "☼";

  toggle.setAttribute(
    "aria-pressed",
    String(dark)
  );

  toggle.setAttribute(
    "aria-label",
    dark
      ? "Switch to light mode"
      : "Switch to dark mode"
  );
}


function setupTheme() {
  const toggle =
    document.getElementById(
      "chat-theme-toggle"
    );

  applyTheme(
    getSavedTheme()
  );

  toggle.addEventListener(
    "click",
    () => {
      const current =
        document.documentElement
          .dataset.theme ||
        "light";

      applyTheme(
        current === "dark"
          ? "light"
          : "dark"
      );
    }
  );
}


/* =========================================================
   Initial conversation
   ========================================================= */

async function startConversation() {
  if (!plannerRequest) {
    window.location.href =
      "/plan.html";

    return;
  }

  const existingExtraction =
    getExtraction();

  const existingMessages =
    getCurrentMessages();

  const stage =
    getStage();


  /*
   * Completed conversation.
   */
  if (
    stage === "complete" &&
    existingExtraction
  ) {
    renderSavedMessages();

    showPlanCta();

    return;
  }


  /*
   * If /plan has already completed,
   * restore the conversation and continue
   * from the current clarification state.
   */
  if (
    existingExtraction
  ) {
    renderSavedMessages();

    const answers =
      getClarificationAnswers();

    const pending =
      getPendingQuestions();

    if (
      answers.length &&
      !pending.length
    ) {
      await processClarificationBatch();

      return;
    }

    if (pending.length) {
      const lastMessage =
        getCurrentMessages()
          .at(-1);

      const lastMessageIsQuestion =
        lastMessage?.role ===
          "assistant" &&
        normalizeQuestion(
          lastMessage.text
        ) ===
          normalizeQuestion(
            pending[0].question
          );

      if (!lastMessageIsQuestion) {
        await askQuestion(
          pending[0]
        );
      } else {
        setStage(
          "awaiting_answer"
        );

        showComposer();
      }

      return;
    }

    await finishClarification();

    return;
  }


  /*
   * Completely fresh conversation.
   */
  chatThread.innerHTML = "";

  saveChat([], false);

  clearClarificationAnswers();

  setStage("initial");

  /*
   * First, write the entire original
   * submission.
   */
  await showInitialUserSubmission();


  /*
   * Only after the complete user message
   * has finished typing, show "...".
   */
  setStage("planning");

  const typingIndicator =
    createTypingIndicator();


  /*
   * Then call /plan.
   */
  const extraction =
    await requestPlannerExtraction();


  typingIndicator.remove();


  if (!extraction) {
    return;
  }


  if (extraction.error) {
    await typeMessage(
      "assistant",
      "Evolution",
      extraction.message
    );

    return;
  }


  saveExtraction(
    extraction
  );


  /*
   * Now begin the clarification loop.
   */
  await continueClarificationLoop();
}


/* =========================================================
   Start
   ========================================================= */

answerForm.addEventListener(
  "submit",
  submitAnswer
);

setupTheme();
startConversation();