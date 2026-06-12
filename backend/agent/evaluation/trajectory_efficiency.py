from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import BaseModel, Field
from .eval_prompts import TRAJECTORY_EFFICIENCY_PROMPT


class TrajectoryEfficiencyEvaluatorOutput(BaseModel):
    search_strategy: float = Field(ge=0.0, le=1.0)
    tool_call_efficiency: float = Field(
        ge=0.0, le=1.0, description="Were tool calls efficient and purposeful?"
    )
    think_usage: float = Field(
        ge=0.0, le=1.0, description="Was think() used effectively at decision points?"
    )
    evidence_accuracy: float = Field(
        ge=0.0,
        le=1.0,
        description="Did the evidence result accurately reflect the evidence gathered?",
    )
    penalties: list[dict] = Field(
        description="List of any applied penalties with type, deduction amount, and reasoning."
    )
    weighted_score_before_penalties: float = Field(
        ge=0.0, le=1.0, description="The weighted score before applying penalties."
    )
    final_score: float = Field(
        ge=0.0, le=1.0, description="The final score after applying penalties."
    )
    critical_failures: list[str] = Field(
        description="List of any critical failures (score 0.0 dimensions or applied penalties)."
    )
    reasoning: str = Field(
        description="Overall reasoning for the grade, highlighting key observations and areas of strength or weakness."
    )


model = init_chat_model(model="openai:gpt-5.4-mini")
model = model.with_structured_output(TrajectoryEfficiencyEvaluatorOutput)


def evaluate_trajectory_efficiency(outputs):
    print("Evaluating trajectory efficiency...")
    print("Outputs:", outputs)

    response = model.invoke(
        [
            HumanMessage(
                content=TRAJECTORY_EFFICIENCY_PROMPT.format(
                    messages=outputs["messages"],
                    control_id=outputs["controls"][0]["regulation_id"],
                    control_description=outputs["controls"][0]["description"],
                )
            )
        ]
    )
    return {
        "results": [
            {"key": "search_strategy", "value": response.search_strategy},
            {"key": "tool_call_efficiency", "value": response.tool_call_efficiency},
            {"key": "think_usage", "value": response.think_usage},
            {"key": "evidence_accuracy", "value": response.evidence_accuracy},
            {"key": "penalties", "value": response.penalties},
            {
                "key": "weighted_score_before_penalties",
                "value": response.weighted_score_before_penalties,
            },
            {"key": "final_score", "value": response.final_score},
            {"key": "critical_failures", "value": response.critical_failures},
            {"key": "reasoning", "value": response.reasoning},
        ]
    }
