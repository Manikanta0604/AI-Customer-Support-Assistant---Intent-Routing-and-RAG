from app.intent import route_intent


def test_billing_intent():
    route = route_intent("I was charged twice and need a refund")
    assert route.intent == "billing"
    assert route.confidence > 0.7


def test_human_request_escalates():
    route = route_intent("I need to speak to a human representative")
    assert route.urgent_reason is not None


def test_general_fallback():
    assert route_intent("Hello there").intent == "general"
