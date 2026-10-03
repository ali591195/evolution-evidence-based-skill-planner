const form = document.getElementById("plan-form");
const message = document.getElementById("message");
const button = form.querySelector("button");
const status = document.getElementById("status");
const statusText = document.getElementById("status-text");

const themeToggle = document.getElementById("theme-toggle");
const themeLabel = document.getElementById("theme-label");
const themeIcon = themeToggle.querySelector(".theme-icon");
const skipButton = document.getElementById("skip-button");

const adventurerName = document.getElementById("adventurer-name");
const scenes = document.querySelectorAll(".story-scene");

const TOKEN_KEY = "token";
const USER_KEY = "evolution_user";

function readError(data) {
  if (!data || !data.detail) {
    return "Something went wrong. Try again.";
  }

  if (typeof data.detail === "string") {
    return data.detail;
  }

  return data.detail.map((d) => d.msg).join(". ");
}

async function getCurrentUser() {
  const token = localStorage.getItem(TOKEN_KEY);

  if (!token) {
    window.location.href = "/";
    return null;
  }

  const res = await fetch("/me", {
    headers: {
      "Authorization": `Bearer ${token}`,
    },
  });

  if (res.status === 401) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    window.location.href = "/";
    return null;
  }

  if (!res.ok) {
    throw new Error("Unable to open your journal. Please try again.");
  }

  const user = await res.json();
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  return user;
}

function showCachedUser() {
  const cached = localStorage.getItem(USER_KEY);

  if (!cached) return;

  try {
    const user = JSON.parse(cached);

    if (user.name) {
      adventurerName.textContent = user.name;
    }
  } catch (_) {
    localStorage.removeItem(USER_KEY);
  }
}

async function loadUser() {
  showCachedUser();

  try {
    const user = await getCurrentUser();

    if (user && user.name) {
      adventurerName.textContent = user.name;
    }
  } catch (error) {
    message.textContent = error.message;
  }
}

function getSavedTheme() {
  const saved = localStorage.getItem("evolution_theme");

  if (saved === "light" || saved === "dark") {
    return saved;
  }

  return window.matchMedia("(prefers-color-scheme: dark)").matches
    ? "dark"
    : "light";
}

function applyTheme(theme) {
  document.documentElement.dataset.theme = theme;
  localStorage.setItem("evolution_theme", theme);

  const dark = theme === "dark";

  themeLabel.textContent = dark ? "Dark" : "Light";
  themeIcon.textContent = dark ? "◐" : "☼";
  themeToggle.setAttribute("aria-pressed", String(dark));
  themeToggle.setAttribute(
    "aria-label",
    dark ? "Switch to light mode" : "Switch to dark mode"
  );
}

function setupTheme() {
  applyTheme(getSavedTheme());

  themeToggle.addEventListener("click", () => {
    const current = document.documentElement.dataset.theme;
    applyTheme(current === "dark" ? "light" : "dark");
  });
}

function setupStory() {
  if (!scenes.length) return;

  const observer = new IntersectionObserver(
    (entries) => {
      const visible = entries
        .filter((entry) => entry.isIntersecting)
        .sort((a, b) => b.intersectionRatio - a.intersectionRatio);

      if (!visible.length) return;

      scenes.forEach((scene) => {
        scene.classList.remove("is-active");
      });

      visible[0].target.classList.add("is-active");
    },
    {
      threshold: [0.35, 0.6, 0.8],
      rootMargin: "-12% 0px -12% 0px",
    }
  );

  scenes.forEach((scene) => observer.observe(scene));

  scenes[0].classList.add("is-active");
}

function skipToForm() {
  const goal = document.getElementById("goal");

  if (!goal) return;

  goal.scrollIntoView({
    behavior: "smooth",
    block: "center",
  });

  window.setTimeout(() => {
    goal.focus({ preventScroll: true });
  }, 600);
}

form.addEventListener("submit", (event) => {
  event.preventDefault();

  message.textContent = "";

  const goal = document.getElementById("goal").value.trim();
  const currentLevel = document.getElementById("level").value.trim();
  const timeframe = document.getElementById("timeframe").value.trim();

  if (!goal || !currentLevel || !timeframe) {
    message.textContent = "Please fill in all three fields before continuing.";
    return;
  }

  const plannerRequest = {
    goal,
    current_level: currentLevel,
    timeframe,
  };

  sessionStorage.setItem(
    "planner_request",
    JSON.stringify(plannerRequest)
  );

  sessionStorage.removeItem("evolution_chat");
  sessionStorage.removeItem("planner_extraction");
  sessionStorage.removeItem("plan_result");

  window.location.href = "/chat.html";
});

setupTheme();
setupStory();
skipButton.addEventListener("click", skipToForm);
loadUser();