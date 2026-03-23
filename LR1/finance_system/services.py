from __future__ import annotations

import copy
from datetime import datetime

from .errors import AuthorizationError, NotFoundError, UndoError, ValidationError
from .models import (
    Account,
    Admin,
    ApplicationStatus,
    AuditLog,
    Bank,
    Client,
    Deposit,
    Enterprise,
    Manager,
    RegistrationStatus,
    Role,
    SalaryApplication,
    SystemState,
    Transaction,
    User,
)


class SystemContext:
    def __init__(self) -> None:
        self.state = SystemState()


class LookupService:
    def __init__(self, context: SystemContext) -> None:
        self.context = context

    def get_user(self, user_id: int) -> User:
        user = self.context.state.users.get(user_id)
        if user is None:
            raise NotFoundError("Пользователь не найден.")
        return user

    def get_client(self, client_id: int) -> Client:
        user = self.get_user(client_id)
        if not isinstance(user, Client):
            raise AuthorizationError("Операция доступна только клиенту.")
        return user

    def get_active_client(self, client_id: int) -> Client:
        client = self.get_client(client_id)
        if client.registration_status != RegistrationStatus.APPROVED:
            raise AuthorizationError("Клиент еще не подтвержден менеджером.")
        return client

    def get_manager(self, manager_id: int) -> Manager:
        user = self.get_user(manager_id)
        if not isinstance(user, Manager):
            raise AuthorizationError("Операция доступна только менеджеру.")
        return user

    def get_admin(self, admin_id: int) -> Admin:
        user = self.get_user(admin_id)
        if not isinstance(user, Admin):
            raise AuthorizationError("Операция доступна только администратору.")
        return user

    def get_bank(self, bank_id: int) -> Bank:
        bank = self.context.state.banks.get(bank_id)
        if bank is None:
            raise NotFoundError("Банк не найден.")
        return bank

    def get_account(self, account_id: int) -> Account:
        account = self.context.state.accounts.get(account_id)
        if account is None:
            raise NotFoundError("Счет не найден.")
        return account

    def get_deposit(self, deposit_id: int) -> Deposit:
        deposit = self.context.state.deposits.get(deposit_id)
        if deposit is None:
            raise NotFoundError("Вклад не найден.")
        return deposit

    def get_enterprise(self, enterprise_id: int) -> Enterprise:
        enterprise = self.context.state.enterprises.get(enterprise_id)
        if enterprise is None:
            raise NotFoundError("Предприятие не найдено.")
        return enterprise

    def get_application(self, application_id: int) -> SalaryApplication:
        application = self.context.state.salary_applications.get(application_id)
        if application is None:
            raise NotFoundError("Заявка не найдена.")
        return application

    def get_product(self, product_type: str, product_id: int) -> Account | Deposit:
        if product_type == "account":
            return self.get_account(product_id)
        if product_type == "deposit":
            return self.get_deposit(product_id)
        raise ValidationError("Тип продукта должен быть account или deposit.")

    def find_approved_application(self, client_id: int, enterprise_id: int) -> SalaryApplication:
        client = self.get_client(client_id)
        for application_id in client.salary_application_ids:
            application = self.get_application(application_id)
            if application.enterprise_id == enterprise_id and application.status == ApplicationStatus.APPROVED:
                return application
        raise ValidationError("Нет одобренной заявки на зарплатный проект для выбранного предприятия.")


