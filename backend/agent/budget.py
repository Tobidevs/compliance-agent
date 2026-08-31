"""Server-side tool-call budget for the evidence subagent.

The budget used to live only in the system prompt, where it was both self-contradictory
and unenforced. It is now a mutable ledger carried in `SubAgentInput["budget"]`: the
graph passes it by reference, so every tool call in a run debits the same object.
"""

from dataclasses import dataclass, field
from typing import Literal

# Per-control anti-stuck caps. Cluster totals are these scaled by the control count.
FETCHES_PER_CONTROL = 3
TREES_PER_CONTROL = 2

_KIND_LABELS = {"fetch": "get_file_content", "tree": "get_repository_tree"}


@dataclass
class BudgetLedger:
    """Tracks tool-call spend for one evidence subagent run (one cluster)."""

    control_ids: list[str]
    fetches_max: int
    trees_max: int
    fetches_used: int = 0
    trees_used: int = 0
    per_control_fetches: dict[str, int] = field(default_factory=dict)
    per_control_trees: dict[str, int] = field(default_factory=dict)
    refusals: int = 0
    # Index of the control currently being investigated; synced from concluded-control count.
    control_index: int = 0

    @classmethod
    def for_controls(cls, controls: list[dict]) -> "BudgetLedger":
        """Size the ledger from cluster width: 3 fetches / 2 trees per assigned control."""
        control_ids = [
            str(control.get("regulation_id") or f"control_{index}")
            for index, control in enumerate(controls or [])
        ]
        # An empty cluster still gets one control's worth so a stray call is bounded, not free.
        width = max(len(control_ids), 1)
        return cls(
            control_ids=control_ids,
            fetches_max=FETCHES_PER_CONTROL * width,
            trees_max=TREES_PER_CONTROL * width,
        )

    @property
    def current_control_id(self) -> str:
        if not self.control_ids:
            return "unknown"
        return self.control_ids[min(self.control_index, len(self.control_ids) - 1)]

    def sync_progress(self, messages) -> None:
        """Controls are processed in order, so the concluded count is the current index."""
        self.control_index = sum(
            1
            for message in messages or []
            if getattr(message, "type", None) == "tool"
            and getattr(message, "name", None) == "conclude_evidence"
        )

    def cluster_remaining(self, kind: Literal["fetch", "tree"]) -> int:
        if kind == "fetch":
            return max(self.fetches_max - self.fetches_used, 0)
        return max(self.trees_max - self.trees_used, 0)

    def control_remaining(self, kind: Literal["fetch", "tree"]) -> int:
        control_id = self.current_control_id
        if kind == "fetch":
            return max(FETCHES_PER_CONTROL - self.per_control_fetches.get(control_id, 0), 0)
        return max(TREES_PER_CONTROL - self.per_control_trees.get(control_id, 0), 0)

    def remaining(self, kind: Literal["fetch", "tree"]) -> int:
        return min(self.cluster_remaining(kind), self.control_remaining(kind))

    def spend(self, kind: Literal["fetch", "tree"]) -> str | None:
        """Debit one call. Returns None when allowed, or a refusal message when exhausted."""
        control_id = self.current_control_id
        if self.cluster_remaining(kind) <= 0:
            self.refusals += 1
            return self._refusal(kind, control_id, cluster_scope=True)
        if self.control_remaining(kind) <= 0:
            self.refusals += 1
            return self._refusal(kind, control_id, cluster_scope=False)

        if kind == "fetch":
            self.fetches_used += 1
            self.per_control_fetches[control_id] = (
                self.per_control_fetches.get(control_id, 0) + 1
            )
        else:
            self.trees_used += 1
            self.per_control_trees[control_id] = (
                self.per_control_trees.get(control_id, 0) + 1
            )
        return None

    def recursion_limit(self) -> int:
        """Worst case at 2 graph steps per turn: one tool call per turn for the whole budget, plus a conclude turn and a refused turn per control, plus slack."""
        turns = self.fetches_max + self.trees_max + 2 * len(self.control_ids) + 4
        return 2 * turns

    def _refusal(self, kind: Literal["fetch", "tree"], control_id: str, cluster_scope: bool) -> str:
        tool_name = _KIND_LABELS[kind]
        used, cap = (
            (self.fetches_used, self.fetches_max)
            if kind == "fetch"
            else (self.trees_used, self.trees_max)
        )
        if cluster_scope:
            return (
                f"BUDGET REFUSED — this {tool_name} call did NOT run and returned no data.\n"
                f"The {tool_name} budget for this entire cluster is exhausted ({used}/{cap} used).\n"
                f"Stop searching. Call conclude_evidence now for control {control_id} using only the "
                f"evidence you have already gathered (set no_evidence_found=true if you found none), "
                f"then conclude every remaining control the same way and call "
                f"finished_gathering_evidence. Retrying this tool will be refused again."
            )
        per_control_cap = FETCHES_PER_CONTROL if kind == "fetch" else TREES_PER_CONTROL
        return (
            f"BUDGET REFUSED — this {tool_name} call did NOT run and returned no data.\n"
            f"Control {control_id} has used its full allowance of {per_control_cap} {tool_name} "
            f"calls.\n"
            f"Call conclude_evidence now for control {control_id} using only the evidence you have "
            f"already gathered (set no_evidence_found=true if you found none), then move to the next "
            f"control. Retrying this tool for this control will be refused again."
        )
