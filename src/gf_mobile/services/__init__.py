"""Lazy exports for service classes.

Avoid importing the full service graph at package import time because sync and
service modules can reference each other during bootstrap and tests.
"""

from __future__ import annotations

from importlib import import_module


_SERVICE_MODULES = {
    "TransactionService": "gf_mobile.services.transaction_service",
    "RecurringService": "gf_mobile.services.recurring_service",
    "BudgetService": "gf_mobile.services.budget_service",
    "AlertService": "gf_mobile.services.alert_service",
    "SavingsGoalService": "gf_mobile.services.savings_goal_service",
    "CategorizationService": "gf_mobile.services.categorization_service",
    "CategoryService": "gf_mobile.services.category_service",
}

__all__ = list(_SERVICE_MODULES.keys())


def __getattr__(name: str):
    module_name = _SERVICE_MODULES.get(name)
    if not module_name:
        raise AttributeError(name)
    module = import_module(module_name)
    return getattr(module, name)
