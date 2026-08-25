import pytest

from nexweave_domain import (
    WORKFLOW_STEP_PLAN,
    WorkflowCommand,
    WorkflowRuleViolation,
    WorkflowTaskStatus,
    WorkflowType,
    available_workflow_commands,
    stable_workflow_id,
    validate_workflow_command,
)


def test_all_seven_workflow_types_have_distinct_bounded_step_plans() -> None:
    assert len(WorkflowType) == 7
    assert set(WORKFLOW_STEP_PLAN) == set(WorkflowType)
    assert all(len(plan) == 3 for plan in WORKFLOW_STEP_PLAN.values())
    assert len({step for plan in WORKFLOW_STEP_PLAN.values() for step in plan}) == 21


def test_stable_workflow_id_uses_type_tenant_and_business_key() -> None:
    value = stable_workflow_id(WorkflowType.KNOWLEDGE_COMPILE, "tenant-1", "case:42")

    assert value == "compile/tenant-1/case:42"
    assert value == stable_workflow_id(WorkflowType.KNOWLEDGE_COMPILE, "tenant-1", "case:42")


def test_human_review_wait_state_exposes_human_commands_but_terminal_does_not() -> None:
    waiting = available_workflow_commands(WorkflowType.HUMAN_REVIEW, WorkflowTaskStatus.WAITING)

    assert WorkflowCommand.CLAIM in waiting
    assert WorkflowCommand.APPROVE in waiting
    assert WorkflowCommand.REJECT in waiting
    assert (
        available_workflow_commands(WorkflowType.HUMAN_REVIEW, WorkflowTaskStatus.SUCCEEDED) == ()
    )


def test_invalid_command_is_rejected_by_domain_policy() -> None:
    with pytest.raises(WorkflowRuleViolation, match="APPROVE is not allowed"):
        validate_workflow_command(
            WorkflowType.SOURCE_INGESTION,
            WorkflowTaskStatus.RUNNING,
            WorkflowCommand.APPROVE,
        )
