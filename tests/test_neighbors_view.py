from toponux.analyzers import neighbors


def _reset_oui_cache():
    neighbors._oui_cache = None


def test_normalize_neighbors_groups_entries_and_filters_lo_veth():
    entries = [
        {"dst": "192.0.2.20", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["REACHABLE"]},
        {"dst": "fe80::1", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["STALE"]},
        {"dst": "192.0.2.30", "dev": "lo", "lladdr": "11:22:33:44:55:66", "state": ["REACHABLE"]},
        {"dst": "192.0.2.31", "dev": "veth123", "lladdr": "22:33:44:55:66:77", "state": ["REACHABLE"]},
        {"dst": "192.0.2.32", "dev": "eth0", "state": ["FAILED"]},
    ]

    result = neighbors.normalize_neighbors(entries)

    assert len(result) == 1
    row = result[0]
    assert row["interface"] == "eth0"
    assert row["mac"] == "aa:bb:cc:dd:ee:ff"
    assert row["addresses"] == ["192.0.2.20", "fe80::1"]
    assert row["ipv4"] == ["192.0.2.20"]
    assert row["ipv6"] == ["fe80::1"]
    assert row["state"] == "REACHABLE, STALE"
    assert row["oui"] == "AA:BB:CC"


def test_normalize_neighbors_marks_docker_interfaces():
    entries = [
        {"dst": "172.17.0.2", "dev": "docker0", "lladdr": "00:00:5e:00:53:02", "state": ["STALE"]},
    ]

    result = neighbors.normalize_neighbors(entries)

    assert result[0]["docker"] is True


def test_lookup_vendor_reads_oui_file(monkeypatch, tmp_path):
    _reset_oui_cache()
    oui = tmp_path / "oui.txt"
    oui.write_text("00-11-22   (hex)\t\tAcme Devices\n112233  Vendor Two\n", encoding="utf-8")
    monkeypatch.setattr(neighbors, "_OUI_PATHS", (oui,))

    assert neighbors.lookup_vendor("00:11:22:33:44:55") == "Acme Devices"

    _reset_oui_cache()


def test_lookup_vendor_handles_locally_administered_addresses(monkeypatch):
    _reset_oui_cache()
    monkeypatch.setattr(neighbors, "_OUI_PATHS", ())

    assert neighbors.lookup_vendor("02:11:22:33:44:55") == "Locally administered"

    _reset_oui_cache()


def test_lookup_vendor_returns_none_without_database(monkeypatch):
    _reset_oui_cache()
    monkeypatch.setattr(neighbors, "_OUI_PATHS", ())

    assert neighbors.lookup_vendor("00:11:22:33:44:55") is None

    _reset_oui_cache()
