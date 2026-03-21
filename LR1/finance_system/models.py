from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    CLIENT = "client"
    MANAGER = "manager"
    ADMIN = "admin"


class RegistrationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"


class ApplicationStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"


@dataclass
class User:
    id: int
    username: str
    password: str
    full_name: str
    role: Role


@dataclass
class Client(User):
    registration_status: RegistrationStatus = RegistrationStatus.PENDING
    account_ids: list[int] = field(default_factory=list)
    deposit_ids: list[int] = field(default_factory=list)
    enterprise_ids: list[int] = field(default_factory=list)
    salary_application_ids: list[int] = field(default_factory=list)


@dataclass
class Manager(User):
    pass

@dataclass
class Admin(User):
    pass

@dataclass
class Bank:
    id: int
    name: str


@dataclass
class FinancialProduct:
    id: int
    owner_id: int
    bank_id: int
    name: str
    balance: float = 0.0
    is_blocked: bool = False
    is_closed: bool = False
    transaction_ids: list[int] = field(default_factory=list)


@dataclass
class Account(FinancialProduct):
    pass


@dataclass
class Deposit(FinancialProduct):
    interest_rate: float = 0.05


@dataclass
class Enterprise:
    id: int
    name: str
    salary_amount: float
    employee_ids: list[int] = field(default_factory=list)


@dataclass
class SalaryApplication:
    id: int
    client_id: int
    enterprise_id: int
    status: ApplicationStatus = ApplicationStatus.PENDING


@dataclass
class Transaction:
    id: int
    source_type: str
    source_id: int
    target_type: str
    target_id: int
    amount: float
    description: str
    created_at: str


@dataclass
class AuditLog:
    id: int
    actor_id: int
    actor_role: str
    action: str
    details: str
    created_at: str
    reversible: bool = False
    undone: bool = False


@dataclass
class SystemState:
    users: dict[int, User] = field(default_factory=dict)
    banks: dict[int, Bank] = field(default_factory=dict)
    accounts: dict[int, Account] = field(default_factory=dict)
    deposits: dict[int, Deposit] = field(default_factory=dict)
    enterprises: dict[int, Enterprise] = field(default_factory=dict)
    salary_applications: dict[int, SalaryApplication] = field(default_factory=dict)
    transactions: dict[int, Transaction] = field(default_factory=dict)
    next_user_id: int = 1
    next_bank_id: int = 1
    next_account_id: int = 1
    next_deposit_id: int = 1
    next_enterprise_id: int = 1
    next_application_id: int = 1
    next_transaction_id: int = 1
