const TOKEN_KEY = "token";
const EXTRACTION_KEY = "planner_extraction";

const thinkingMessages = [
    "Reading your goal and starting point...",
    "Finding relevant research...",
    "Comparing the available evidence...",
    "Turning the evidence into practical steps...",
    "Putting your roadmap together..."
];

const thinkingTitle = document.getElementById(
    "thinkingTitle"
);

const thinkingMessage = document.getElementById(
    "thinkingMessage"
);

const thinkingState = document.getElementById(
    "thinkingState"
);

const generatedPlan = document.getElementById(
    "generatedPlan"
);

const errorState = document.getElementById(
    "errorState"
);

const errorMessage = document.getElementById(
    "errorMessage"
);

const planStatus = document.getElementById(
    "planStatus"
);

const nextTaskButton = document.getElementById(
    "next-task-button"
);

const currentActionSection =
    document.querySelector(
        ".plan-current-action"
    );

const roadmapSection =
    document.querySelector(
        ".plan-card:has(#planSections)"
    );

let thinkingInterval = null;
let currentThinkingIndex = 0;
let generatedPlanData = null;


function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}


function formatDate(value) {
    if (!value) {
        return "";
    }

    const date = new Date(
        `${value}T00:00:00`
    );

    return new Intl.DateTimeFormat(
        "en-US",
        {
            month: "long",
            day: "numeric",
            year: "numeric",
        }
    ).format(date);
}


function startThinkingState() {
    currentThinkingIndex = 0;

    thinkingMessage.textContent =
        thinkingMessages[
            currentThinkingIndex
        ];

    thinkingInterval = setInterval(() => {
        currentThinkingIndex =
            (
                currentThinkingIndex + 1
            ) % thinkingMessages.length;

        thinkingMessage.textContent =
            thinkingMessages[
                currentThinkingIndex
            ];
    }, 2200);
}


function stopThinkingState() {
    if (thinkingInterval) {
        clearInterval(thinkingInterval);
        thinkingInterval = null;
    }
}


function showError(message) {
    stopThinkingState();

    thinkingState.classList.add(
        "hidden"
    );

    generatedPlan.classList.add(
        "hidden"
    );

    errorState.classList.remove(
        "hidden"
    );

    errorMessage.textContent =
        message;

    planStatus.textContent =
        "Unable to build plan";
}


function renderBulletList(items) {
    if (!items || !items.length) {
        return "<p>No additional details.</p>";
    }

    return items
        .map(
            (item) =>
                `<li>${escapeHtml(item)}</li>`
        )
        .join("");
}


function renderRequirements(
    requirements
) {
    const container =
        document.getElementById(
            "requirementsList"
        );

    if (
        !requirements ||
        !requirements.length
    ) {
        document
            .getElementById(
                "requirementsSection"
            )
            .classList.add("hidden");

        return;
    }

    container.innerHTML =
        requirements
            .map(
                (requirement) => `
                    <article class="plan-requirement">
                        <h3>
                            ${escapeHtml(
                                requirement.item
                            )}
                        </h3>

                        <p>
                            ${escapeHtml(
                                requirement.why_needed
                            )}
                        </p>
                    </article>
                `
            )
            .join("");
}


function renderSections(
    sections,
    currentActionTitle
) {
    const container =
        document.getElementById(
            "planSections"
        );

    container.innerHTML =
        sections
            .map(
                (section, sectionIndex) => {
                    const tasks =
                        section.tasks
                            .map(
                                (
                                    task,
                                    taskIndex
                                ) => {
                                    const isCurrent =
                                        normalizeText(
                                            task.title
                                        ) ===
                                        normalizeText(
                                            currentActionTitle
                                        );

                                    return `
                                        <article
                                            class="
                                                plan-task
                                                ${
                                                    isCurrent
                                                        ? "plan-task-current"
                                                        : ""
                                                }
                                            "
                                        >
                                            <div class="plan-task-number">
                                                ${sectionIndex + 1}.${taskIndex + 1}
                                            </div>

                                            <div class="plan-task-content">

                                                <div class="plan-task-title-row">
                                                    <h3>
                                                        ${escapeHtml(
                                                            task.title
                                                        )}
                                                    </h3>

                                                    ${
                                                        isCurrent
                                                            ? `
                                                                <span class="plan-task-badge">
                                                                    CURRENT
                                                                </span>
                                                            `
                                                            : ""
                                                    }
                                                </div>

                                            </div>
                                        </article>
                                    `;
                                }
                            )
                            .join("");

                    return `
                        <article class="plan-roadmap-section">

                            <div class="plan-roadmap-section-header">
                                <span class="plan-roadmap-number">
                                    ${sectionIndex + 1}
                                </span>

                                <div>
                                    <h3>
                                        ${escapeHtml(
                                            section.title
                                        )}
                                    </h3>

                                    <p>
                                        ${escapeHtml(
                                            section.purpose
                                        )}
                                    </p>
                                </div>
                            </div>

                            <div class="plan-task-list">
                                ${tasks}
                            </div>

                        </article>
                    `;
                }
            )
            .join("");
}


