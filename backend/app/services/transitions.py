from collections.abc import Iterable
from enum import Enum
from typing import Any

from sqlalchemy import update
from sqlalchemy.orm import Session


def compare_and_set(
    db: Session, model: type, row_id: int, expected_statuses: Iterable[Enum], values: dict[str, Any]
) -> bool:
    """Atomically update a row only if its status is still one of `expected_statuses`.

    This is the guard against two people acting on the same record at once: the
    status check and the write happen in a single UPDATE statement, so exactly one
    of two concurrent requests can win. Returns False when the row had moved on.
    """
    result = db.execute(
        update(model)
        .where(model.id == row_id, model.status.in_(list(expected_statuses)))
        .values(**values)
        .execution_options(synchronize_session=False)
    )
    return result.rowcount == 1
