from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from auth import get_current_active_user, require_write_access
from database import get_db
from main import app
from models import Base, LedgerEntry, LedgerEntryType, User


@pytest.fixture()
def api_client_and_db_sessionmaker():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        db.add(
            User(
                id=1,
                email="test@example.com",
                username="test-user",
                hashed_password="not-used",
                role="user",
                is_active=True,
            )
        )
        db.commit()

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
        finally:
            db.close()

    def override_require_write_access():
        return SimpleNamespace(id=1, username="test-user")

    def override_get_current_active_user():
        return SimpleNamespace(id=1, username="test-user")

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[require_write_access] = override_require_write_access
    app.dependency_overrides[get_current_active_user] = override_get_current_active_user

    with TestClient(app) as client:
        yield client, SessionLocal

    app.dependency_overrides.clear()


def test_create_transaction_posts_balanced_ledger_and_is_idempotent(api_client_and_db_sessionmaker):
    client, SessionLocal = api_client_and_db_sessionmaker

    payload = {
        "type": "expense",
        "description": "Lunch",
        "amount": 125.50,
        "category": "Food",
        "date": "2026-03-24T12:00:00",
        "notes": "team lunch",
        "recurring": False,
        "spread_over_year": False,
    }

    response = client.post(
        "/api/transactions",
        json=payload,
        headers={"X-Idempotency-Key": "txn-create-001"},
    )
    assert response.status_code == 200
    created = response.json()
    transaction_id = created["id"]

    with SessionLocal() as db:
        entries = (
            db.query(LedgerEntry)
            .filter(LedgerEntry.transaction_id == transaction_id)
            .order_by(LedgerEntry.id.asc())
            .all()
        )
        assert len(entries) == 2

        debit_entries = [e for e in entries if e.entry_type == LedgerEntryType.DEBIT]
        credit_entries = [e for e in entries if e.entry_type == LedgerEntryType.CREDIT]
        assert len(debit_entries) == 1
        assert len(credit_entries) == 1
        assert debit_entries[0].amount == credit_entries[0].amount

    replay = client.post(
        "/api/transactions",
        json=payload,
        headers={"X-Idempotency-Key": "txn-create-001"},
    )
    assert replay.status_code == 200
    replay_json = replay.json()
    assert replay_json["id"] == transaction_id

    with SessionLocal() as db:
        count_after_replay = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == transaction_id).count()
        assert count_after_replay == 2


def test_reversal_creates_compensating_transaction_and_prevents_duplicates(api_client_and_db_sessionmaker):
    client, SessionLocal = api_client_and_db_sessionmaker

    create_payload = {
        "type": "income",
        "description": "Salary",
        "amount": 1000.00,
        "category": "Salary",
        "date": "2026-03-24T09:00:00",
        "notes": "monthly salary",
        "recurring": False,
        "spread_over_year": False,
    }

    create_resp = client.post(
        "/api/transactions",
        json=create_payload,
        headers={"X-Idempotency-Key": "txn-create-002"},
    )
    assert create_resp.status_code == 200
    original = create_resp.json()

    reverse_resp = client.post(
        f"/api/transactions/{original['id']}/reverse",
        json={"reason": "posted to wrong month"},
        headers={"X-Idempotency-Key": "txn-reversal-001"},
    )
    assert reverse_resp.status_code == 200
    reversal = reverse_resp.json()
    assert reversal["type"] == "expense"

    with SessionLocal() as db:
        reversal_entries = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == reversal["id"]).all()
        assert len(reversal_entries) == 2
        debit_total = sum(e.amount for e in reversal_entries if e.entry_type == LedgerEntryType.DEBIT)
        credit_total = sum(e.amount for e in reversal_entries if e.entry_type == LedgerEntryType.CREDIT)
        assert debit_total == credit_total

    duplicate_prevent_resp = client.post(
        f"/api/transactions/{original['id']}/reverse",
        json={"reason": "try duplicate reversal"},
        headers={"X-Idempotency-Key": "txn-reversal-002"},
    )
    assert duplicate_prevent_resp.status_code == 200
    duplicate_json = duplicate_prevent_resp.json()
    assert duplicate_json["id"] == reversal["id"]

    with SessionLocal() as db:
        total_for_reversal_tx = db.query(LedgerEntry).filter(LedgerEntry.transaction_id == reversal["id"]).count()
        assert total_for_reversal_tx == 2


def test_ledger_endpoint_returns_entries_for_transaction_filter(api_client_and_db_sessionmaker):
    client, SessionLocal = api_client_and_db_sessionmaker

    create_payload = {
        "type": "expense",
        "description": "Books",
        "amount": 250.00,
        "category": "Education",
        "date": "2026-03-24T14:00:00",
        "notes": "training books",
        "recurring": False,
        "spread_over_year": False,
    }

    create_resp = client.post(
        "/api/transactions",
        json=create_payload,
        headers={"X-Idempotency-Key": "txn-create-003"},
    )
    assert create_resp.status_code == 200
    transaction_id = create_resp.json()["id"]

    ledger_resp = client.get(f"/api/ledger?transaction_id={transaction_id}")
    assert ledger_resp.status_code == 200
    rows = ledger_resp.json()
    assert len(rows) == 2
    assert all(r["transaction_id"] == transaction_id for r in rows)
