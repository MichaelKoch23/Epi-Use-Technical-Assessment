"""§ analytics: the org-structure dashboard. Exercised at the router-function
level, like the other tests here (see test_hierarchy_roots.py for why).
"""

from __future__ import annotations

import json
import uuid
from decimal import Decimal

import pytest
from fastapi import Response

from app.core.constants import DEEP_CHAIN_THRESHOLD, WIDE_SPAN_THRESHOLD
from app.core.exceptions import EmployeeNotFound
from app.core.security import Principal
from app.routers.analytics import get_branch_summary, get_org_summary
from app.services.analytics_service import AnalyticsService, clear_org_summary_cache
from app.services.employee_service import EmployeeService

ADMIN = "hr_admin"
VIEWER = "viewer"


@pytest.fixture(autouse=True)
def _clear_analytics_cache():
    """The org-summary cache is process-lifetime (§ analytics: a 60-second
    in-process TTL cache keyed by role), but this suite truncates the
    database between tests - without this, a later test would be served an
    earlier test's cached result instead of fresh data."""
    clear_org_summary_cache()
    yield
    clear_org_summary_cache()


def _principal(actor_id, role: str = ADMIN) -> Principal:
    return Principal(id=actor_id, role=role)


async def test_headcount_depth_and_roots(db_session, actor_id, employee_factory):
    root = await employee_factory()
    mgr_a = await employee_factory(manager_id=root.id)
    mgr_b = await employee_factory(manager_id=root.id)
    await employee_factory(manager_id=mgr_a.id)
    await employee_factory(manager_id=mgr_a.id)
    await employee_factory(manager_id=mgr_b.id)

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    assert data.headcount == 6
    assert data.root_count == 1
    assert data.max_depth == 2
    assert {(d.depth, d.count) for d in data.depth_distribution} == {
        (0, 1),
        (1, 2),
        (2, 3),
    }


async def test_average_span_of_control_excludes_individual_contributors(
    db_session, actor_id, employee_factory
):
    root = await employee_factory()  # 2 direct reports
    mgr_a = await employee_factory(manager_id=root.id)  # 2 direct reports
    mgr_b = await employee_factory(manager_id=root.id)  # 1 direct report
    await employee_factory(manager_id=mgr_a.id)
    await employee_factory(manager_id=mgr_a.id)
    await employee_factory(manager_id=mgr_b.id)

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    # Over managers only: (2 + 2 + 1) / 3, never diluted by the three
    # individual contributors' zero-report rows.
    assert data.average_span_of_control == pytest.approx(5 / 3)
    assert data.average_span_of_control != pytest.approx(5 / 6)


async def test_soft_deleted_employee_excluded_from_headcount(
    db_session, actor_id, employee_factory
):
    root = await employee_factory()
    leaf = await employee_factory(manager_id=root.id)

    service = AnalyticsService(db_session)
    before = await service.get_org_summary(_principal(actor_id))
    assert before.headcount == 2

    await EmployeeService(db_session).soft_delete(leaf.id, actor_id=actor_id)
    await db_session.commit()
    clear_org_summary_cache()

    after = await service.get_org_summary(_principal(actor_id))
    assert after.headcount == before.headcount - 1


async def test_wide_span_anomaly_fires_above_threshold_only(
    db_session, actor_id, employee_factory
):
    root = await employee_factory()
    at_threshold = await employee_factory(manager_id=root.id)
    over_threshold = await employee_factory(manager_id=root.id)
    for _ in range(WIDE_SPAN_THRESHOLD):
        await employee_factory(manager_id=at_threshold.id)
    for _ in range(WIDE_SPAN_THRESHOLD + 1):
        await employee_factory(manager_id=over_threshold.id)

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    wide_span_ids = {row.id for row in data.anomalies.wide_spans}
    assert over_threshold.id in wide_span_ids
    assert at_threshold.id not in wide_span_ids


