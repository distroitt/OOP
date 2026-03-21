from __future__ import annotations

from .models import Account, Client, Deposit, RegistrationStatus, Role
from .system import (
    FinanceSystemError,
    FinancialSystem,
    ValidationError,
)


class ConsoleApp:
    def __init__(self) -> None:
        self.system = FinancialSystem()

    def run(self) -> None:
        print("Система управления финансами")
        print("Демо-доступ: manager/manager123, admin/admin123, alice/alice123, bob/bob123")
        while True:
            print("\nГлавное меню")
            print("1. Войти")
            print("2. Зарегистрировать клиента")
            print("0. Выход")
            choice = input("Выберите действие: ").strip()

            if choice == "1":
                self._login()
            elif choice == "2":
                self._register_client()
            elif choice == "0":
                print("Работа завершена.")
                return
            else:
                print("Неизвестная команда.")

    def _login(self) -> None:
        username = input("Логин: ").strip()
        password = input("Пароль: ").strip()
        try:
            user = self.system.authenticate(username, password)
        except FinanceSystemError as error:
            print(error)
            return

        if user.role == Role.CLIENT:
            self._client_menu(user.id)
        elif user.role == Role.MANAGER:
            self._manager_menu(user.id)
        else:
            self._admin_menu(user.id)

    def _register_client(self) -> None:
        username = input("Новый логин: ").strip()
        password = input("Пароль: ").strip()
        full_name = input("ФИО: ").strip()
        try:
            client = self.system.register_client(username, password, full_name)
        except FinanceSystemError as error:
            print(error)
            return
        print(f"Клиент #{client.id} зарегистрирован. Ожидайте подтверждения менеджера.")

    def _client_menu(self, user_id: int) -> None:
        while True:
            client = self.system.get_user(user_id)
            assert isinstance(client, Client)
            print(f"\nКлиент: {client.full_name} ({client.registration_status.value})")
            if client.registration_status != RegistrationStatus.APPROVED:
                print("Аккаунт еще не подтвержден менеджером.")
                print("1. Посмотреть банки")
                print("0. Выйти")
                choice = input("Выберите действие: ").strip()
                if choice == "1":
                    self._print_banks()
                elif choice == "0":
                    return
                else:
                    print("Неизвестная команда.")
                continue

            print("1. Мои продукты")
            print("2. Все банки")
            print("3. Открыть счет")
            print("4. Закрыть счет")
            print("5. Создать вклад")
            print("6. Закрыть вклад")
            print("7. Перевод между счетом и вкладом")
            print("8. Начислить проценты по вкладу")
            print("9. История счета")
            print("10. История вклада")
            print("11. Доступные предприятия")
            print("12. Подать заявку на зарплатный проект")
            print("13. Получить зарплату")
            print("0. Выйти")
            choice = input("Выберите действие: ").strip()

            try:
                if choice == "1":
                    self._print_client_products(client.id)
                elif choice == "2":
                    self._print_banks()
                elif choice == "3":
                    self._open_account(client.id)
                elif choice == "4":
                    self._close_account(client.id)
                elif choice == "5":
                    self._create_deposit(client.id)
                elif choice == "6":
                    self._close_deposit(client.id)
                elif choice == "7":
                    self._transfer_between_products(client.id)
                elif choice == "8":
                    self._accumulate_deposit(client.id)
                elif choice == "9":
                    self._print_account_history(client.id)
                elif choice == "10":
                    self._print_deposit_history(client.id)
                elif choice == "11":
                    self._print_enterprises(client.id)
                elif choice == "12":
                    self._submit_salary_application(client.id)
                elif choice == "13":
                    self._receive_salary(client.id)
                elif choice == "0":
                    return
                else:
                    print("Неизвестная команда.")
            except FinanceSystemError as error:
                print(error)

    def _manager_menu(self, user_id: int) -> None:
        while True:
            manager = self.system.get_user(user_id)
            print(f"\nМенеджер: {manager.username}")
            print("1. Неподтвержденные клиенты")
            print("2. Подтвердить клиента")
            print("3. Предприятия и сотрудники")
            print("4. Добавить клиента в предприятие")
            print("5. Удалить клиента из предприятия")
            print("6. Заявки на зарплатный проект")
            print("7. Одобрить заявку")
            print("8. Заблокировать/разблокировать счет")
            print("9. Заблокировать/разблокировать вклад")
            print("10. История счета клиента")
            print("0. Выйти")
            choice = input("Выберите действие: ").strip()

            try:
                if choice == "1":
                    self._print_pending_clients()
                elif choice == "2":
                    client_id = self._input_int("ID клиента: ")
                    self.system.confirm_client(user_id, client_id)
                    print("Клиент подтвержден.")
                elif choice == "3":
                    self._print_enterprises_with_employees()
                elif choice == "4":
                    client_id = self._input_int("ID клиента: ")
                    enterprise_id = self._input_int("ID предприятия: ")
                    self.system.add_client_to_enterprise(user_id, client_id, enterprise_id)
                    print("Клиент добавлен в предприятие.")
                elif choice == "5":
                    client_id = self._input_int("ID клиента: ")
                    enterprise_id = self._input_int("ID предприятия: ")
                    self.system.remove_client_from_enterprise(user_id, client_id, enterprise_id)
                    print("Клиент удален из предприятия.")
                elif choice == "6":
                    self._print_pending_applications()
                elif choice == "7":
                    application_id = self._input_int("ID заявки: ")
                    self.system.approve_salary_application(user_id, application_id)
                    print("Заявка одобрена.")
                elif choice == "8":
                    account_id = self._input_int("ID счета: ")
                    blocked = self._input_blocked_flag()
                    self.system.set_account_blocked(user_id, account_id, blocked)
                    print("Состояние счета обновлено.")
                elif choice == "9":
                    deposit_id = self._input_int("ID вклада: ")
                    blocked = self._input_blocked_flag()
                    self.system.set_deposit_blocked(user_id, deposit_id, blocked)
                    print("Состояние вклада обновлено.")
                elif choice == "10":
                    self._print_account_history()
                elif choice == "0":
                    return
                else:
                    print("Неизвестная команда.")
            except FinanceSystemError as error:
                print(error)

    def _admin_menu(self, user_id: int) -> None:
        while True:
            print("\nАдминистратор")
            print("1. Просмотреть логи")
            print("2. Отменить последнее действие клиента или менеджера")
            print("0. Выйти")
            choice = input("Выберите действие: ").strip()

            try:
                if choice == "1":
                    self._print_audit_logs()
                elif choice == "2":
                    log = self.system.undo_last_reversible_action(user_id)
                    print(f"Отменено действие #{log.id}: {log.details}")
                elif choice == "0":
                    return
                else:
                    print("Неизвестная команда.")
            except FinanceSystemError as error:
                print(error)

    def _open_account(self, client_id: int) -> None:
        self._print_banks()
        bank_id = self._input_int("ID банка: ")
        name = input("Название счета: ").strip()
        balance = self._input_float("Начальный баланс: ")
        account = self.system.open_account(client_id, bank_id, name, balance)
        print(f"Счет #{account.id} успешно открыт.")

    def _close_account(self, client_id: int) -> None:
        self._print_client_products(client_id)
        account_id = self._input_int("ID счета для закрытия: ")
        self.system.close_account(client_id, account_id)
        print("Счет закрыт.")

    def _create_deposit(self, client_id: int) -> None:
        self._print_banks()
        self._print_client_products(client_id)
        bank_id = self._input_int("ID банка: ")
        name = input("Название вклада: ").strip()
        source_account_id = self._input_int("ID счета-источника: ")
        amount = self._input_float("Сумма вклада: ")
        interest_rate = self._input_float("Ставка вклада (например 0.08): ")
        deposit = self.system.create_deposit(client_id, bank_id, name, source_account_id, amount, interest_rate)
        print(f"Вклад #{deposit.id} создан.")

    def _close_deposit(self, client_id: int) -> None:
        self._print_client_products(client_id)
        deposit_id = self._input_int("ID вклада для закрытия: ")
        target_account_id = self._input_int("ID счета для вывода: ")
        self.system.close_deposit(client_id, deposit_id, target_account_id)
        print("Вклад закрыт.")

    def _transfer_between_products(self, client_id: int) -> None:
        self._print_client_products(client_id)
        source_type = self._input_product_type("Тип источника (account/deposit): ")
        source_id = self._input_int("ID источника: ")
        target_type = self._input_product_type("Тип получателя (account/deposit): ")
        target_id = self._input_int("ID получателя: ")
        amount = self._input_float("Сумма перевода: ")
        self.system.transfer_between_products(client_id, source_type, source_id, target_type, target_id, amount)
        print("Перевод выполнен.")

    def _accumulate_deposit(self, client_id: int) -> None:
        self._print_client_products(client_id)
        deposit_id = self._input_int("ID вклада: ")
        income = self.system.accumulate_deposit(client_id, deposit_id)
        print(f"Начислено процентов: {income:.2f}")

    def _submit_salary_application(self, client_id: int) -> None:
        self._print_enterprises(client_id)
        enterprise_id = self._input_int("ID предприятия: ")
        application = self.system.submit_salary_application(client_id, enterprise_id)
        print(f"Заявка #{application.id} создана.")

    def _receive_salary(self, client_id: int) -> None:
        self._print_enterprises(client_id)
        self._print_client_products(client_id)
        enterprise_id = self._input_int("ID предприятия: ")
        account_id = self._input_int("ID счета для зачисления: ")
        amount = self.system.receive_salary(client_id, enterprise_id, account_id)
        print(f"Получена зарплата {amount:.2f}")

    def _print_client_products(self, client_id: int) -> None:
        accounts = self.system.list_client_accounts(client_id)
        deposits = self.system.list_client_deposits(client_id)
        print("\nСчета:")
        if not accounts:
            print("Нет счетов.")
        for account in accounts:
            print(self._format_account(account))

        print("\nВклады:")
        if not deposits:
            print("Нет вкладов.")
        for deposit in deposits:
            print(self._format_deposit(deposit))

    def _print_banks(self) -> None:
        print("\nБанки:")
        for bank in self.system.list_banks():
            print(f"{bank.id}. {bank.name}")

    def _print_enterprises(self, client_id: int | None = None) -> None:
        print("\nПредприятия:")
        client_enterprises: set[int] = set()
        if client_id is not None:
            client = self.system.get_user(client_id)
            assert isinstance(client, Client)
            client_enterprises = set(client.enterprise_ids)
        for enterprise in self.system.list_enterprises():
            marker = ""
            if enterprise.id in client_enterprises:
                marker = " [сотрудник]"
            print(
                f"{enterprise.id}. {enterprise.name} | зарплата {enterprise.salary_amount:.2f}"
                f"{marker}"
            )

    def _print_enterprises_with_employees(self) -> None:
        print("\nПредприятия и сотрудники:")
        for enterprise in self.system.list_enterprises():
            employee_names: list[str] = []
            for employee_id in enterprise.employee_ids:
                client = self.system.get_user(employee_id)
                assert isinstance(client, Client)
                employee_names.append(f"{client.full_name} (id={client.id})")
            employees = ", ".join(employee_names) if employee_names else "нет сотрудников"
            print(
                f"{enterprise.id}. {enterprise.name} | зарплата {enterprise.salary_amount:.2f} | "
                f"сотрудники: {employees}"
            )

    def _print_pending_clients(self) -> None:
        clients = self.system.list_pending_clients()
        print("\nНеподтвержденные клиенты:")
        if not clients:
            print("Нет клиентов на подтверждение.")
            return
        for client in clients:
            print(f"{client.id}. {client.full_name} ({client.username})")

    def _print_pending_applications(self) -> None:
        applications = self.system.list_pending_salary_applications()
        print("\nЗаявки на зарплатный проект:")
        if not applications:
            print("Нет ожидающих заявок.")
            return
        for application in applications:
            client = self.system.get_user(application.client_id)
            enterprise = next(
                item for item in self.system.list_enterprises() if item.id == application.enterprise_id
            )
            print(
                f"{application.id}. Клиент {client.username} -> {enterprise.name} "
                f"({application.status.value})"
            )

    def _print_account_history(self, client_id: int | None = None) -> None:
        account_id = self._input_int("ID счета: ")
        if client_id is None:
            history = self.system.get_account_history(account_id)
        else:
            history = self.system.get_client_account_history(client_id, account_id)
        print("\nИстория счета:")
        if not history:
            print("История пуста.")
            return
        for transaction in history:
            print(self._format_transaction(transaction))

    def _print_deposit_history(self, client_id: int | None = None) -> None:
        deposit_id = self._input_int("ID вклада: ")
        if client_id is None:
            history = self.system.get_deposit_history(deposit_id)
        else:
            history = self.system.get_client_deposit_history(client_id, deposit_id)
        print("\nИстория вклада:")
        if not history:
            print("История пуста.")
            return
        for transaction in history:
            print(self._format_transaction(transaction))

    def _print_audit_logs(self) -> None:
        logs = self.system.list_audit_logs()
        print("\nЛоги:")
        for log in logs:
            status = " [отменено]" if log.undone else ""
            print(
                f"{log.id}. {log.created_at} | {log.actor_role}#{log.actor_id} | "
                f"{log.action} | {log.details}{status}"
            )

    def _format_account(self, account: Account) -> str:
        return (
            f"Счет #{account.id} | {account.name} | баланс {account.balance:.2f} | "
            f"{self._format_state(account.is_closed, account.is_blocked)}"
        )

    def _format_deposit(self, deposit: Deposit) -> str:
        return (
            f"Вклад #{deposit.id} | {deposit.name} | баланс {deposit.balance:.2f} | "
            f"ставка {deposit.interest_rate:.2%} | {self._format_state(deposit.is_closed, deposit.is_blocked)}"
        )

    def _format_transaction(self, transaction) -> str:
        return (
            f"{transaction.id}. {transaction.created_at} | {transaction.source_type}#{transaction.source_id} -> "
            f"{transaction.target_type}#{transaction.target_id} | {transaction.amount:.2f} | "
            f"{transaction.description}"
        )

    def _format_state(self, is_closed: bool, is_blocked: bool) -> str:
        flags: list[str] = []
        flags.append("закрыт" if is_closed else "активен")
        if is_blocked:
            flags.append("заблокирован")
        return ", ".join(flags)

    def _input_int(self, prompt: str) -> int:
        raw = input(prompt).strip()
        if not raw.isdigit():
            raise ValidationError("Нужно ввести целое положительное число.")
        return int(raw)

    def _input_float(self, prompt: str) -> float:
        raw = input(prompt).strip().replace(",", ".")
        try:
            return float(raw)
        except ValueError as error:
            raise ValidationError("Нужно ввести число.") from error

    def _input_product_type(self, prompt: str) -> str:
        value = input(prompt).strip().lower()
        if value not in {"account", "deposit"}:
            raise ValidationError("Допустимые значения: account или deposit.")
        return value

    def _input_blocked_flag(self) -> bool:
        value = input("Введите 1 для блокировки или 0 для разблокировки: ").strip()
        if value not in {"0", "1"}:
            raise ValidationError("Допустимые значения: 0 или 1.")
        return value == "1"