class ValidationService:
    def __init__(self, context: SystemContext) -> None:
        self.context = context

    def validate_text(self, value: str, field_name: str, min_length: int = 1) -> str:
        prepared = value.strip()
        if len(prepared) < min_length:
            if min_length > 1:
                raise ValidationError(f"{field_name} должно содержать минимум {min_length} символа(ов).")
            raise ValidationError(f"{field_name} не должно быть пустым.")
        return prepared

    def validate_amount(self, value: float, allow_zero: bool = False) -> float:
        if allow_zero and value == 0:
            return 0.0
        if value <= 0:
            raise ValidationError("Сумма должна быть больше нуля.")
        return round(value, 2)

    def validate_rate(self, value: float) -> float:
        if value <= 0 or value > 1:
            raise ValidationError("Ставка вклада должна быть в диапазоне (0; 1].")
        return round(value, 4)

    def ensure_unique_username(self, username: str) -> None:
        for user in self.context.state.users.values():
            if user.username.lower() == username.lower():
                raise ValidationError("Пользователь с таким логином уже существует.")

    def ensure_owner(self, expected_owner_id: int, actual_owner_id: int, label: str) -> None:
        if expected_owner_id != actual_owner_id:
            raise AuthorizationError(f"У клиента нет прав на выбранный {label}.")

    def ensure_product_open(self, product: Account | Deposit, label: str) -> None:
        if product.is_closed:
            raise ValidationError(f"{label} уже закрыт.")

    def ensure_not_blocked(self, product: Account | Deposit, label: str) -> None:
        if product.is_blocked:
            raise ValidationError(f"{label} заблокирован для исходящих операций.")


class AuditService:
    def __init__(self, context: SystemContext) -> None:
        self.context = context
        self.audit_logs: list[AuditLog] = []
        self.snapshots: dict[int, SystemState] = {}
        self.next_log_id = 1

    def now(self) -> str:
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def clone_state(self) -> SystemState:
        return copy.deepcopy(self.context.state)

    def append_log(
        self,
        actor_id: int,
        actor_role: str,
        action: str,
        details: str,
        reversible: bool,
    ) -> AuditLog:
        log = AuditLog(
            id=self.next_log_id,
            actor_id=actor_id,
            actor_role=actor_role,
            action=action,
            details=details,
            created_at=self.now(),
            reversible=reversible,
        )
        self.audit_logs.append(log)
        self.next_log_id += 1
        return log

    def remember_snapshot(self, log_id: int, snapshot: SystemState) -> None:
        self.snapshots[log_id] = snapshot

    def list_logs(self) -> list[AuditLog]:
        return list(self.audit_logs)

    def find_last_reversible_log(self) -> AuditLog:
        target_log = next(
            (
                log
                for log in reversed(self.audit_logs)
                if log.reversible and not log.undone and log.actor_role in {Role.CLIENT.value, Role.MANAGER.value}
            ),
            None,
        )
        if target_log is None:
            raise UndoError("Нет доступных действий для отката.")
        return target_log

    def restore_snapshot(self, log_id: int) -> None:
        snapshot = self.snapshots.get(log_id)
        if snapshot is None:
            raise UndoError("Для выбранного действия не найден снимок состояния.")
        self.context.state = copy.deepcopy(snapshot)


class TransactionService:
    def __init__(self, context: SystemContext, lookup: LookupService, audit: AuditService) -> None:
        self.context = context
        self.lookup = lookup
        self.audit = audit

    def create_transaction(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        amount: float,
        description: str,
    ) -> Transaction:
        transaction = Transaction(
            id=self.context.state.next_transaction_id,
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            amount=round(amount, 2),
            description=description,
            created_at=self.audit.now(),
        )
        self.context.state.transactions[transaction.id] = transaction
        self.context.state.next_transaction_id += 1

        for product_type, product_id in ((source_type, source_id), (target_type, target_id)):
            if product_type == "account" and product_id in self.context.state.accounts:
                self.context.state.accounts[product_id].transaction_ids.append(transaction.id)
            if product_type == "deposit" and product_id in self.context.state.deposits:
                self.context.state.deposits[product_id].transaction_ids.append(transaction.id)
        return transaction

    def apply_transfer(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        amount: float,
        description: str,
    ) -> None:
        source_product = self.lookup.get_product(source_type, source_id)
        target_product = self.lookup.get_product(target_type, target_id)
        source_product.balance = round(source_product.balance - amount, 2)
        target_product.balance = round(target_product.balance + amount, 2)
        self.create_transaction(source_type, source_id, target_type, target_id, amount, description)

    def apply_external_credit(
        self,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        amount: float,
        description: str,
    ) -> None:
        target_product = self.lookup.get_product(target_type, target_id)
        target_product.balance = round(target_product.balance + amount, 2)
        self.create_transaction(source_type, source_id, target_type, target_id, amount, description)


