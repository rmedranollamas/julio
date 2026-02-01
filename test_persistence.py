from persistence import Persistence
import os

def test_persistence():
    db_path = "test_agent.db"
    if os.path.exists(db_path):
        os.remove(db_path)

    p = Persistence(db_path)

    # Test history
    p.add_history("chat1", "user1", "user", "Hello")
    p.add_history("chat1", "user1", "assistant", "Hi there")

    history = p.get_history("chat1", "user1")
    print(f"History: {history}")
    assert len(history) == 2
    assert history[0]["role"] == "user"

    # Test state
    p.set_state("last_heartbeat", "2023-01-01")
    state = p.get_state("last_heartbeat")
    print(f"State: {state}")
    assert state == "2023-01-01"

    print("Persistence test PASSED")
    os.remove(db_path)

if __name__ == "__main__":
    test_persistence()
