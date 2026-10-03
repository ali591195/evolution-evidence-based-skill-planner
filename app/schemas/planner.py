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