class FactoryService:
    def __init__(self, context: SystemContext, lookup: LookupService) -> None:
        self.context = context
        self.lookup = lookup

    def create_user(
        self,
        role: Role,
        username: str,
        password: str,
        full_name: str,
        approved: bool = True,
    ) -> User:
        user_id = self.context.state.next_user_id
        self.context.state.next_user_id += 1
        if role == Role.CLIENT:
            user = Client(
                id=user_id,
                username=username,
                password=password,
                full_name=full_name,
                role=role,
                registration_status=RegistrationStatus.APPROVED if approved else RegistrationStatus.PENDING,
            )
        elif role == Role.MANAGER:
            user = Manager(id=user_id, username=username, password=password, full_name=full_name, role=role)
        else:
            user = Admin(id=user_id, username=username, password=password, full_name=full_name, role=role)
        self.context.state.users[user.id] = user
        return user

    def create_bank(self, name: str) -> Bank:
        bank = Bank(id=self.context.state.next_bank_id, name=name)
        self.context.state.banks[bank.id] = bank
        self.context.state.next_bank_id += 1
        return bank

    def create_account(self, owner_id: int, bank_id: int, name: str, balance: float) -> Account:
        account = Account(
            id=self.context.state.next_account_id,
            owner_id=owner_id,
            bank_id=bank_id,
            name=name,
            balance=round(balance, 2),
        )
        self.context.state.accounts[account.id] = account
        self.context.state.next_account_id += 1
        client = self.lookup.get_client(owner_id)
        client.account_ids.append(account.id)
        return account

    def create_deposit(
        self,
        owner_id: int,
        bank_id: int,
        name: str,
        balance: float,
        interest_rate: float,
    ) -> Deposit:
        deposit = Deposit(
            id=self.context.state.next_deposit_id,
            owner_id=owner_id,
            bank_id=bank_id,
            name=name,
            balance=round(balance, 2),
            interest_rate=interest_rate,
        )
        self.context.state.deposits[deposit.id] = deposit
        self.context.state.next_deposit_id += 1
        client = self.lookup.get_client(owner_id)
        client.deposit_ids.append(deposit.id)
        return deposit

    def create_enterprise(self, name: str, salary_amount: float) -> Enterprise:
        enterprise = Enterprise(id=self.context.state.next_enterprise_id, name=name, salary_amount=salary_amount)
        self.context.state.enterprises[enterprise.id] = enterprise
        self.context.state.next_enterprise_id += 1
        return enterprise

    def attach_client_to_enterprise(self, client_id: int, enterprise_id: int) -> None:
        client = self.lookup.get_client(client_id)
        enterprise = self.lookup.get_enterprise(enterprise_id)
        client.enterprise_ids.append(enterprise.id)
        enterprise.employee_ids.append(client.id)


