from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


DATE_FORMAT = "%Y-%m-%d"


class PlannerIn(BaseModel):
    goal: str = Field(min_length=1)
    current_level: str = Field(min_length=1)
    timeframe: str = Field(min_length=1)


class GoalExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    conditions: list[str]
    clarification_questions: list[str]


class StartingPointExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    starting_point: str
    clarification_questions: list[str]


class TimePeriodExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    start_date: str | None
    end_date: str | None
    clarification_questions: list[str]

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str | None) -> str | None:
        if value is None:
            return None

        try:
            datetime.strptime(value, DATE_FORMAT)
        except ValueError:
            raise ValueError(
                "Dates must use YYYY-MM-DD format"
            )

        return value


class PlannerExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: GoalExtraction
    starting_point: StartingPointExtraction
    time_period: TimePeriodExtraction


class ClarificationAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    category: Literal[
        "goal",
        "starting_point",
        "time_period",
    ]

    question: str = Field(min_length=1)
    answer: str = Field(min_length=1)


class PlannerClarificationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: PlannerExtraction
    answers: list[ClarificationAnswer]

class ClarificationProcessResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answered: bool
    defer_question: bool
    follow_up_question: str | None
    extraction: PlannerExtraction

class PlanGenerationIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    extraction: PlannerExtraction


class ResearchQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")

    angle: str
    purpose: str
    query: str


class ResearchQuerySet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    queries: list[ResearchQuery]


class PlanSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    angle: str
    query: str
    paper_id: str
    title: str
    year: int | None
    authors: list[str]
    url: str | None


class PlanFeasibility(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assessment: str
    reasons: list[str]
    constraints: list[str]
    uncertainty: str


class PlanRequirement(BaseModel):
    model_config = ConfigDict(extra="forbid")

    item: str
    why_needed: str
    source_ids: list[str]


class PlanTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    source_ids: list[str]


class PlanSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    purpose: str
    tasks: list[PlanTask]


class CurrentAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str
    description: str
    completion_condition: str
    source_ids: list[str]

class GeneratedPlanContent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    goal_conditions: list[str]
    starting_point: str
    start_date: str
    end_date: str

    encouragement: str

    feasibility: PlanFeasibility

    requirements: list[PlanRequirement]

    sections: list[PlanSection]

    current_action: CurrentAction

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(
                value,
                DATE_FORMAT,
            )
        except ValueError:
            raise ValueError(
                "Dates must use YYYY-MM-DD format"
            )

        return value

class GeneratedPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    goal: str
    goal_conditions: list[str]
    starting_point: str
    start_date: str
    end_date: str

    encouragement: str

    feasibility: PlanFeasibility

    requirements: list[PlanRequirement]

    sections: list[PlanSection]

    current_action: CurrentAction

    sources: list[PlanSource]

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, value: str) -> str:
        try:
            datetime.strptime(
                value,
                DATE_FORMAT,
            )
        except ValueError:
            raise ValueError(
                "Dates must use YYYY-MM-DD format"
            )

        return value