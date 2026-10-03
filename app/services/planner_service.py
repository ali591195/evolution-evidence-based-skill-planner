import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo

from groq import Groq

from app.schemas.planner import (
    ClarificationAnswer,
    PlannerExtraction, DATE_FORMAT, ClarificationProcessResult,
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