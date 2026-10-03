import json
import time
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from dataclasses import dataclass

from groq import Groq

from app.schemas.planner import (
    ClarificationAnswer,
    PlannerExtraction,
    DATE_FORMAT,
    ClarificationProcessResult,
    GeneratedPlan,
    GeneratedPlanContent,
    PlanGenerationIn,
    PlanSource,
    ResearchQuery,
    ResearchQuerySet, CurrentAction,
)


MODEL = "qwen/qwen3.8-27b"
MAX_COMPLETION_TOKENS = 900

client = Groq(api_key=os.environ["GROQ_API_KEY"])


PROMPTS = {
    "goal": """
Extract the user's actual improvement goal from their answer.

Separate:
- goal: the core thing they want to become better at
- conditions: meaningful conditions attached to that goal
- clarification_questions: only the few questions that are materially necessary
  to understand the goal or its conditions better

Do not turn every possible missing detail into a question.
Do not nitpick wording.
Do not invent information that the user did not provide.

Examples:
"Learn to speak English with confidence."
goal = "speak English"
conditions = ["with confidence"]

"Learn to play my favourite songs."
goal = "play songs on guitar"
conditions = ["the user's favourite songs"]

A useful clarification might then be:
"What are some of your favourite songs?"

Ask questions only when the answer could materially change the eventual
improvement plan. Prefer the smallest number of useful questions.
""",

    "starting_point": """
Extract the user's actual starting point from their answer.

Return:
- starting_point: what the user can currently do, knows, or has already
  experienced
- clarification_questions: only the few questions needed when their current
  level is materially ambiguous

Do not assume a skill level from vague confidence words.
Do not ask for tiny details that would not change the plan.
Do not invent experience the user did not mention.

The purpose is to understand where the person is starting, not to interrogate
them.
""",

    "time_period": """
Interpret the user's timeframe as a concrete date range.

Return:
- start_date: the starting date of the improvement period in YYYY-MM-DD
  format
- end_date: the ending date of the improvement period in YYYY-MM-DD format
- clarification_questions: only the few questions that are materially
  necessary when the timeframe cannot be converted reliably into dates

IMPORTANT TEMPORAL RULES:
- Every returned date must be today or later.
- Never return a date that has already passed.
- When a relative expression can refer to either a past or future occurrence,
  always choose the next future occurrence.
- "This summer" means the current year's summer only when summer has not yet
  ended. If today's date is already after summer, "this summer" is no longer
  a valid future period.
- "Next summer" always means the next upcoming summer after today.
- For Pakistan and the Northern Hemisphere, summer should be interpreted as
  approximately June through August.
- Therefore, if the current date is after August, "next summer" refers to
  June-August of the following year.
- Do not ask for clarification merely because the current year's occurrence
  has already passed when the natural future interpretation is obvious.
- If the user's wording clearly identifies a future period, convert it directly
  into dates instead of asking a question.

IMPORTANT:
- Never return a relative phrase such as "6 months", "by the end of this year",
  "next summer", or "in a few months" in start_date or end_date.
- start_date and end_date must be exact calendar dates in YYYY-MM-DD format
  whenever they can be determined.
- Use today's date as the start date for duration-based goals such as
  "6 months" or "for one year".
- For deadline expressions such as "by the end of this year", use today's date
  as start_date and the actual future deadline as end_date.
- For a seasonal PERIOD such as "next summer", use the actual seasonal range:
  start_date = the beginning of that future summer
  end_date = the end of that future summer.
- For a deadline expression such as "by next summer", use today's date as
  start_date and the end of the next summer as end_date.
- Do not invent a precise date when the user's wording genuinely does not
  support one.
- If a required date genuinely cannot be determined, return null for that
  date and ask the minimum clarification question needed.
- If the timeframe is clear, return an empty clarification_questions list.

Examples:

Current date: 2026-10-03

"6 months"
start_date = "2026-10-03"
end_date = "2027-04-03"
clarification_questions = []

"by the end of this year"
start_date = "2026-10-03"
end_date = "2026-12-31"
clarification_questions = []

"next summer"
start_date = "2027-06-01"
end_date = "2027-08-31"
clarification_questions = []

"by next summer"
start_date = "2026-10-03"
end_date = "2027-08-31"
clarification_questions = []

"before my next big presentation"
start_date = "2026-10-03"
end_date = null
clarification_questions = ["When is your presentation?"]

Never interpret "next summer" as a summer that has already passed.
""",
}


