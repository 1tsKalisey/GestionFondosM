"""Shared event type mapping for SyncOutbox and remote merge."""

from __future__ import annotations


EVENT_TYPE_BY_ENTITY_OPERATION = {
    ("transaction", "create"): "txn_created",
    ("transaction", "update"): "txn_updated",
    ("transaction", "delete"): "txn_deleted",
    ("budget", "create"): "budget_created",
    ("budget", "update"): "budget_updated",
    ("budget", "delete"): "budget_deleted",
    ("category", "create"): "category_created",
    ("category", "update"): "category_updated",
    ("category", "delete"): "category_deleted",
    ("recurring", "create"): "recurring_created",
    ("recurring", "update"): "recurring_updated",
    ("recurring", "delete"): "recurring_deleted",
    ("alert", "create"): "alert_created",
    ("alert", "update"): "alert_updated",
    ("alert", "delete"): "alert_deleted",
    ("savings_goal", "create"): "goal_created",
    ("savings_goal", "update"): "goal_updated",
    ("savings_goal", "delete"): "goal_deleted",
    ("categorization_rule", "create"): "categorization_rule_created",
    ("categorization_rule", "update"): "categorization_rule_updated",
    ("categorization_rule", "delete"): "categorization_rule_deleted",
    ("account", "create"): "account_created",
    ("account", "update"): "account_updated",
    ("account", "delete"): "account_deleted",
}


def resolve_event_type(entity_type: str | None, operation: str | None) -> str:
    return EVENT_TYPE_BY_ENTITY_OPERATION.get((entity_type, operation), "txn_updated")
