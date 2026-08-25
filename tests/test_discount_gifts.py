import pytest

import app


def test_discounted_threshold_uses_post_discount_subtotal():
    assert app.get_sale_gift_tier(150, 15) == 'MT2'
    assert app.get_sale_gift_tier(200, 15) == 'GHK-CU'
    assert app.get_sale_gift_tier(177, 15) == 'MT2'
    assert app.get_sale_gift_tier(149, 15) is None
    assert app.get_sale_gift_tier(235.29, 15) == 'GHK-CU'
    assert app.get_sale_gift_tier(210, 10) == 'GHK-CU'


def test_free_gift_variant_detection_handles_hyphenated_gift_options():
    assert app._extract_variant_name('Pen - Free bank holiday gift') == 'Pen'
    assert app._extract_variant_name('Nasal - Free bank holiday gift') == 'Nasal'
    assert app._extract_variant_name('Pen — £45') == 'Pen'
    assert app._extract_variant_name('Nasal — £35 (20mg total, +£15 extra)') == 'Nasal'
