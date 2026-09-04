"""application serviceが所有するtransaction境界の共通処理。"""

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.services.errors import DataIntegrityError


@contextmanager
def transaction(
    db: Session,
    *,
    integrity_detail: str = "データベースの整合性制約に違反しました。",
) -> Iterator[None]:
    """service use caseを1 transactionとしてcommit/rollbackする。

    CRUDは制約検出や生成値反映のため ``flush()`` できるが、transactionは確定しない。
    context正常終了時にこのhelperがSessionをcommitし、途中例外ではflush済み変更を含めて
    rollbackする。DB ``IntegrityError`` はadapterへ直接漏らさず
    :class:`DataIntegrityError` に正規化する。

    このhelperは渡されたSession全体のtransactionを所有する。callerは別use caseの未確定変更を
    同じSessionへ混在させないこと。そうしたpending stateもcommit/rollback対象になるため、
    service boundaryごとに1つのtransaction ownershipを維持する。
    """
    try:
        yield
        db.commit()
    except IntegrityError as exc:
        # application側の事前チェックを並行writeがすり抜けても、DB制約違反は
        # application errorへ正規化し、raw DB例外をHTTP境界へ漏らさない。
        db.rollback()
        raise DataIntegrityError(integrity_detail) from exc
    except Exception:
        # use case途中の失敗では、それ以前にflushした変更も同じtransactionで戻す。
        db.rollback()
        raise
