from __future__ import annotations

from .errors import (
    AuthorizationError,
    FinanceSystemError,
    NotFoundError,
    UndoError,
    ValidationError,
)
from .models import Account, AuditLog, Bank, Client, Deposit, Enterprise, SalaryApplication, Transaction, User
from .services import (
    AdminService,
    AuditService,
    AuthService,
    ClientService,
    DemoDataSeeder,
    FactoryService,
    LookupService,
    ManagerService,
    QueryService,
    SystemContext,
    TransactionService,
    ValidationService,
)


class FinancialSystem:
    def __init__(self) -> None:
        self._context = SystemContext()
        self._lookup = LookupService(self._context)
        self._validation = ValidationService(self._context)
        self._audit = AuditService(self._context)
        self._transactions = TransactionService(self._context, self._lookup, self._audit)
        self._factory = FactoryService(self._context, self._lookup)
        self._queries = QueryService(self._context, self._lookup, self._validation, self._audit)
        self._auth = AuthService(self._context, self._validation, self._audit)
        self._client = ClientService(
            self._context,
            self._queries,
            self._lookup,
            self._validation,
            self._audit,
            self._transactions,
        )
        self._manager = ManagerService(self._lookup, self._validation, self._audit)
        self._admin = AdminService(self._lookup, self._audit)
        DemoDataSeeder(self._context, self._factory, self._transactions, self._audit).seed()

    def authenticate(self, username: str, password: str) -> User:
        return self._auth.authenticate(username, password)

    def get_user(self, user_id: int) -> User:
        return self._queries.get_user(user_id)

    def list_banks(self) -> list[Bank]:
        return self._queries.list_banks()

    def list_enterprises(self) -> list[Enterprise]:
        return self._queries.list_enterprises()

    def list_client_accounts(self, client_id: int) -> list[Account]:
        return self._queries.list_client_accounts(client_id)

    def list_client_deposits(self, client_id: int) -> list[Deposit]:
        return self._queries.list_client_deposits(client_id)

    def list_client_salary_applications(self, client_id: int) -> list[SalaryApplication]:
        return self._queries.list_client_salary_applications(client_id)

    def list_pending_clients(self) -> list[Client]:
        return self._queries.list_pending_clients()

    def list_clients(self) -> list[Client]:
        return self._queries.list_clients()

    def list_pending_salary_applications(self) -> list[SalaryApplication]:
        return self._queries.list_pending_salary_applications()

    def list_audit_logs(self) -> list[AuditLog]:
        return self._queries.list_audit_logs()

    def get_account_history(self, account_id: int) -> list[Transaction]:
        return self._queries.get_account_history(account_id)

    def get_deposit_history(self, deposit_id: int) -> list[Transaction]:
        return self._queries.get_deposit_history(deposit_id)

    def get_client_account_history(self, client_id: int, account_id: int) -> list[Transaction]:
        return self._queries.get_client_account_history(client_id, account_id)

    def get_client_deposit_history(self, client_id: int, deposit_id: int) -> list[Transaction]:
        return self._queries.get_client_deposit_history(client_id, deposit_id)

    def register_client(self, username: str, password: str, full_name: str) -> Client:
        return self._auth.register_client(username, password, full_name)

    def confirm_client(self, manager_id: int, client_id: int) -> None:
        self._manager.confirm_client(manager_id, client_id)

    def open_account(self, client_id: int, bank_id: int, name: str, initial_balance: float) -> Account:
        return self._client.open_account(client_id, bank_id, name, initial_balance)

    def close_account(self, client_id: int, account_id: int) -> None:
        self._client.close_account(client_id, account_id)

    def create_deposit(
        self,
        client_id: int,
        bank_id: int,
        name: str,
        source_account_id: int,
        amount: float,
        interest_rate: float,
    ) -> Deposit:
        return self._client.create_deposit(client_id, bank_id, name, source_account_id, amount, interest_rate)

    def close_deposit(self, client_id: int, deposit_id: int, target_account_id: int) -> None:
        self._client.close_deposit(client_id, deposit_id, target_account_id)

    def transfer_between_products(
        self,
        client_id: int,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        amount: float,
    ) -> None:
        self._client.transfer_between_products(client_id, source_type, source_id, target_type, target_id, amount)

    def accumulate_deposit(self, client_id: int, deposit_id: int) -> float:
        return self._client.accumulate_deposit(client_id, deposit_id)

    def submit_salary_application(self, client_id: int, enterprise_id: int) -> SalaryApplication:
        return self._client.submit_salary_application(client_id, enterprise_id)

    def receive_salary(self, client_id: int, enterprise_id: int, target_account_id: int) -> float:
        return self._client.receive_salary(client_id, enterprise_id, target_account_id)

    def add_client_to_enterprise(self, manager_id: int, client_id: int, enterprise_id: int) -> None:
        self._manager.add_client_to_enterprise(manager_id, client_id, enterprise_id)

    def remove_client_from_enterprise(self, manager_id: int, client_id: int, enterprise_id: int) -> None:
        self._manager.remove_client_from_enterprise(manager_id, client_id, enterprise_id)

    def approve_salary_application(self, manager_id: int, application_id: int) -> None:
        self._manager.approve_salary_application(manager_id, application_id)

    def set_account_blocked(self, manager_id: int, account_id: int, blocked: bool) -> None:
        self._manager.set_account_blocked(manager_id, account_id, blocked)

    def set_deposit_blocked(self, manager_id: int, deposit_id: int, blocked: bool) -> None:
        self._manager.set_deposit_blocked(manager_id, deposit_id, blocked)

    def undo_last_reversible_action(self, admin_id: int) -> AuditLog:
        return self._admin.undo_last_reversible_action(admin_id)
