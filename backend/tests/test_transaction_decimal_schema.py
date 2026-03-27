from datetime import datetime
from decimal import Decimal

import pytest

from schemas import TransactionCreate, TransactionType, TransactionUpdate


def test_transaction_create_quantizes_amount_round_half_up():
    tx = TransactionCreate(
        type=TransactionType.EXPENSE,
        description="Coffee",
        amount="10.235",
        category="Food",
        date=datetime(2026, 3, 24, 10, 0, 0),
    )

    assert tx.amount == Decimal("10.24")


def test_transaction_create_rejects_non_positive_amount():
    with pytest.raises(ValueError):
        TransactionCreate(
            type=TransactionType.EXPENSE,
            description="Invalid",
            amount="0",
            category="Food",
            date=datetime(2026, 3, 24, 10, 0, 0),
        )


def test_transaction_update_quantizes_when_amount_present():
    tx_update = TransactionUpdate(amount="15.994")
    assert tx_update.amount == Decimal("15.99")