class QueryService:
    def __init__(self, context: SystemContext, lookup: LookupService, validation: ValidationService, audit: AuditService) -> None:
        self.context = context
        self.lookup = lookup
        self.validation = validation
        self.audit = audit

    def get_user(self, user_id: int) -> User:
        return self.lookup.get_user(user_id)

    def list_banks(self) -> list[Bank]:
        return sorted(self.context.state.banks.values(), key=lambda bank: bank.id)

    def list_enterprises(self) -> list[Enterprise]:
        return sorted(self.context.state.enterprises.values(), key=lambda enterprise: enterprise.id)

    def list_client_accounts(self, client_id: int) -> list[Account]:
        client = self.lookup.get_client(client_id)
        return [self.context.state.accounts[account_id] for account_id in client.account_ids]

    def list_client_deposits(self, client_id: int) -> list[Deposit]:
        client = self.lookup.get_client(client_id)
        return [self.context.state.deposits[deposit_id] for deposit_id in client.deposit_ids]

    def list_client_salary_applications(self, client_id: int) -> list[SalaryApplication]:
        client = self.lookup.get_client(client_id)
        return [self.context.state.salary_applications[application_id] for application_id in client.salary_application_ids]

    def list_pending_clients(self) -> list[Client]:
        pending_clients = [
            user
            for user in self.context.state.users.values()
            if isinstance(user, Client) and user.registration_status == RegistrationStatus.PENDING
        ]
        return sorted(pending_clients, key=lambda client: client.id)

    def list_clients(self) -> list[Client]:
        clients = [user for user in self.context.state.users.values() if isinstance(user, Client)]
        return sorted(clients, key=lambda client: client.id)

    def list_pending_salary_applications(self) -> list[SalaryApplication]:
        applications = [
            application
            for application in self.context.state.salary_applications.values()
            if application.status == ApplicationStatus.PENDING
        ]
        return sorted(applications, key=lambda application: application.id)

    def list_audit_logs(self) -> list[AuditLog]:
        return self.audit.list_logs()

    def get_account_history(self, account_id: int) -> list[Transaction]:
        account = self.lookup.get_account(account_id)
        return [self.context.state.transactions[transaction_id] for transaction_id in account.transaction_ids]

    def get_deposit_history(self, deposit_id: int) -> list[Transaction]:
        deposit = self.lookup.get_deposit(deposit_id)
        return [self.context.state.transactions[transaction_id] for transaction_id in deposit.transaction_ids]

    def get_client_account_history(self, client_id: int, account_id: int) -> list[Transaction]:
        account = self.lookup.get_account(account_id)
        self.validation.ensure_owner(client_id, account.owner_id, "счет")
        return self.get_account_history(account_id)

    def get_client_deposit_history(self, client_id: int, deposit_id: int) -> list[Transaction]:
        deposit = self.lookup.get_deposit(deposit_id)
        self.validation.ensure_owner(client_id, deposit.owner_id, "вклад")
        return self.get_deposit_history(deposit_id)


class AuthService:
    def __init__(
        self,
        context: SystemContext,
        validation: ValidationService,
        audit: AuditService,
    ) -> None:
        self.context = context
        self.validation = validation
        self.audit = audit

    def authenticate(self, username: str, password: str) -> User:
        username = username.strip()
        password = password.strip()
        if not username or not password:
            raise ValidationError("Логин и пароль обязательны.")
        for user in self.context.state.users.values():
            if user.username == username and user.password == password:
                return user
        raise AuthorizationError("Неверный логин или пароль.")

    def register_client(self, username: str, password: str, full_name: str) -> Client:
        username = self.validation.validate_text(username, "Логин")
        password = self.validation.validate_text(password, "Пароль", min_length=4)
        full_name = self.validation.validate_text(full_name, "ФИО")
        self.validation.ensure_unique_username(username)

        snapshot = self.audit.clone_state()
        client = Client(
            id=self.context.state.next_user_id,
            username=username,
            password=password,
            full_name=full_name,
            role=Role.CLIENT,
        )
        self.context.state.users[client.id] = client
        self.context.state.next_user_id += 1

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=Role.CLIENT.value,
            action="register_client",
            details=f"Клиент {client.full_name} зарегистрировался и ожидает подтверждения.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return client


