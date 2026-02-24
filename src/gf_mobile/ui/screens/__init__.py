"""__init__ para ui.screens"""

from gf_mobile.ui.screens.login_screen import LoginScreen
from gf_mobile.ui.screens.transactions_screen import TransactionsScreen
from gf_mobile.ui.screens.transactions_results_screen import TransactionsResultsScreen
from gf_mobile.ui.screens.add_transaction_screen import AddTransactionScreen
from gf_mobile.ui.screens.sync_status_screen import SyncStatusScreen
from gf_mobile.ui.screens.profile_screen import ProfileScreen
from gf_mobile.ui.screens.quick_entry_screen import QuickEntryScreen

__all__ = [
    "LoginScreen",
    "TransactionsScreen",
    "TransactionsResultsScreen",
    "AddTransactionScreen",
    "SyncStatusScreen",
    "ProfileScreen",
    "QuickEntryScreen",
]
