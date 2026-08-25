import importlib
import warnings

from api.database import Base
import api.payment_admin.models as payment_models


def test_payment_admin_models_can_be_reloaded_without_metadata_collision():
    """Regression for Render startup re-importing payment admin models.

    The isolated payment route loader may encounter a second execution of the
    declarative module after an optional integration import fails. Reloading
    must not raise SQLAlchemy's duplicate-table InvalidRequestError.
    """
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        reloaded = importlib.reload(payment_models)

    assert reloaded.PaymentAudit.__table__ is Base.metadata.tables["payment_audit"]
    assert reloaded.PromoCode.__table__ is Base.metadata.tables["promo_codes"]
    assert reloaded.PromoRedemption.__table__ is Base.metadata.tables["promo_redemptions"]

    assert {"id", "method", "payment_id", "subscriber_id", "new_status"}.issubset(
        Base.metadata.tables["payment_audit"].columns.keys()
    )
    assert {"id", "code", "scope", "discount_value", "active"}.issubset(
        Base.metadata.tables["promo_codes"].columns.keys()
    )
