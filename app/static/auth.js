const form = document.querySelector("form");
const message = document.getElementById("message");
const button = form.querySelector("button");
const mode = form.dataset.mode; // "login" or "register"

// Where to go after login. Change this when the planner page exists.
const NEXT_PAGE = "/plan.html";

function readError(data) {
  if (!data || !data.detail) return "Something went wrong. Try again.";
  if (typeof data.detail === "string") return data.detail;
  // FastAPI validation errors come as a list
  return data.detail.map((d) => d.msg).join(". ");
}

async function post(url, body) {
  const res = await fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  let data = null;
  try { data = await res.json(); } catch (_) {}
  if (!res.ok) throw new Error(readError(data));
  return data;
}

async function login(email, password) {
  const data = await post("/login", { email, password });
  localStorage.setItem("token", data.access_token);
  window.location.href = NEXT_PAGE;
}

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  message.textContent = "";
  button.disabled = true;

  const email = document.getElementById("email").value.trim();
  const password = document.getElementById("password").value;

  try {
    if (mode === "register") {
      const name = document.getElementById("name").value.trim();
      await post("/signup", { name, email, password });
    }
    await login(email, password);
  } catch (err) {
    message.textContent = err.message;
    button.disabled = false;
  }
});