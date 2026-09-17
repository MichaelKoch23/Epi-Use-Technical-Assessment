from __future__ import annotations

import argparse
import asyncio
import random
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import TypedDict

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.passwords import hash_password
from app.db.session import async_session_factory
from app.models.app_user import AppUser
from app.models.employee import Employee
from app.services.employee_service import EmployeeService

SEED_ACTOR_EMAIL = "seed@employee.example.com"

DEMO_ACCOUNTS = [
    ("admin@epiuse-demo.com", "EpiUse-Admin-2026!", "hr_admin"),
    ("viewer@epiuse-demo.com", "EpiUse-Viewer-2026!", "viewer"),
]

FIRST_NAMES = [
    "Thabo", "Sipho", "Bongani", "Mandla", "Kagiso", "Lwazi", "Tumelo", "Sizwe",
    "Nomvula", "Zanele", "Lindiwe", "Thandeka", "Nokuthula", "Sindisiwe", "Ayanda", "Precious",
    "Pieter", "Johan", "Hendrik", "Willem", "Andries", "Francois", "Stefan", "Riaan",
    "Anneke", "Elmarie", "Marietjie", "Susara", "Retief", "Charlotte", "Ilse", "Karin",
    "James", "Michael", "David", "Robert", "Sarah", "Emma", "Jessica", "Laura",
    "Kavitha", "Priya", "Ravi", "Suresh", "Anil", "Kiran", "Nadia", "Yusuf",
    "Xolani", "Mzwandile", "Katlego", "Karabo", "Lerato", "Dineo", "Palesa", "Boitumelo",
]  # fmt: skip

LAST_NAMES = [
    "Nkosi", "Dlamini", "Khumalo", "Zulu", "Mokoena", "Sithole", "Mahlangu", "Ndlovu",
    "Van der Merwe", "Botha", "Pretorius", "Du Toit", "Nel", "Fourie", "Kruger", "Van Wyk",
    "Smith", "Williams", "Brown", "Jones", "Miller", "Davies", "Wilson", "Taylor",
    "Naidoo", "Pillay", "Govender", "Reddy", "Moodley", "Chetty", "Naicker", "Moonsamy",
    "Molefe", "Mabaso", "Mthembu", "Cele", "Buthelezi", "Radebe", "Motaung", "Tshabalala",
]  # fmt: skip


class Department(TypedDict):
    exec_title: str
    director_title: str
    manager_title: str
    ic_titles: list[str]


DEPARTMENTS: list[Department] = [
    {
        "exec_title": "Chief Technology Officer",
        "director_title": "Director of Engineering",
        "manager_title": "Engineering Manager",
        "ic_titles": [
            "Software Engineer",
            "DevOps Engineer",
            "QA Engineer",
            "Data Engineer",
        ],
    },
    {
        "exec_title": "Chief Financial Officer",
        "director_title": "Finance Director",
        "manager_title": "Finance Manager",
        "ic_titles": [
            "Financial Accountant",
            "Payroll Administrator",
            "Financial Analyst",
        ],
    },
    {
        "exec_title": "Chief Operating Officer",
        "director_title": "Operations Director",
        "manager_title": "Operations Manager",
        "ic_titles": [
            "Operations Coordinator",
            "Logistics Analyst",
            "Supply Chain Specialist",
        ],
    },
    {
        "exec_title": "Chief Human Resources Officer",
        "director_title": "HR Director",
        "manager_title": "HR Manager",
        "ic_titles": [
            "HR Business Partner",
            "Recruitment Specialist",
            "Payroll Officer",
        ],
    },
    {
        "exec_title": "Chief Commercial Officer",
        "director_title": "Sales Director",
        "manager_title": "Sales Manager",
        "ic_titles": [
            "Account Executive",
            "Sales Representative",
            "Business Development Rep",
        ],
    },
]

SALARY_BANDS: dict[str, tuple[Decimal, Decimal]] = {
    "ceo": (Decimal(2600000), Decimal(3400000)),
    "exec": (Decimal(1700000), Decimal(2200000)),
    "director": (Decimal(1050000), Decimal(1400000)),
    "manager": (Decimal(620000), Decimal(860000)),
    "ic": (Decimal(340000), Decimal(620000)),
}


def _salary(band: str) -> Decimal:
    low, high = SALARY_BANDS[band]
    step = Decimal(500)
    span = int((high - low) / step)
    return low + step * random.randint(0, span)


def _birth_date() -> date:
    age_days = random.randint(23 * 365, 62 * 365)
    return datetime.now(UTC).date() - timedelta(days=age_days)