function renderSources(
    sources
) {
    const container =
        document.getElementById(
            "planSources"
        );

    if (
        !sources ||
        !sources.length
    ) {
        document
            .getElementById(
                "sourcesSection"
            )
            .classList.add(
                "hidden"
            );

        return;
    }

    container.innerHTML =
        sources
            .map(
                (source) => {
                    const authors =
                        source.authors &&
                        source.authors.length
                            ? source.authors.join(
                                ", "
                            )
                            : "Unknown authors";

                    return `
                        <article class="plan-source">

                            <span class="plan-source-id">
                                ${escapeHtml(
                                    source.source_id
                                )}
                            </span>

                            <div class="plan-source-content">

                                <h3>
                                    ${escapeHtml(
                                        source.title
                                    )}
                                </h3>

                                <p>
                                    ${escapeHtml(
                                        authors
                                    )}
                                    ${
                                        source.year
                                            ? ` · ${escapeHtml(source.year)}`
                                            : ""
                                    }
                                </p>

                                <p>
                                    Research angle:
                                    ${escapeHtml(
                                        source.angle
                                    )}
                                </p>

                                ${
                                    source.url
                                        ? `
                                            <a
                                                href="${escapeHtml(source.url)}"
                                                target="_blank"
                                                rel="noopener noreferrer"
                                            >
                                                View source
                                            </a>
                                        `
                                        : ""
                                }

                            </div>

                        </article>
                    `;
                }
            )
            .join("");
}

function normalizeText(value) {
    return String(value ?? "")
        .trim()
        .toLowerCase()
        .replace(/\s+/g, " ");
}


function setProgressFog(
    active
) {
    currentActionSection.classList.toggle(
        "plan-progress-fog",
        active
    );

    roadmapSection.classList.toggle(
        "plan-progress-fog",
        active
    );

    nextTaskButton.disabled =
        active;

    if (active) {
        nextTaskButton.setAttribute(
            "aria-busy",
            "true"
        );
    } else {
        nextTaskButton.removeAttribute(
            "aria-busy"
        );
    }
}


function updateCurrentAction(
    currentAction
) {
    document.getElementById(
        "currentActionTitle"
    ).textContent =
        currentAction.title;

    document.getElementById(
        "currentActionDescription"
    ).textContent =
        currentAction.description;

    document.getElementById(
        "currentActionCompletion"
    ).textContent =
        currentAction.completion_condition;
}


function updateProgressViews(
    plan
) {
    updateCurrentAction(
        plan.current_action
    );

    renderSections(
        plan.sections,
        plan.current_action.title
    );
}

