from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timedelta, timezone

from verification.billing import EntitlementService
from verification.billing.trials import TrialConfig, TrialLifecycleService
from verification.control_plane import ControlPlaneService, InMemoryControlPlaneStore


def test_trial_activates_for_eligible_organization_on_first_meaningful_use():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )

    updated = trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="GET /v1/nonprofit/{ein}",
        now=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )

    assert updated is not None
    assert updated.plan_code == "free"
    assert updated.trial_status == "active"
    assert updated.trial_consumed is True
    assert updated.trial_trigger_event == "GET /v1/nonprofit/{ein}"
    assert updated.trial_started_at == "2026-03-19T00:00:00+00:00"
    assert updated.trial_ends_at == "2026-04-02T00:00:00+00:00"
    history = control_plane.store.get_trial_history("123456789")
    assert history is not None
    assert history.first_account_id == account["id"]
    assert history.last_status == "active"


def test_trial_activation_is_idempotent_under_duplicate_triggers():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    started_at = datetime(2026, 3, 19, tzinfo=timezone.utc)

    first = trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="POST /v1/verify",
        now=started_at,
    )
    second = trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="POST /v1/verify",
        now=started_at + timedelta(minutes=5),
    )

    assert first is not None and second is not None
    assert second.trial_status == "active"
    assert second.trial_started_at == first.trial_started_at
    assert second.trial_ends_at == first.trial_ends_at


def test_non_activation_route_does_not_start_trial():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )

    unchanged = trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="GET /v1/organization/billing/subscription",
        now=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )

    assert unchanged is not None
    assert unchanged.trial_status == "never_started"
    assert control_plane.store.get_trial_history("123456789") is None


def test_trial_expiry_reverts_to_free_entitlements_without_blocking_access():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    entitlement_service = EntitlementService(
        subscription_loader=lambda account_id: control_plane.store.get_subscription(account_id).to_subscription(),
        trial_config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="GET /v1/nonprofit/{ein}",
        now=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )

    refreshed = trial_service.refresh_subscription(
        account_id=account["id"],
        now=datetime(2026, 4, 3, tzinfo=timezone.utc),
    )
    resolved = entitlement_service.resolve(
        account_id=account["id"],
        fallback_plan_code="free",
        subscription=refreshed.to_subscription(),
        now=datetime(2026, 4, 3, tzinfo=timezone.utc),
    )

    assert refreshed is not None
    assert refreshed.trial_status == "expired"
    assert refreshed.trial_termination_reason == "expired_to_free"
    assert resolved.subscription.plan_code == "free"
    assert resolved.entitlements.plan_code == "free"


def test_trial_converts_to_paid_cleanly():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    trial_service.maybe_activate_trial(
        account_id=account["id"],
        trigger_event="POST /v1/verify",
        now=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )
    current = control_plane.store.get_subscription(account["id"])
    control_plane.store.put_subscription(
        replace(
            current,
            plan_code="growth",
            stripe_subscription_id="sub_123",
            stripe_customer_id="cus_123",
            billing_status="active",
            updated_at="2026-03-20T00:00:00+00:00",
        )
    )

    converted = trial_service.mark_paid_conversion(
        account_id=account["id"],
        now=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    assert converted is not None
    assert converted.trial_status == "converted"
    assert converted.trial_termination_reason == "converted_to_paid"
    history = control_plane.store.get_trial_history("123456789")
    assert history is not None
    assert history.last_status == "converted"


def test_trial_cannot_be_reused_for_same_ein_on_new_account():
    control_plane = ControlPlaneService(store=InMemoryControlPlaneStore())
    first_account = control_plane.create_account({"name": "Trial Org", "ein": "123456789"})
    second_account = control_plane.create_account({"name": "Trial Org Two", "ein": "123456789"})
    trial_service = TrialLifecycleService(
        store=control_plane.store,
        config=TrialConfig(enabled=True, duration_days=14, plan_code="growth"),
    )
    trial_service.maybe_activate_trial(
        account_id=first_account["id"],
        trigger_event="GET /v1/nonprofit/{ein}",
        now=datetime(2026, 3, 19, tzinfo=timezone.utc),
    )

    second = trial_service.maybe_activate_trial(
        account_id=second_account["id"],
        trigger_event="GET /v1/nonprofit/{ein}",
        now=datetime(2026, 3, 20, tzinfo=timezone.utc),
    )

    assert second is not None
    assert second.trial_status == "ineligible"
    assert second.trial_consumed is True
    assert second.trial_termination_reason == "already_consumed"