@dataclass
class _Counter:
    value: int = 0

    def next(self) -> int:
        self.value += 1
        return self.value


_used_names: set[tuple[str, str]] = set()
_employee_numbers = _Counter()
_email_suffixes = _Counter()


def _unique_name() -> tuple[str, str]:
    for _ in range(50):
        candidate = (random.choice(FIRST_NAMES), random.choice(LAST_NAMES))
        if candidate not in _used_names:
            _used_names.add(candidate)
            return candidate
    return random.choice(FIRST_NAMES), random.choice(LAST_NAMES)


async def _create(
    service: EmployeeService,
    *,
    position: str,
    band: str,
    manager_id: uuid.UUID | None,
    actor_id: uuid.UUID,
) -> Employee:
    first, last = _unique_name()
    number = _employee_numbers.next()
    email_local = (
        f"{first.lower()}.{last.lower().replace(' ', '-')}.{_email_suffixes.next()}"
    )
    return await service.create(
        employee_number=f"EMP-{number:05d}",
        first_name=first,
        last_name=last,
        email=f"{email_local}@employee.example.com",
        birth_date=_birth_date(),
        position=position,
        salary=_salary(band),
        currency="ZAR",
        manager_id=manager_id,
        actor_id=actor_id,
    )


async def _ensure_seed_actor(session: AsyncSession) -> uuid.UUID:
    existing = (
        await session.execute(select(AppUser).where(AppUser.email == SEED_ACTOR_EMAIL))
    ).scalar_one_or_none()
    if existing is not None:
        return existing.id

    actor = AppUser(
        email=SEED_ACTOR_EMAIL, password_hash="not-a-real-hash", role="hr_admin"
    )
    session.add(actor)
    await session.commit()
    return actor.id


async def _ensure_demo_accounts(session: AsyncSession) -> None:
    for email, password, role in DEMO_ACCOUNTS:
        existing = (
            await session.execute(select(AppUser).where(AppUser.email == email))
        ).scalar_one_or_none()
        password_hash = hash_password(password)
        if existing is None:
            session.add(AppUser(email=email, password_hash=password_hash, role=role))
        else:
            existing.password_hash = password_hash
            existing.role = role
    await session.commit()
    print(f"demo accounts ready: {', '.join(email for email, _, _ in DEMO_ACCOUNTS)}")


async def _reset(session: AsyncSession) -> None:
    await session.execute(text("TRUNCATE TABLE audit_log, employee"))
    await session.commit()


async def seed(target: int, *, reset: bool) -> None:
    async with async_session_factory() as session:
        if reset:
            await _reset(session)

        await _ensure_demo_accounts(session)
        actor_id = await _ensure_seed_actor(session)
        service = EmployeeService(session)

        execs = len(DEPARTMENTS)
        directors_per_exec = 3
        managers_per_director = 4
        directors_total = execs * directors_per_exec
        managers_total = directors_total * managers_per_director
        base = 1 + execs + directors_total + managers_total
        remaining = max(target - base, managers_total)
        ics_per_manager = max(1, round(remaining / managers_total))

        ceo = await _create(
            service,
            position="Chief Executive Officer",
            band="ceo",
            manager_id=None,
            actor_id=actor_id,
        )
        await session.commit()
        total = 1
        print(f"CEO: {ceo.first_name} {ceo.last_name}")

        for dept in DEPARTMENTS:
            executive = await _create(
                service,
                position=dept["exec_title"],
                band="exec",
                manager_id=ceo.id,
                actor_id=actor_id,
            )
            total += 1

            for _ in range(directors_per_exec):
                director = await _create(
                    service,
                    position=dept["director_title"],
                    band="director",
                    manager_id=executive.id,
                    actor_id=actor_id,
                )
                total += 1

                for _ in range(managers_per_director):
                    manager = await _create(
                        service,
                        position=dept["manager_title"],
                        band="manager",
                        manager_id=director.id,
                        actor_id=actor_id,
                    )
                    total += 1

                    for _ in range(ics_per_manager):
                        await _create(
                            service,
                            position=random.choice(dept["ic_titles"]),
                            band="ic",
                            manager_id=manager.id,
                            actor_id=actor_id,
                        )
                        total += 1

            await session.commit()
            print(f"  {dept['exec_title']} branch done - {total} employees so far")

        print(f"seed complete: {total} employees (target was ~{target})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--employees", type=int, default=250, help="approximate headcount to generate"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="truncate employee and audit_log data first",
    )
    args = parser.parse_args()

    asyncio.run(seed(args.employees, reset=args.reset))


if __name__ == "__main__":
    main()