async def test_single_report_manager_anomaly(db_session, actor_id, employee_factory):
    root = await employee_factory()
    single_report_manager = await employee_factory(manager_id=root.id)
    two_report_manager = await employee_factory(manager_id=root.id)
    await employee_factory(manager_id=single_report_manager.id)
    await employee_factory(manager_id=two_report_manager.id)
    await employee_factory(manager_id=two_report_manager.id)

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    single_report_ids = {row.id for row in data.anomalies.single_report_managers}
    assert single_report_manager.id in single_report_ids
    assert two_report_manager.id not in single_report_ids


async def test_deep_chain_anomaly_fires_at_threshold_not_below(
    db_session, actor_id, employee_factory
):
    current = await employee_factory()
    chain = [current]
    for _ in range(DEEP_CHAIN_THRESHOLD):
        current = await employee_factory(manager_id=current.id)
        chain.append(current)

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    deep_chain_ids = {row.id for row in data.anomalies.deep_chains}
    at_threshold_employee = chain[DEEP_CHAIN_THRESHOLD]
    one_below_threshold_employee = chain[DEEP_CHAIN_THRESHOLD - 1]
    assert at_threshold_employee.id in deep_chain_ids
    assert one_below_threshold_employee.id not in deep_chain_ids


async def test_unreachable_detection_after_manager_deleted_without_reparenting(
    db_session, actor_id, employee_factory
):
    root = await employee_factory()
    mid_manager = await employee_factory(manager_id=root.id)
    leaf = await employee_factory(manager_id=mid_manager.id)

    # Soft-delete the manager directly (not via a `DeletionPolicy`, which
    # would reparent `leaf`) so `leaf` is left pointing at a dead manager -
    # the only way this anomaly can occur (§ analytics).
    await EmployeeService(db_session).soft_delete(mid_manager.id, actor_id=actor_id)
    await db_session.commit()

    service = AnalyticsService(db_session)
    data = await service.get_org_summary(_principal(actor_id))

    unreachable_ids = {row.id for row in data.anomalies.unreachable}
    assert leaf.id in unreachable_ids
    assert root.id not in unreachable_ids


async def test_viewer_response_has_no_cost_key(db_session, actor_id, employee_factory):
    await employee_factory()

    result = await get_org_summary(
        response=Response(), session=db_session, principal=_principal(actor_id, VIEWER)
    )
    body = json.loads(result.model_dump_json())

    assert "cost" not in body


async def test_admin_response_has_cost_with_string_monetary_values(
    db_session, actor_id, employee_factory
):
    await employee_factory(salary=Decimal("123456.78"))

    result = await get_org_summary(
        response=Response(), session=db_session, principal=_principal(actor_id, ADMIN)
    )
    body = json.loads(result.model_dump_json())

    assert "cost" in body
    assert isinstance(body["cost"]["total_annual"], str)
    assert isinstance(body["cost"]["average"], str)
    assert isinstance(body["cost"]["median"], str)


async def test_branch_summary_404_for_unknown_employee(db_session, actor_id):
    with pytest.raises(EmployeeNotFound):
        await get_branch_summary(
            employee_id=uuid.uuid4(), session=db_session, principal=_principal(actor_id)
        )


async def test_branch_summary_404_for_soft_deleted_employee(
    db_session, actor_id, employee_factory
):
    employee = await employee_factory()
    await EmployeeService(db_session).soft_delete(employee.id, actor_id=actor_id)
    await db_session.commit()

    with pytest.raises(EmployeeNotFound):
        await get_branch_summary(
            employee_id=employee.id, session=db_session, principal=_principal(actor_id)
        )


async def test_branch_headcount_includes_the_root(
    db_session, actor_id, employee_factory
):
    root = await employee_factory()
    child_a = await employee_factory(manager_id=root.id)
    await employee_factory(manager_id=root.id)
    await employee_factory(manager_id=child_a.id)

    result = await get_branch_summary(
        employee_id=root.id, session=db_session, principal=_principal(actor_id)
    )

    assert result.headcount == 4
    assert result.direct_reports == 2
    assert result.depth_below == 2
