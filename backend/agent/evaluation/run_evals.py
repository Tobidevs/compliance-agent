from langsmith import Client

from ..state import SubAgentInput
from ..subagents import evidence_subagent
from .trajectory_efficiency import evaluate_trajectory_efficiency

ls_client = Client()
dataset = ls_client.read_dataset(dataset_name="compliance-dataset")

def target_func(state: SubAgentInput):
    final_state = evidence_subagent.invoke(state)
    return final_state
    
ls_client.evaluate(
    target_func,
    data=dataset,
    evaluators=[evaluate_trajectory_efficiency],
    experiment_prefix="evidence-eval"
)
    