function renderPlan(plan) {
    generatedPlanData =
        plan;

    document.getElementById(
        "planGoal"
    ).textContent =
        plan.goal;

    document.getElementById(
        "planEncouragement"
    ).textContent =
        plan.encouragement;

    document.getElementById(
        "planStartingPoint"
    ).textContent =
        plan.starting_point;

    document.getElementById(
        "planTimeframe"
    ).textContent =
        `${formatDate(plan.start_date)} — ${formatDate(plan.end_date)}`;

    document.getElementById(
        "feasibilityAssessment"
    ).textContent =
        plan.feasibility.assessment;

    document.getElementById(
        "feasibilityReasons"
    ).innerHTML =
        renderBulletList(
            plan.feasibility.reasons
        );

    document.getElementById(
        "feasibilityConstraints"
    ).innerHTML =
        renderBulletList(
            plan.feasibility.constraints
        );

    document.getElementById(
        "feasibilityUncertainty"
    ).textContent =
        plan.feasibility.uncertainty;

    document.getElementById(
        "currentActionTitle"
    ).textContent =
        plan.current_action.title;

    document.getElementById(
        "currentActionDescription"
    ).textContent =
        plan.current_action.description;

    document.getElementById(
        "currentActionCompletion"
    ).textContent =
        plan.current_action.completion_condition;

    renderRequirements(
        plan.requirements
    );

    renderSections(
        plan.sections,
        plan.current_action.title
    );

    renderSources(
        plan.sources
    );

    stopThinkingState();

    thinkingState.classList.add(
        "hidden"
    );

    generatedPlan.classList.remove(
        "hidden"
    );

    planStatus.textContent =
        "Your plan is ready";

    window.scrollTo({
        top: 0,
        behavior: "instant",
    });
}


function buildPlainTextPlan(
    plan
) {
    const lines = [];

    lines.push(
        "EVOLUTION PLAN"
    );
    lines.push("");
    lines.push(
        plan.goal
    );
    lines.push("");

    if (plan.goal_conditions?.length) {
        lines.push(
            "GOAL CONDITIONS"
        );

        for (
            const condition of
            plan.goal_conditions
        ) {
            lines.push(
                `- ${condition}`
            );
        }

        lines.push("");
    }

    lines.push(
        "STARTING POINT"
    );
    lines.push(
        plan.starting_point
    );
    lines.push("");

    lines.push(
        `TIMEFRAME: ${plan.start_date} to ${plan.end_date}`
    );
    lines.push("");

    lines.push(
        "ENCOURAGEMENT"
    );
    lines.push(
        plan.encouragement
    );
    lines.push("");

    lines.push(
        "FEASIBILITY"
    );
    lines.push(
        plan.feasibility.assessment
    );
    lines.push("");

    if (
        plan.feasibility.reasons?.length
    ) {
        lines.push(
            "WHY THIS IS REALISTIC"
        );

        for (
            const reason of
            plan.feasibility.reasons
        ) {
            lines.push(
                `- ${reason}`
            );
        }

        lines.push("");
    }

    if (
        plan.feasibility.constraints?.length
    ) {
        lines.push(
            "CONSTRAINTS"
        );

        for (
            const constraint of
            plan.feasibility.constraints
        ) {
            lines.push(
                `- ${constraint}`
            );
        }

        lines.push("");
    }

    lines.push(
        "CURRENT ACTION"
    );
    lines.push(
        plan.current_action.title
    );
    lines.push(
        plan.current_action.description
    );
    lines.push(
        `Complete when: ${plan.current_action.completion_condition}`
    );
    lines.push("");

    lines.push(
        "ROADMAP"
    );

    plan.sections.forEach(
        (section, sectionIndex) => {
            lines.push("");
            lines.push(
                `${sectionIndex + 1}. ${section.title}`
            );
            lines.push(
                section.purpose
            );

            section.tasks.forEach(
                (
                    task,
                    taskIndex
                ) => {
                    lines.push(
                        `   ${sectionIndex + 1}.${taskIndex + 1} ${task.title}`
                    );
                }
            );
        }
    );

    lines.push("");

    lines.push(
        "SOURCES"
    );

    plan.sources?.forEach(
        (source) => {
            lines.push(
                `${source.source_id}: ${source.title}`
            );
        }
    );

    return lines.join("\n");
}


async function copyPlan() {
    const button =
        document.getElementById(
            "copyPlanButton"
        );

    const status =
        document.getElementById(
            "copyStatus"
        );

    if (!generatedPlanData) {
        return;
    }

    const text =
        buildPlainTextPlan(
            generatedPlanData
        );

    try {
        await navigator.clipboard.writeText(
            text
        );

        button.textContent =
            "Plan copied";

        status.textContent =
            "Your plan has been copied to the clipboard.";

        setTimeout(() => {
            button.textContent =
                "Copy plan";
        }, 2000);

    } catch (error) {
        status.textContent =
            "Copying failed. Please select and copy the plan manually.";
    }
}


