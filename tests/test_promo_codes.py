from pathlib import Path


def test_promo_models_are_registered_for_database_creation():
    source = Path("api/payment_admin/models.py").read_text(encoding="utf-8")
    assert "class PromoCode" in source
    assert "class PromoRedemption" in source
    assert 'UniqueConstraint("promo_code_id", "subscriber_id"' not in source


def test_promo_routes_require_admin_for_management_and_allow_reuse():
    source = Path("api/payments/routes.py").read_text(encoding="utf-8")
    assert '@promo_router.get("/admin")' in source
    assert '@promo_router.post("/admin", status_code=201)' in source
    assert "Depends(require_admin)" in source
    assert '@promo_router.post("/{subscriber_id}/quote")' in source
    assert '@promo_router.post("/{subscriber_id}/redeem")' in source
    assert "Depends(require_subscriber_or_admin)" in source
    assert "already been used by this subscriber" not in source
    assert "usage limit has been reached" in source


def test_admin_promo_page_uses_authenticated_admin_api():
    source = Path("admin-frontend/promotions.html").read_text(encoding="utf-8")
    assert "Promotion & Discount Codes" in source
    assert "bethel_access_token" not in source
    assert 'src="js/api.js' in source
    assert "PROMO_ENDPOINT" in source
    assert "restricted_email" in source
    assert "max_uses" in source
    assert "BETHELPROMO" in source
    assert "unlimited reuse" in source