def build_prompt(
    goal: str,
    current_level: str,
    timeframe: str,
) -> str:
    now = datetime.now(ZoneInfo("Asia/Karachi"))
    current_date = now.strftime("%Y-%m-%d")
    current_datetime = now.strftime(
        "%A, %d %B %Y at %I:%M %p PKT"
    )

    schema = PlannerExtraction.model_json_schema()

    return f"""
You are the intake interpreter for Evolution, an evidence-grounded
improvement planner.

Your job is to understand the person before planning anything.

You will receive three raw answers:
1. Goal
2. Starting point
3. Timeframe

Analyze all three, but keep their interpretations separate.

IMPORTANT RULES:
- Do not invent facts.
- Do not assume missing details.
- Ask clarification questions only when the answer would materially affect
  understanding or planning.
- Prefer one strong clarification question over several small ones.
- If an answer is sufficiently clear, return an empty clarification list.
- The person should feel understood, not interrogated.
- Do not provide advice or create a plan yet.
- Only extract and clarify.

GOAL EXTRACTION:
{PROMPTS["goal"]}

STARTING POINT EXTRACTION:
{PROMPTS["starting_point"]}

TIMEFRAME EXTRACTION:
{PROMPTS["time_period"]}

CURRENT DATE:
{current_date}

CURRENT DATE AND TIME:
{current_datetime}

VERY IMPORTANT:
The current date is the lower boundary for every date you return.

No returned start_date or end_date may be earlier than:
{current_date}

When interpreting relative time:
- Prefer the future occurrence.
- Never select an occurrence that has already passed.
- If a phrase such as "next summer" appears after the current summer has ended,
  it refers to the following year's summer.
- Do not ask a clarification question when the future interpretation is
  unambiguous.

USER'S GOAL:
{goal}

USER'S STARTING POINT:
{current_level}

USER'S TIMEFRAME:
{timeframe}

Before producing the response, reason about whether each part is sufficiently
clear to proceed.

For clarification questions:
- Ask only what is necessary.
- Prefer the smallest number of questions that removes meaningful ambiguity.
- Do not ask questions merely because additional information might be useful.
- Do not ask several questions when one question can resolve the uncertainty.
- Never fabricate an answer just to avoid asking a necessary question.

For the timeframe specifically:
- start_date and end_date must be exact calendar dates in YYYY-MM-DD format
  whenever they can be determined.
- A date before {current_date} is invalid.
- Never return natural-language timeframe expressions in those fields.

Return only the structured response described by this schema.

JSON SCHEMA:
{json.dumps(schema, indent=2)}
"""