async function generatePlan() {
    const token =
        localStorage.getItem(
            TOKEN_KEY
        );

    const extractionRaw =
        sessionStorage.getItem(
            EXTRACTION_KEY
        );

    if (!token) {
        showError(
            "Your session has expired. Please log in again."
        );

        return;
    }

    if (!extractionRaw) {
        showError(
            "Your finalized planner information could not be found. Please return to the planner."
        );

        return;
    }

    let extraction;

    try {
        extraction =
            JSON.parse(
                extractionRaw
            );
    } catch {
        showError(
            "Your planner information could not be read."
        );

        return;
    }

    startThinkingState();

    try {
        const response =
            await fetch(
                "/generate-plan",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${token}`,
                    },

                    body: JSON.stringify({
                        extraction,
                    }),
                }
            );

        const data =
            await response.json();

        if (!response.ok) {
            throw new Error(
                data.detail ||
                "Unable to generate your plan."
            );
        }

        sessionStorage.setItem(
            "plan_result",
            JSON.stringify(data)
        );

        renderPlan(
            data
        );

    } catch (error) {
        showError(
            error.message ||
            "Something went wrong while generating your plan."
        );
    }
}

async function advanceToNextTask() {
    if (!generatedPlanData) {
        return;
    }

    const token =
        localStorage.getItem(
            TOKEN_KEY
        );

    if (!token) {
        showError(
            "Your session has expired. Please log in again."
        );

        return;
    }

    setProgressFog(
        true
    );

    planStatus.textContent =
        "Finding your next step";

    try {
        const response =
            await fetch(
                "/next-task",
                {
                    method: "POST",

                    headers: {
                        "Content-Type":
                            "application/json",

                        "Authorization":
                            `Bearer ${token}`,
                    },

                    body: JSON.stringify(
                        generatedPlanData
                    ),
                }
            );

        let data = null;

        try {
            data =
                await response.json();
        } catch (_) {
            // Keep data as null.
        }

        if (response.status === 401) {
            localStorage.removeItem(
                TOKEN_KEY
            );

            localStorage.removeItem(
                "evolution_user"
            );

            window.location.href = "/";

            return;
        }

        if (response.status === 409) {
            throw new Error(
                data?.detail ||
                "You have reached the end of your plan."
            );
        }

        if (!response.ok) {
            throw new Error(
                data?.detail ||
                "Unable to move to the next task."
            );
        }

        /*
         * Store the returned plan first so the
         * browser session always contains the
         * latest progression state.
         */
        sessionStorage.setItem(
            "plan_result",
            JSON.stringify(data)
        );

        generatedPlanData =
            data;

        /*
         * Replace only the two progression views:
         * current action + roadmap.
         */
        updateProgressViews(
            data
        );

        /*
         * Allow the updated content to exist
         * underneath the fog before revealing it.
         */
        requestAnimationFrame(() => {
            setProgressFog(
                false
            );
        });

        planStatus.textContent =
            "Your plan is ready";

    } catch (error) {
        setProgressFog(
            false
        );

        planStatus.textContent =
            "Your plan is ready";

        /*
         * Keep the old plan visible if the
         * progression request fails.
         */
        document.getElementById(
            "copyStatus"
        ).textContent =
            error.message ||
            "Something went wrong while moving to the next task.";
    }
}

nextTaskButton.addEventListener(
    "click",
    advanceToNextTask
);

document.addEventListener(
    "DOMContentLoaded",
    () => {
        document
            .getElementById("copyPlanButton")
            .addEventListener(
                "click",
                copyPlan
            );

        setupTheme();

        const cachedPlan =
            sessionStorage.getItem(
                "plan_result"
            );

        if (cachedPlan) {
            try {
                renderPlan(
                    JSON.parse(cachedPlan)
                );
                return;
            } catch (_) {
                sessionStorage.removeItem(
                    "plan_result"
                );
            }
        }

        generatePlan();
    }
);

function getSavedTheme() {
    const saved =
        localStorage.getItem(
            "evolution_theme"
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
        "evolution_theme",
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