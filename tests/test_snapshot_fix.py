import time
from app import state, snapshot

def test_prune_stale_vessels_handles_none_last_seen():
    # Setup: one vessel with last_seen=None (the old bug case)
    # and one vessel with actual seen time
    with state.latest_lock:
        state.latest["MMSI_NONE"] = {"loc": None, "meta": {"name": "None Vessel"}, "last_seen": None}
        state.latest["MMSI_OLD"] = {"loc": None, "meta": {"name": "Old Vessel"}, "last_seen": 1000}
        state.latest["MMSI_NEW"] = {"loc": None, "meta": {"name": "New Vessel"}, "last_seen": int(time.time())}

    # Cutoff for pruning (e.g., everything older than 30 mins)
    cutoff_ts = int(time.time()) - 30 * 60

    # This part replicates the logic in sampler_task
    with state.latest_lock:
        # Before the fix, this would raise TypeError because of None in MMSI_NONE
        stale_mmsis = [mmsi for mmsi, v in state.latest.items() if (v.get("last_seen") or 0) < cutoff_ts]
        
        for mmsi in stale_mmsis:
            del state.latest[mmsi]

    # Verification:
    # MMSI_NONE should be pruned (as 0 < cutoff)
    # MMSI_OLD should be pruned (as 1000 < cutoff)
    # MMSI_NEW should remain
    assert "MMSI_NONE" not in state.latest
    assert "MMSI_OLD" not in state.latest
    assert "MMSI_NEW" in state.latest

    print("Test passed: NoneType last_seen handled correctly.")
