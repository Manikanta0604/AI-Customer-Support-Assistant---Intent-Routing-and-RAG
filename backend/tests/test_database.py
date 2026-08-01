from app.database import Database


def test_memory_and_escalation(tmp_path):
    db = Database(str(tmp_path / "support.db"))
    session = db.ensure_session(None)
    db.add_message(session, "user", "Help with my account", "account")
    assert db.history(session)[0].content == "Help with my account"
    case_id = db.escalate(session, "Customer asked for a human", "Help")
    assert db.escalations()[0].id == case_id