class ClientService:
    def __init__(
        self,
        context: SystemContext,
        queries: QueryService,
        lookup: LookupService,
        validation: ValidationService,
        audit: AuditService,
        transactions: TransactionService,
    ) -> None:
        self.context = context
        self.queries = queries
        self.lookup = lookup
        self.validation = validation
        self.audit = audit
        self.transactions = transactions

    def open_account(self, client_id: int, bank_id: int, name: str, initial_balance: float) -> Account:
        client = self.lookup.get_active_client(client_id)
        bank = self.lookup.get_bank(bank_id)
        name = self.validation.validate_text(name, "Название счета")
        initial_balance = self.validation.validate_amount(initial_balance, allow_zero=True)

        snapshot = self.audit.clone_state()
        account = Account(
            id=self.context.state.next_account_id,
            owner_id=client.id,
            bank_id=bank.id,
            name=name,
            balance=round(initial_balance, 2),
        )
        self.context.state.accounts[account.id] = account
        self.context.state.next_account_id += 1
        client.account_ids.append(account.id)
        if initial_balance > 0:
            self.transactions.create_transaction(
                source_type="cash",
                source_id=0,
                target_type="account",
                target_id=account.id,
                amount=initial_balance,
                description="Первичное пополнение счета",
            )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="open_account",
            details=f"Открыт счет #{account.id} в банке {bank.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return account

    def close_account(self, client_id: int, account_id: int) -> None:
        client = self.lookup.get_active_client(client_id)
        account = self.lookup.get_account(account_id)
        self.validation.ensure_owner(client.id, account.owner_id, "счет")
        self.validation.ensure_product_open(account, "Счет")
        self.validation.ensure_not_blocked(account, "Счет")
        if account.balance > 0:
            raise ValidationError("Счет можно закрыть только с нулевым балансом.")

        snapshot = self.audit.clone_state()
        account.is_closed = True
        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="close_account",
            details=f"Закрыт счет #{account.id}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def create_deposit(
        self,
        client_id: int,
        bank_id: int,
        name: str,
        source_account_id: int,
        amount: float,
        interest_rate: float,
    ) -> Deposit:
        client = self.lookup.get_active_client(client_id)
        bank = self.lookup.get_bank(bank_id)
        source_account = self.lookup.get_account(source_account_id)
        self.validation.ensure_owner(client.id, source_account.owner_id, "счет")
        self.validation.ensure_product_open(source_account, "Счет")
        self.validation.ensure_not_blocked(source_account, "Счет")
        name = self.validation.validate_text(name, "Название вклада")
        amount = self.validation.validate_amount(amount)
        interest_rate = self.validation.validate_rate(interest_rate)
        if source_account.balance < amount:
            raise ValidationError("Недостаточно средств на счете для создания вклада.")

        snapshot = self.audit.clone_state()
        deposit = Deposit(
            id=self.context.state.next_deposit_id,
            owner_id=client.id,
            bank_id=bank.id,
            name=name,
            balance=round(amount, 2),
            interest_rate=interest_rate,
        )
        self.context.state.deposits[deposit.id] = deposit
        self.context.state.next_deposit_id += 1
        client.deposit_ids.append(deposit.id)
        source_account.balance = round(source_account.balance - amount, 2)
        self.transactions.create_transaction(
            source_type="account",
            source_id=source_account.id,
            target_type="deposit",
            target_id=deposit.id,
            amount=amount,
            description="Открытие вклада со счета",
        )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="create_deposit",
            details=f"Создан вклад #{deposit.id} в банке {bank.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return deposit

    def close_deposit(self, client_id: int, deposit_id: int, target_account_id: int) -> None:
        client = self.lookup.get_active_client(client_id)
        deposit = self.lookup.get_deposit(deposit_id)
        target_account = self.lookup.get_account(target_account_id)
        self.validation.ensure_owner(client.id, deposit.owner_id, "вклад")
        self.validation.ensure_owner(client.id, target_account.owner_id, "счет")
        self.validation.ensure_product_open(deposit, "Вклад")
        self.validation.ensure_product_open(target_account, "Счет")
        self.validation.ensure_not_blocked(deposit, "Вклад")
        if deposit.balance <= 0:
            raise ValidationError("Во вкладе нет средств для вывода.")

        snapshot = self.audit.clone_state()
        amount = deposit.balance
        deposit.balance = 0.0
        deposit.is_closed = True
        target_account.balance = round(target_account.balance + amount, 2)
        self.transactions.create_transaction(
            source_type="deposit",
            source_id=deposit.id,
            target_type="account",
            target_id=target_account.id,
            amount=amount,
            description="Закрытие вклада и перевод на счет",
        )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="close_deposit",
            details=f"Закрыт вклад #{deposit.id}, средства переведены на счет #{target_account.id}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def transfer_between_products(
        self,
        client_id: int,
        source_type: str,
        source_id: int,
        target_type: str,
        target_id: int,
        amount: float,
    ) -> None:
        client = self.lookup.get_active_client(client_id)
        source = self.lookup.get_product(source_type, source_id)
        target = self.lookup.get_product(target_type, target_id)
        self.validation.ensure_owner(client.id, source.owner_id, "источник")
        self.validation.ensure_product_open(source, "Источник")
        self.validation.ensure_product_open(target, "Получатель")
        self.validation.ensure_not_blocked(source, "Источник")
        amount = self.validation.validate_amount(amount)
        if source_type == target_type and source_id == target_id:
            raise ValidationError("Нельзя перевести средства на тот же самый продукт.")
        if source.balance < amount:
            raise ValidationError("Недостаточно средств для перевода.")

        snapshot = self.audit.clone_state()
        source.balance = round(source.balance - amount, 2)
        target.balance = round(target.balance + amount, 2)
        self.transactions.create_transaction(
            source_type=source_type,
            source_id=source_id,
            target_type=target_type,
            target_id=target_id,
            amount=amount,
            description="Перевод между продуктами",
        )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="transfer_between_products",
            details=f"Перевод {amount:.2f} со {source_type} #{source_id} на {target_type} #{target_id}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def accumulate_deposit(self, client_id: int, deposit_id: int) -> float:
        client = self.lookup.get_active_client(client_id)
        deposit = self.lookup.get_deposit(deposit_id)
        self.validation.ensure_owner(client.id, deposit.owner_id, "вклад")
        self.validation.ensure_product_open(deposit, "Вклад")
        if deposit.balance <= 0:
            raise ValidationError("Нельзя начислить проценты на пустой вклад.")

        snapshot = self.audit.clone_state()
        income = round(deposit.balance * deposit.interest_rate, 2)
        deposit.balance = round(deposit.balance + income, 2)
        self.transactions.create_transaction(
            source_type="system",
            source_id=0,
            target_type="deposit",
            target_id=deposit.id,
            amount=income,
            description="Начисление процентов по вкладу",
        )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="accumulate_deposit",
            details=f"Начислены проценты {income:.2f} на вклад #{deposit.id}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return income

    def submit_salary_application(self, client_id: int, enterprise_id: int) -> SalaryApplication:
        client = self.lookup.get_active_client(client_id)
        enterprise = self.lookup.get_enterprise(enterprise_id)
        if enterprise.id not in client.enterprise_ids:
            raise ValidationError("Клиент не является сотрудником выбранного предприятия.")
        for application in self.queries.list_client_salary_applications(client.id):
            if application.enterprise_id == enterprise.id and application.status in {
                ApplicationStatus.PENDING,
                ApplicationStatus.APPROVED,
            }:
                raise ValidationError("Заявка по этому предприятию уже существует.")

        snapshot = self.audit.clone_state()
        application = SalaryApplication(
            id=self.context.state.next_application_id,
            client_id=client.id,
            enterprise_id=enterprise.id,
        )
        self.context.state.salary_applications[application.id] = application
        self.context.state.next_application_id += 1
        client.salary_application_ids.append(application.id)

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="submit_salary_application",
            details=f"Подана заявка #{application.id} на зарплатный проект {enterprise.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return application

    def receive_salary(self, client_id: int, enterprise_id: int, target_account_id: int) -> float:
        client = self.lookup.get_active_client(client_id)
        enterprise = self.lookup.get_enterprise(enterprise_id)
        account = self.lookup.get_account(target_account_id)
        self.validation.ensure_owner(client.id, account.owner_id, "счет")
        self.validation.ensure_product_open(account, "Счет")
        if enterprise.id not in client.enterprise_ids:
            raise ValidationError("Клиент больше не числится в выбранном предприятии.")
        application = self.lookup.find_approved_application(client.id, enterprise.id)

        snapshot = self.audit.clone_state()
        amount = enterprise.salary_amount
        account.balance = round(account.balance + amount, 2)
        self.transactions.create_transaction(
            source_type="enterprise",
            source_id=enterprise.id,
            target_type="account",
            target_id=account.id,
            amount=amount,
            description=f"Получение зарплаты по заявке #{application.id}",
        )

        log = self.audit.append_log(
            actor_id=client.id,
            actor_role=client.role.value,
            action="receive_salary",
            details=f"Получена зарплата {amount:.2f} от предприятия {enterprise.name} на счет #{account.id}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)
        return amount


class ManagerService:
    def __init__(
        self,
        lookup: LookupService,
        validation: ValidationService,
        audit: AuditService,
    ) -> None:
        self.lookup = lookup
        self.validation = validation
        self.audit = audit

    def confirm_client(self, manager_id: int, client_id: int) -> None:
        manager = self.lookup.get_manager(manager_id)
        client = self.lookup.get_client(client_id)
        if client.registration_status == RegistrationStatus.APPROVED:
            raise ValidationError("Клиент уже подтвержден.")

        snapshot = self.audit.clone_state()
        client.registration_status = RegistrationStatus.APPROVED
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="confirm_client",
            details=f"Менеджер подтвердил клиента {client.full_name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def add_client_to_enterprise(self, manager_id: int, client_id: int, enterprise_id: int) -> None:
        manager = self.lookup.get_manager(manager_id)
        client = self.lookup.get_active_client(client_id)
        enterprise = self.lookup.get_enterprise(enterprise_id)
        if client.id in enterprise.employee_ids:
            raise ValidationError("Клиент уже числится в предприятии.")

        snapshot = self.audit.clone_state()
        enterprise.employee_ids.append(client.id)
        client.enterprise_ids.append(enterprise.id)
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="add_client_to_enterprise",
            details=f"Клиент {client.full_name} добавлен в предприятие {enterprise.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def remove_client_from_enterprise(self, manager_id: int, client_id: int, enterprise_id: int) -> None:
        manager = self.lookup.get_manager(manager_id)
        client = self.lookup.get_active_client(client_id)
        enterprise = self.lookup.get_enterprise(enterprise_id)
        if client.id not in enterprise.employee_ids:
            raise ValidationError("Клиент не состоит в этом предприятии.")

        snapshot = self.audit.clone_state()
        enterprise.employee_ids.remove(client.id)
        client.enterprise_ids.remove(enterprise.id)
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="remove_client_from_enterprise",
            details=f"Клиент {client.full_name} удален из предприятия {enterprise.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def approve_salary_application(self, manager_id: int, application_id: int) -> None:
        manager = self.lookup.get_manager(manager_id)
        application = self.lookup.get_application(application_id)
        if application.status == ApplicationStatus.APPROVED:
            raise ValidationError("Заявка уже подтверждена.")

        snapshot = self.audit.clone_state()
        application.status = ApplicationStatus.APPROVED
        enterprise = self.lookup.get_enterprise(application.enterprise_id)
        client = self.lookup.get_client(application.client_id)
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="approve_salary_application",
            details=f"Одобрена заявка #{application.id} клиента {client.full_name} для предприятия {enterprise.name}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def set_account_blocked(self, manager_id: int, account_id: int, blocked: bool) -> None:
        manager = self.lookup.get_manager(manager_id)
        account = self.lookup.get_account(account_id)
        self.validation.ensure_product_open(account, "Счет")
        if account.is_blocked == blocked:
            raise ValidationError("Состояние счета уже установлено.")

        snapshot = self.audit.clone_state()
        account.is_blocked = blocked
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="set_account_blocked",
            details=f"Счет #{account.id} {'заблокирован' if blocked else 'разблокирован'}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)

    def set_deposit_blocked(self, manager_id: int, deposit_id: int, blocked: bool) -> None:
        manager = self.lookup.get_manager(manager_id)
        deposit = self.lookup.get_deposit(deposit_id)
        self.validation.ensure_product_open(deposit, "Вклад")
        if deposit.is_blocked == blocked:
            raise ValidationError("Состояние вклада уже установлено.")

        snapshot = self.audit.clone_state()
        deposit.is_blocked = blocked
        log = self.audit.append_log(
            actor_id=manager.id,
            actor_role=manager.role.value,
            action="set_deposit_blocked",
            details=f"Вклад #{deposit.id} {'заблокирован' if blocked else 'разблокирован'}.",
            reversible=True,
        )
        self.audit.remember_snapshot(log.id, snapshot)


class AdminService:
    def __init__(self, lookup: LookupService, audit: AuditService) -> None:
        self.lookup = lookup
        self.audit = audit

    def undo_last_reversible_action(self, admin_id: int) -> AuditLog:
        admin = self.lookup.get_admin(admin_id)
        target_log = self.audit.find_last_reversible_log()
        self.audit.restore_snapshot(target_log.id)
        target_log.undone = True
        self.audit.append_log(
            actor_id=admin.id,
            actor_role=admin.role.value,
            action="undo_action",
            details=f"Администратор отменил действие #{target_log.id}: {target_log.details}",
            reversible=False,
        )
        return target_log


class DemoDataSeeder:
    def __init__(
        self,
        context: SystemContext,
        factory: FactoryService,
        transactions: TransactionService,
        audit: AuditService,
    ) -> None:
        self.context = context
        self.factory = factory
        self.transactions = transactions
        self.audit = audit

    def seed(self) -> None:
        manager = self.factory.create_user(Role.MANAGER, "manager", "manager123", "Ирина Менеджер")
        self.factory.create_user(Role.ADMIN, "admin", "admin123", "Системный Администратор")
        alpha_bank = self.factory.create_bank("Альфа Банк")
        nova_bank = self.factory.create_bank("Нова Банк")
        invest_bank = self.factory.create_bank("Инвест Банк")
        techsoft = self.factory.create_enterprise("TechSoft", 2500.0)
        greenfood = self.factory.create_enterprise("GreenFood", 1800.0)
        self.factory.create_enterprise("LogiTrans", 2200.0)

        alice = self.factory.create_user(Role.CLIENT, "alice", "alice123", "Алиса Клиент", approved=True)
        bob = self.factory.create_user(Role.CLIENT, "bob", "bob123", "Боб Клиент", approved=True)
        pending = self.factory.create_user(Role.CLIENT, "newuser", "newuser123", "Новый Клиент", approved=False)

        alice_account = self.factory.create_account(alice.id, alpha_bank.id, "Основной счет", 2400.0)
        alice_reserve = self.factory.create_account(alice.id, nova_bank.id, "Резервный счет", 200.0)
        bob_account = self.factory.create_account(bob.id, invest_bank.id, "Зарплатный счет", 0.0)
        alice_deposit = self.factory.create_deposit(alice.id, alpha_bank.id, "Накопительный вклад", 0.0, 0.08)

        self.factory.attach_client_to_enterprise(alice.id, techsoft.id)
        self.factory.attach_client_to_enterprise(bob.id, greenfood.id)

        approved_application = SalaryApplication(
            id=self.context.state.next_application_id,
            client_id=alice.id,
            enterprise_id=techsoft.id,
            status=ApplicationStatus.APPROVED,
        )
        self.context.state.salary_applications[approved_application.id] = approved_application
        self.context.state.next_application_id += 1
        alice.salary_application_ids.append(approved_application.id)

        pending_application = SalaryApplication(
            id=self.context.state.next_application_id,
            client_id=bob.id,
            enterprise_id=greenfood.id,
            status=ApplicationStatus.PENDING,
        )
        self.context.state.salary_applications[pending_application.id] = pending_application
        self.context.state.next_application_id += 1
        bob.salary_application_ids.append(pending_application.id)

        self.transactions.apply_external_credit(
            target_type="account",
            target_id=alice_account.id,
            amount=2500.0,
            source_type="enterprise",
            source_id=techsoft.id,
            description="Демонстрационное начисление зарплаты",
        )
        self.transactions.apply_transfer(
            source_type="account",
            source_id=alice_account.id,
            target_type="deposit",
            target_id=alice_deposit.id,
            amount=1200.0,
            description="Демонстрационное создание вклада",
        )
        self.transactions.apply_transfer(
            source_type="account",
            source_id=alice_account.id,
            target_type="account",
            target_id=alice_reserve.id,
            amount=500.0,
            description="Демонстрационный перевод между счетами",
        )
        self.transactions.apply_external_credit(
            target_type="account",
            target_id=bob_account.id,
            amount=900.0,
            source_type="cash",
            source_id=0,
            description="Демонстрационное пополнение счета",
        )

        self.audit.append_log(
            actor_id=manager.id,
            actor_role=Role.MANAGER.value,
            action="seed_system",
            details=f"Система заполнена демонстрационными данными. Есть ожидающий клиент #{pending.id}.",
            reversible=False,
        )
