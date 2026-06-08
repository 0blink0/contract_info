from backend.app.validate.billing_inference import infer_subscription_billing_rules


def test_subscribe_billing_outside():
    text = "净认购金额=认购金额/(1+认购费率)"
    assert infer_subscription_billing_rules(text).get("认购费") == "价外法"


def test_purchase_billing_outside():
    text = "净申购金额=申购金额/(1+申购费率)"
    assert infer_subscription_billing_rules(text).get("申购费") == "价外法"


def test_purchase_billing_outside_variant():
    text = "申购份额=申购金额/(1+申购费率)/申购价格"
    assert infer_subscription_billing_rules(text).get("申购费") == "价外法"


def test_purchase_billing_inside():
    text = "净申购金额=申购金额×（1-申购费率）"
    assert infer_subscription_billing_rules(text).get("申购费") == "价内法"