def extract(
    goal: str,
    current_level: str,
    timeframe: str,
) -> dict:
    prompt = build_prompt(
        goal,
        current_level,
        timeframe,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Extract the requested information and return only the "
                    "structured JSON response."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        reasoning_effort="none",
        reasoning_format="hidden",
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "planner_extraction",
                "strict": True,
                "schema": PlannerExtraction.model_json_schema(),
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError("The LLM returned an empty response")

    data = json.loads(content)

    result = PlannerExtraction.model_validate(data)

    today = datetime.now(ZoneInfo("Asia/Karachi")).date()

    for value in (
        result.time_period.start_date,
        result.time_period.end_date,
    ):
        if value is None:
            continue

        parsed = datetime.strptime(
            value,
            "%Y-%m-%d",
        ).date()

        if parsed < today:
            raise ValueError(
                "The LLM returned a timeframe date in the past"
            )

    return result.model_dump()


CLARIFICATION_PROMPT = """
You are the clarification processor for Evolution, an evidence-grounded
improvement planner.

You receive:
1. the current PlannerExtraction
2. one clarification question
3. the user's answer to that question

Your job is to determine whether the answer resolves the question and update
the extraction accordingly.

There are three possible outcomes.

1. ANSWERED
The answer clearly resolves the uncertainty behind the question.

Set:
- answered = true
- defer_question = false
- follow_up_question = null

Update the relevant part of the extraction using the information supported
by the answer.

The original question must be removed from that category's
clarification_questions.

2. PARTIALLY ANSWERED
The answer gives useful information, but does not fully resolve the original
question.

Set:
- answered = false
- defer_question = false
- follow_up_question = one NEW, more specific question

The extraction may include the useful information explicitly provided by
the user.

The original question must NOT remain unchanged.

The follow-up question must target only the remaining uncertainty.

3. NOT ANSWERABLE YET
The answer cannot reasonably answer the question because a prerequisite is
missing or the question depends on another unresolved part of the intake.

Set:
- answered = false
- defer_question = true
- follow_up_question = null

Do not invent information.

The original question should be removed for now rather than repeated.

It can be introduced again later when its prerequisite becomes known.

IMPORTANT:
- Never invent facts.
- Never infer information the user did not provide.
- Never treat sarcasm, frustration, uncertainty, or an unrelated response
  as a successful answer.
- Do not punish the user for not knowing something.
- Do not ask the same clarification question twice.
- A follow-up question must be materially different from the original.
- A follow-up question must be easier and more specific than the original.
- If the answer explicitly explains why the question cannot yet be answered,
  prefer defer_question=true.

GOAL EXAMPLE:

Question:
"Since you are open to suggestions, would you prefer to focus on a physical
skill, a creative hobby, or a professional skill?"

Answer:
"Choose something unique for me."

Interpretation:
The user has not selected an actual skill, so the question is not fully
answered. However, they have explicitly stated that they want Evolution to
choose something unique.

Therefore:
- answered = false
- defer_question = false
- add the supported condition that the user wants Evolution to choose a
  unique skill
- replace the original question with a more useful question, for example
  asking whether there are any types of activities the user definitely wants
  to avoid.

STARTING-POINT EXAMPLE:

Question:
"Could you please describe your current level or experience regarding this
goal?"

Answer:
"How would I know when I haven't even decided the goal?"

Interpretation:
The user cannot reasonably answer the starting-point question because the
goal itself is unresolved.

Therefore:
- answered = false
- defer_question = true
- do not invent a starting point
- do not repeat the same starting-point question

Later, once the goal becomes concrete, a new starting-point clarification
can be introduced.

GOAL:
Only update goal or conditions using actual information from the answer.

STARTING POINT:
Only update starting_point using explicit information about the user's
current abilities, experience, knowledge, or situation.

TIME PERIOD:
Only update dates when the answer gives enough information to determine
them reliably.

TIME RULES:
- Every returned date must be today or later.
- Never return a date in the past.
- Dates must use YYYY-MM-DD.
- Do not invent precision.
- If a date cannot be determined reliably, keep it null and ask the minimum
  useful clarification question.

CLARIFICATION QUESTION QUALITY:
- One focused question is better than several small questions.
- Ask only what materially affects understanding or planning.
- Do not interrogate the user.
- Never repeat the original question verbatim as the follow-up.

Return only the structured ClarificationProcessResult.
"""

FALLBACK_QUESTIONS = {
    "goal": (
        "What is one specific skill or ability you would like "
        "to become better at?"
    ),
    "starting_point": (
        "Now that we know the goal, what can you currently do "
        "in that skill, even if you are a complete beginner?"
    ),
    "time_period": (
        "What future date would you like to work toward?"
    ),
}


def normalize_text(value: str) -> str:
    return " ".join(
        value.lower().strip().split()
    )


def _remove_question(
    extraction: PlannerExtraction,
    category: str,
    question: str,
) -> PlannerExtraction:
    data = extraction.model_dump()

    questions = data[category][
        "clarification_questions"
    ]

    target = normalize_text(question)

    data[category]["clarification_questions"] = [
        item
        for item in questions
        if normalize_text(item) != target
    ]

    return PlannerExtraction.model_validate(data)


def _replace_question(
    extraction: PlannerExtraction,
    category: str,
    original_question: str,
    new_question: str,
) -> PlannerExtraction:
    data = extraction.model_dump()

    questions = data[category][
        "clarification_questions"
    ]

    original = normalize_text(
        original_question
    )

    replacement = new_question.strip()

    updated = []

    replaced = False

    for question in questions:
        if normalize_text(question) == original:
            if not replaced:
                updated.append(replacement)
                replaced = True
            continue

        updated.append(question)

    if not replaced:
        updated.append(replacement)

    deduplicated = []
    seen = set()

    for question in updated:
        normalized = normalize_text(question)

        if normalized in seen:
            continue

        seen.add(normalized)
        deduplicated.append(question)

    data[category][
        "clarification_questions"
    ] = deduplicated

    return PlannerExtraction.model_validate(data)


def _ensure_future_dates(
    extraction: PlannerExtraction,
) -> None:
    today = datetime.now(
        ZoneInfo("Asia/Karachi")
    ).date()

    for value in (
        extraction.time_period.start_date,
        extraction.time_period.end_date,
    ):
        if value is None:
            continue

        parsed = datetime.strptime(
            value,
            DATE_FORMAT,
        ).date()

        if parsed < today:
            raise ValueError(
                "The LLM returned a timeframe date in the past"
            )


def _add_starting_point_question_if_needed(
    extraction: PlannerExtraction,
) -> PlannerExtraction:
    data = extraction.model_dump()

    goal = data["goal"]["goal"]
    starting_point = data["starting_point"][
        "starting_point"
    ]

    starting_questions = data[
        "starting_point"
    ]["clarification_questions"]

    goal_is_known = (
        goal.strip().lower()
        not in {"", "unknown", "undetermined"}
    )

    starting_point_is_unknown = (
        starting_point.strip().lower()
        in {"", "unknown", "undetermined"}
    )

    if (
        goal_is_known
        and starting_point_is_unknown
        and not starting_questions
    ):
        starting_questions.append(
            FALLBACK_QUESTIONS["starting_point"]
        )

    return PlannerExtraction.model_validate(data)


def build_clarification_prompt(
    extraction: PlannerExtraction,
    answer: ClarificationAnswer,
) -> str:
    now = datetime.now(
        ZoneInfo("Asia/Karachi")
    )

    current_date = now.strftime(
        "%Y-%m-%d"
    )

    current_datetime = now.strftime(
        "%A, %d %B %Y at %I:%M %p PKT"
    )

    schema = ClarificationProcessResult.model_json_schema()

    extraction_data = extraction.model_dump()

    answer_data = answer.model_dump()

    return f"""
{CLARIFICATION_PROMPT}

CURRENT DATE:
{current_date}

CURRENT DATE AND TIME:
{current_datetime}

CURRENT EXTRACTION:
{json.dumps(extraction_data, indent=2)}

QUESTION CATEGORY:
{answer.category}

QUESTION:
{answer.question}

USER ANSWER:
{answer.answer}

Before returning the response, explicitly determine:

- Did the answer actually resolve the question?
- If not, did it at least provide useful partial information?
- Does the question depend on another unresolved part of the intake?
- Should the question be removed, replaced, or deferred?

For a partial answer, the follow-up question must be different from:

{answer.question}

If the user cannot answer because a prerequisite is unresolved, do NOT ask
the same question again. Use defer_question=true.

The final response must conform exactly to this schema:

JSON SCHEMA:
{json.dumps(schema, indent=2)}
"""


def process_clarification_answer(
    extraction: PlannerExtraction,
    answer: ClarificationAnswer,
) -> PlannerExtraction:
    prompt = build_clarification_prompt(
        extraction,
        answer,
    )

    response = client.chat.completions.create(
        model=MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Process the clarification answer and return only the "
                    "structured clarification result."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        reasoning_effort="none",
        reasoning_format="hidden",
        max_completion_tokens=MAX_COMPLETION_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "clarification_process_result",
                "strict": True,
                "schema": (
                    ClarificationProcessResult
                    .model_json_schema()
                ),
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "The LLM returned an empty response"
        )

    data = json.loads(content)

    result = (
        ClarificationProcessResult
        .model_validate(data)
    )

    current = extraction

    target_category = answer.category

    if result.defer_question:
        return _remove_question(
            current,
            target_category,
            answer.question,
        )

    updated = result.extraction

    if result.answered:
        return _remove_question(
            updated,
            target_category,
            answer.question,
        )

    follow_up = (
            result.follow_up_question or ""
    ).strip()

    original_normalized = normalize_text(
        answer.question
    )

    if (
            not follow_up
            or normalize_text(follow_up)
            == original_normalized
    ):
        follow_up = FALLBACK_QUESTIONS[
            target_category
        ]

    return _replace_question(
        updated,
        target_category,
        answer.question,
        follow_up,
    )


def clarify(
        extraction: PlannerExtraction,
        answers: list[ClarificationAnswer],
) -> dict:
    current = extraction

    for answer in answers:
        current = process_clarification_answer(
            current,
            answer,
        )

        current = (
            _add_starting_point_question_if_needed(
                current
            )
        )

    _ensure_future_dates(current)

    return current.model_dump()

SEMANTIC_SCHOLAR_URL = (
    "https://api.semanticscholar.org/graph/v1/paper/search"
)

PLAN_MODEL = "openai/gpt-oss-120b"
PLAN_MAX_COMPLETION_TOKENS = 2800


@dataclass
class ResearchSource:
    source_id: str
    angle: str
    query: str
    paper_id: str
    title: str
    abstract: str | None
    year: int | None
    authors: list[str]
    url: str | None


RESEARCH_QUERY_PROMPT = """
You are the research-query generator for Evolution.

Evolution receives a finalized understanding of a person's improvement goal.

Your job is to create exactly THREE distinct research queries about the
actual goal.

The three queries must approach the goal from genuinely different angles.

Prefer angles such as:
1. learning or skill-acquisition evidence
2. effective practice, training, or intervention methods
3. transfer, retention, performance, constraints, or feasibility

Choose the angles that make the most sense for the specific goal.

IMPORTANT:
- Start from the actual goal, not vague wording from the original user input.
- Use the goal conditions when they materially narrow the research.
- Queries must be plain natural-language search strings.
- Do not use Boolean operators.
- Do not make the three queries near-duplicates.
- Each query should be useful for finding research that contributes a
  different part of the eventual plan.
- Do not ask questions.
- Do not create a plan.
- Do not invent research findings.

Return exactly three queries.
"""


PLAN_GENERATION_PROMPT = """
You are the final planning engine for Evolution, an evidence-grounded skill
improvement planner.

You receive:
- a finalized goal
- goal conditions
- starting point
- exact start and end dates
- research queries
- up to three research papers and their abstracts

Your job is to turn this information into a practical plan that is written
FOR THE PERSON and feels like the plan is speaking directly to them.

STRICT JSON RULES:
- Return valid JSON only.
- Never use Markdown syntax inside the JSON.
- Never use **bold**, *italics*, backticks, comments, or trailing commas.
- Every string value must use normal double quotes.
- Do not put Markdown formatting around any JSON value.
- Example of valid JSON:
  "title": "Integrate Grammar in Context"
- Never produce:
  "title": **"Integrate Grammar in Context"**

This is NOT a research report.
This is NOT a report about the user.
This is NOT a description of what "the user" should do.

Write the plan as something the person can read and immediately follow.

VOICE AND PRESENTATION:
- Speak directly to the person using "you" and "your".
- Make the plan feel personal, practical, and encouraging.
- Do not refer to "the user", "the person", "they", or "their user profile".
- Do not write like a research paper, assessment report, or case study.
- Do not write meta-commentary about the planning process.
- Do not explain what Evolution is doing internally.
- Keep explanations concise, concrete, and useful.
- Prefer direct wording such as:
  "You already know a few basic chords..."
  "Start by..."
  "Your first milestone is..."
  "You are ready to move on when..."
- Avoid wording such as:
  "The user should..."
  "The user is..."
  "The plan recommends..."
  "Research demonstrates that the user..."

EVIDENCE RULES:
- Treat supplied paper records as research evidence when they are available.
- Do not claim a study found something that is not supported by its supplied
  title or abstract.
- Do not invent statistics, effect sizes, timelines, exercises, equipment,
  or findings.
- Distinguish research-supported ideas from practical recommendations.
- Do not pretend that a paper supports a recommendation when it does not.
- Do not pretend that a small number of papers establishes universal truth.
- Do not fabricate details from papers whose abstracts do not contain those
  details.

RESEARCH FALLBACK:
- Research evidence may be unavailable if all Semantic Scholar searches fail.
- If no research evidence is supplied, use your general knowledge to create
  a practical plan.
- When using general knowledge, do NOT present it as research-backed.
- Explicitly state in feasibility.uncertainty that no usable research source
  was retrieved for this plan.
- Requirements, tasks, and current_action may have empty source_ids when no
  research source is available.

GOAL:
State the person's actual goal clearly and concisely.

STARTING POINT:
Describe where the person is starting in practical terms.
Do not silently assume a skill level that was not established.

GOAL CONDITIONS:
Respect every meaningful condition extracted from the person.

TIME:
The full plan must fit entirely between the supplied start_date and end_date.

ENCOURAGEMENT:
Write directly to the person.
Acknowledge the foundation they already have and make the next steps feel
clear and achievable without making unrealistic promises.

FEASIBILITY:
Give a grounded assessment of what the person can realistically work toward
within the available timeframe.

Write the reasons and constraints as useful information for the person, not
as a report about them.

For example:
GOOD:
"You already know a few basic chords, so you can spend more of your time
building transitions and complete-song fluency."

BAD:
"The user already knows a few basic chords, which reduces the initial
learning load."

Do not produce a numerical feasibility score.

REQUIREMENTS:
List only the things the person genuinely needs to carry out the plan.

Write them in practical, user-facing language.
Examples:
- "15–30 minutes of focused practice time"
- "A guitar that is ready to play"
- "Song sheets or tablature for songs you want to learn"

Do not invent expensive or unnecessary requirements.

PLAN STRUCTURE:
Create a sequential phased plan.

Create exactly 4 sections.

Keep section purposes to one sentence.
Keep task titles short.
Keep encouragement concise.
Keep feasibility reasons and constraints concise.
Keep the current_action description to 1–3 sentences.

The sections represent the progression through the goal.
The person should move through them in order.

Each section must contain:
- a clear title
- a short purpose written for the person
- 2–3 concise tasks

Sections are milestones, not disconnected topic groups.
Later sections must build naturally on earlier ones.

TASK STYLE:
Tasks should be concise, actionable steps.

Write task titles as things the person can actually do.

Prefer:
"Review your basic chords at a slow tempo"
"Practice the hardest chord transitions"
"Play the song sections in sequence"

Avoid:
"Chord review"
"Transition analysis"
"Song integration"

Do not turn every task into a long tutorial.
The detailed explanation belongs in the current_action when that task becomes
the person's immediate focus.

CURRENT ACTION — VERY IMPORTANT:
The current action is NOT a separate task.

It must always be the person's immediate next step in the sequence.

It must correspond to the FIRST TASK of the FIRST SECTION.

Therefore:

current_action.title
MUST be exactly the same as:
sections[0].tasks[0].title

The current action description should expand that first task into a short,
practical explanation that gives the person enough detail to begin
immediately.

The description should:
- speak directly to "you"
- explain what to do
- provide just enough practical detail to remove uncertainty
- remain concise
- not introduce a new task that is not represented by the first task

The completion condition should clearly tell the person what must be true
before they move on to the next task.

For example, if the first task is:
"Review your basic chords at a slow tempo"

a suitable current action would explain which chords to review, how to keep
the session focused, and what successful completion looks like, without
turning into a full guitar lesson.

The current action must NEVER:
- jump to a later section
- combine several later tasks
- introduce a new unrelated activity
- tell the person to choose something that belongs to a later task

The intended progression is:

Section 1 → Task 1 → Task 2 → Task 3
→ Section 2 → Task 1 → Task 2 → ...

Evolution will later advance the current action as the person progresses.

SOURCE LINKING:
Each requirement, task, and current action must include only the IDs of
research sources that directly support it.

Use only source IDs that are actually supplied.

A plan may contain S1, S2, S3, or fewer if fewer papers were successfully
retrieved.

Do not invent a missing source.
Do not attach irrelevant sources merely to fill the field.

FINAL RESPONSE:
Return only the structured JSON required by the supplied schema.
"""


def _validate_plan_dates(
    extraction: PlanGenerationIn,
) -> None:
    today = datetime.now(
        ZoneInfo("Asia/Karachi")
    ).date()

    start_date = extraction.extraction.time_period.start_date
    end_date = extraction.extraction.time_period.end_date

    if not start_date or not end_date:
        raise ValueError(
            "A complete start and end date are required before generating a plan"
        )

    parsed_start = datetime.strptime(
        start_date,
        DATE_FORMAT,
    ).date()

    parsed_end = datetime.strptime(
        end_date,
        DATE_FORMAT,
    ).date()

    if parsed_start < today:
        raise ValueError(
            "The plan start date cannot be in the past"
        )

    if parsed_end < parsed_start:
        raise ValueError(
            "The plan end date cannot be before the start date"
        )


def _is_unknown(value: str) -> bool:
    return value.strip().lower() in {
        "",
        "unknown",
        "undetermined",
    }


def _validate_plan_input(
    extraction: PlanGenerationIn,
) -> None:
    _validate_plan_dates(extraction)

    planner = extraction.extraction

    if _is_unknown(
        planner.goal.goal
    ):
        raise ValueError(
            "A concrete goal is required before generating a plan"
        )

    if _is_unknown(
        planner.starting_point.starting_point
    ):
        raise ValueError(
            "A concrete starting point is required before generating a plan"
        )

    remaining_questions = [
        *planner.goal.clarification_questions,
        *planner.starting_point.clarification_questions,
        *planner.time_period.clarification_questions,
    ]

    if remaining_questions:
        raise ValueError(
            "All clarification questions must be resolved before generating a plan"
        )


def _build_query_prompt(
    extraction: PlanGenerationIn,
) -> str:
    planner = extraction.extraction

    return f"""
{RESEARCH_QUERY_PROMPT}

FINALIZED GOAL:
{planner.goal.goal}

GOAL CONDITIONS:
{json.dumps(planner.goal.conditions, indent=2)}

STARTING POINT:
{planner.starting_point.starting_point}

START DATE:
{planner.time_period.start_date}

END DATE:
{planner.time_period.end_date}

Return exactly three distinct research queries.
"""


def _generate_research_queries(
    extraction: PlanGenerationIn,
) -> list[ResearchQuery]:
    prompt = _build_query_prompt(
        extraction
    )

    response = client.chat.completions.create(
        model=PLAN_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Generate exactly three distinct research queries "
                    "and return only the structured JSON response."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        reasoning_effort="medium",
        reasoning_format="hidden",
        max_completion_tokens=700,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "research_query_set",
                "strict": True,
                "schema": (
                    ResearchQuerySet
                    .model_json_schema()
                ),
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "The research-query model returned an empty response"
        )

    result = ResearchQuerySet.model_validate(
        json.loads(content)
    )

    if len(result.queries) != 3:
        raise ValueError(
            "The research-query model did not return exactly three queries"
        )

    normalized = {
        query.query.strip().lower()
        for query in result.queries
    }

    if len(normalized) != 3:
        raise ValueError(
            "The research-query model returned duplicate queries"
        )

    return result.queries


def _semantic_scholar_search(
    query: ResearchQuery,
) -> ResearchSource | None:
    params = urlencode(
        {
            "query": query.query,
            "limit": 1,
            "fields": (
                "paperId,"
                "title,"
                "abstract,"
                "year,"
                "authors,"
                "url"
            ),
        }
    )

    url = (
        f"{SEMANTIC_SCHOLAR_URL}"
        f"?{params}"
    )

    max_attempts = 4
    last_error = None

    for attempt in range(max_attempts):
        request = Request(
            url,
            headers={
                "User-Agent": (
                    "Evolution/1.0 "
                    "(evidence-based skill planner)"
                ),
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(
                request,
                timeout=20,
            ) as response:
                data = json.loads(
                    response.read()
                )

            papers = data.get(
                "data",
                []
            )

            if not papers:
                return None

            paper = papers[0]

            authors = [
                author.get("name", "")
                for author in paper.get(
                    "authors",
                    []
                )
                if author.get("name")
            ]

            return ResearchSource(
                source_id="",
                angle=query.angle,
                query=query.query,
                paper_id=paper["paperId"],
                title=paper.get(
                    "title",
                    "",
                ),
                abstract=paper.get(
                    "abstract"
                ),
                year=paper.get(
                    "year"
                ),
                authors=authors,
                url=paper.get(
                    "url"
                ),
            )

        except HTTPError as error:
            last_error = error

            retryable = (
                error.code == 429
                or 500 <= error.code < 600
            )

            if not retryable:
                return None

            retry_after = (
                error.headers.get(
                    "Retry-After"
                )
                if error.headers
                else None
            )

            try:
                delay = float(
                    retry_after
                ) if retry_after else 1.5 * (2 ** attempt)
            except (TypeError, ValueError):
                delay = 1.5 * (2 ** attempt)

            if attempt < max_attempts - 1:
                time.sleep(
                    min(delay, 10.0)
                )

        except (
            URLError,
            TimeoutError,
            OSError,
        ) as error:
            last_error = error

            if attempt < max_attempts - 1:
                delay = 1.5 * (2 ** attempt)

                time.sleep(
                    min(delay, 10.0)
                )

    return None

def _build_generic_fallback_queries() -> list[ResearchQuery]:
    return [
        ResearchQuery(
            angle="general skill learning",
            purpose="Broad research on how people learn and improve skills",
            query="skill learning",
        ),
        ResearchQuery(
            angle="skill acquisition and practice",
            purpose="Broad research on skill acquisition and effective practice",
            query="skill acquisition practice",
        ),
    ]


def _fetch_research_sources(
    extraction: PlanGenerationIn,
    queries: list[ResearchQuery],
) -> list[ResearchSource]:
    sources = []

    # First attempt: the three goal-specific research queries.
    for query in queries:
        source = _semantic_scholar_search(
            query
        )

        if source is None:
            continue

        source.source_id = (
            f"S{len(sources) + 1}"
        )

        sources.append(
            source
        )

    # If at least one goal-specific source was found,
    # use the available research normally.
    if sources:
        return sources

    # Second attempt: two deliberately broader,
    # topic-independent Semantic Scholar searches.
    for query in _build_generic_fallback_queries():
        source = _semantic_scholar_search(
            query
        )

        if source is None:
            continue

        source.source_id = (
            f"S{len(sources) + 1}"
        )

        sources.append(
            source
        )

    # If Semantic Scholar still produced nothing,
    # return an empty list so the planning model can
    # fall back to its general knowledge.
    return sources

def _build_plan_prompt(
    extraction: PlanGenerationIn,
    sources: list[ResearchSource],
    queries: list[ResearchQuery],
) -> str:
    planner = extraction.extraction

    research_context = [
        {
            "source_id": source.source_id,
            "angle": source.angle,
            "title": source.title,
            "abstract": (
                source.abstract[:3000]
                if source.abstract
                else None
            ),
        }
        for source in sources
    ]

    return f"""
{PLAN_GENERATION_PROMPT}

FINALIZED USER CONTEXT:

GOAL:
{planner.goal.goal}

GOAL CONDITIONS:
{json.dumps(planner.goal.conditions, indent=2)}

STARTING POINT:
{planner.starting_point.starting_point}

START DATE:
{planner.time_period.start_date}

END DATE:
{planner.time_period.end_date}

RESEARCH EVIDENCE:
{json.dumps(research_context, indent=2)}

The research evidence contains paper abstracts retrieved from Semantic Scholar.

{
    "If research evidence is supplied, use it as the evidence base for the plan. "
    "Do not reproduce the abstracts in your response."
    if research_context
    else
    "No usable research paper was retrieved from Semantic Scholar. "
    "Use your general knowledge to create the plan, but do not describe any "
    "recommendation as being supported by research. Explicitly reflect the "
    "absence of retrieved research in feasibility.uncertainty."
}

Source metadata will be attached by the application after generation.

Remember:
- Compare the supplied research evidence rather than treating each source
  independently.
- Do not invent unsupported findings.
- Keep the plan user-facing and written directly to the person.
- Use "you" and "your", not "the user" or "the person".
- Keep section purposes and task titles concise.
- The sections must form a sequential progression.
- The current action must be based on the first task of the first section.
- current_action.title must exactly match sections[0].tasks[0].title.
- current_action.description must expand that task with enough practical
  detail for the person to begin immediately.
- current_action.completion_condition must describe when that first task is
  genuinely complete.
- Do not let current_action introduce a later task or skip ahead.
- Return exactly one current_action.
"""


def _generate_plan(
    extraction: PlanGenerationIn,
    sources: list[ResearchSource],
    queries: list[ResearchQuery],
) -> GeneratedPlan:
    prompt = _build_plan_prompt(
        extraction,
        sources,
        queries,
    )

    response = client.chat.completions.create(
        model=PLAN_MODEL,
        messages=[
            {
                "role": "system",
                "content": (
                    "Create an evidence-grounded structured improvement "
                    "plan and return only the requested JSON."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
        temperature=0,
        reasoning_effort="low",
        include_reasoning=False,
        max_completion_tokens=PLAN_MAX_COMPLETION_TOKENS,
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "generated_plan_content",
                "strict": True,
                "schema": (
                    GeneratedPlanContent
                    .model_json_schema()
                ),
            },
        },
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "The planning model returned an empty response"
        )

    result = GeneratedPlanContent.model_validate(
        json.loads(content)
    )

    if not result.sections:
        raise ValueError(
            "The planning model returned no plan sections"
        )

    if not result.sections[0].tasks:
        raise ValueError(
            "The first plan section contains no tasks"
        )

    first_task = result.sections[0].tasks[0]

    if normalize_text(
            result.current_action.title
    ) != normalize_text(
        first_task.title
    ):
        raise ValueError(
            "The current action must match the first task of the first section"
        )

    expected_source_ids = {
        source.source_id
        for source in sources
    }

    for requirement in result.requirements:
        if not set(
            requirement.source_ids
        ).issubset(
            expected_source_ids
        ):
            raise ValueError(
                "A plan requirement contains an invalid source ID"
            )

    for section in result.sections:
        for task in section.tasks:
            if not set(
                task.source_ids
            ).issubset(
                expected_source_ids
            ):
                raise ValueError(
                    "A plan task contains an invalid source ID"
                )

    if not set(
        result.current_action.source_ids
    ).issubset(
        expected_source_ids
    ):
        raise ValueError(
            "The current action contains an invalid source ID"
        )

    final_sources = [
        PlanSource(
            source_id=source.source_id,
            angle=source.angle,
            query=source.query,
            paper_id=source.paper_id,
            title=source.title,
            year=source.year,
            authors=source.authors,
            url=source.url,
        )
        for source in sources
    ]

    final_data = result.model_dump()

    final_data["sources"] = [
        source.model_dump()
        for source in final_sources
    ]

    return GeneratedPlan.model_validate(
        final_data
    )


def generate_plan(
    extraction: PlanGenerationIn,
) -> dict:
    _validate_plan_input(
        extraction
    )

    queries = _generate_research_queries(
        extraction
    )

    sources = _fetch_research_sources(
        extraction,
        queries,
    )

    plan = _generate_plan(
        extraction,
        sources,
        queries,
    )

    return plan.model_dump()

def _find_current_task(
    plan: GeneratedPlan,
) -> tuple[int, int]:
    current_title = normalize_text(
        plan.current_action.title
    )

    for section_index, section in enumerate(
        plan.sections
    ):
        for task_index, task in enumerate(
            section.tasks
        ):
            if (
                normalize_text(task.title)
                == current_title
            ):
                return section_index, task_index

    raise ValueError(
        "The current action does not match any task in the plan"
    )


def _get_next_task(
    plan: GeneratedPlan,
) -> tuple[int, int, object]:
    section_index, task_index = (
        _find_current_task(plan)
    )

    current_section = plan.sections[
        section_index
    ]

    if task_index + 1 < len(
        current_section.tasks
    ):
        next_section_index = section_index
        next_task_index = task_index + 1

    elif section_index + 1 < len(
        plan.sections
    ):
        next_section_index = section_index + 1

        if not plan.sections[
            next_section_index
        ].tasks:
            raise ValueError(
                "The next plan section contains no tasks"
            )

        next_task_index = 0

    else:
        raise ValueError(
            "You have already reached the final task in the plan"
        )

    next_task = plan.sections[
        next_section_index
    ].tasks[
        next_task_index
    ]

    return (
        next_section_index,
        next_task_index,
        next_task,
    )


def advance_current_action(
    plan: GeneratedPlan,
) -> GeneratedPlan:
    (
        _,
        _,
        next_task,
    ) = _get_next_task(plan)

    new_action = CurrentAction(
        title=next_task.title,
        description=(
            f"Work on this task as the next step in "
            f"your plan: {next_task.title}."
        ),
        completion_condition=(
            f"You have completed '{next_task.title}' "
            "and feel comfortable with it before moving on."
        ),
        source_ids=next_task.source_ids,
    )

    updated_data = plan.model_dump()

    updated_data["current_action"] = (
        new_action.model_dump()
    )

    return GeneratedPlan.model_validate(
        updated_data
    )