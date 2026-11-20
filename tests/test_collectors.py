from toponux.collectors import firewall
from toponux.collectors.firewall import collect_firewall
from toponux.models.network import collect_snapshot


def _which(available):
    return lambda name: f"/usr/sbin/{name}" if name in available else None


def test_firewall_prefers_nftables(monkeypatch):
    monkeypatch.setattr(firewall.shutil, "which", _which({"nft"}))
    monkeypatch.setattr(firewall, "run_json", lambda command: [{"metainfo": {"version": "1.0"}}])

    result = collect_firewall()

    assert result["backend"] == "nftables"
    assert result["rules"] == [{"metainfo": {"version": "1.0"}}]
    assert "error" not in result


def test_firewall_falls_back_to_iptables(monkeypatch):
    monkeypatch.setattr(firewall.shutil, "which", _which({"nft", "iptables-save", "ip6tables-save"}))

    def broken_nft(command):
        raise RuntimeError("nft: permission denied")

    monkeypatch.setattr(firewall, "run_json", broken_nft)
    monkeypatch.setattr(firewall, "run_text", lambda command: f"rules from {command[0]}")

    result = collect_firewall()

    assert result["backend"] == "iptables"
    assert result["rules"] == {"ipv4": "rules from iptables-save", "ipv6": "rules from ip6tables-save"}
    assert "permission denied" in result["nft_error"]


def test_firewall_without_backend_has_no_rules_key(monkeypatch):
    monkeypatch.setattr(firewall.shutil, "which", _which(set()))

    result = collect_firewall()

    assert result["backend"] == "unavailable"
    assert "rules" not in result
    assert result["error"]
    assert result["nft_error"] == "nft not installed"


def test_firewall_reports_iptables_failure(monkeypatch):
    monkeypatch.setattr(firewall.shutil, "which", _which({"iptables-save"}))

    def denied(command):
        raise RuntimeError("iptables-save : permission denied")

    monkeypatch.setattr(firewall, "run_text", denied)

    result = collect_firewall()

    assert result["backend"] == "unavailable"
    assert "permission denied" in result["error"]
    assert "rules" not in result


def test_snapshot_isolates_failures_and_never_returns_none():
    snapshot = collect_snapshot(
        {
            "interfaces": lambda: None,
            "routes": lambda: 1 / 0,
            "firewall": lambda: {"backend": "unavailable"},
        }
    )

    assert snapshot["interfaces"] == []
    assert snapshot["routes"] == {}
    assert snapshot["firewall"] == {"backend": "unavailable"}
    assert "routes" in snapshot["errors"]
    assert snapshot["collected_at"]


def test_interfaces_collector_enriches_with_kernel_statistics(monkeypatch, tmp_path):
    from toponux.collectors import interfaces

    stats_dir = tmp_path / "eth0" / "statistics"
    stats_dir.mkdir(parents=True)
    (stats_dir / "rx_bytes").write_text("1234\n")
    (stats_dir / "tx_bytes").write_text("5678\n")
    broken_dir = tmp_path / "eth1" / "statistics"
    broken_dir.mkdir(parents=True)
    (broken_dir / "rx_bytes").write_text("not-a-number\n")

    monkeypatch.setattr(interfaces, "SYS_NET", tmp_path)
    monkeypatch.setattr(
        interfaces,
        "run_json",
        lambda command: [
            {"ifname": "eth0", "operstate": "UP"},
            {"ifname": "eth1", "operstate": "DOWN"},
            {"operstate": "UP"},
        ],
    )

    result = interfaces.collect_interfaces()

    assert result[0]["stats"]["rx_bytes"] == 1234
    assert result[0]["stats"]["tx_bytes"] == 5678
    assert result[0]["stats"]["rx_errors"] == 0
    assert result[1]["stats"]["rx_bytes"] == 0
    assert "stats" not in result[2]


def test_neighbors_collector_reads_the_kernel_neighbour_table(monkeypatch):
    from toponux.collectors import neighbors

    captured = {}

    def fake_run_json(command):
        captured["command"] = command
        return [{"dst": "192.0.2.20", "dev": "eth0", "lladdr": "aa:bb:cc:dd:ee:ff", "state": ["REACHABLE"]}]

    monkeypatch.setattr(neighbors, "run_json", fake_run_json)

    result = neighbors.collect_neighbors()

    assert captured["command"] == ["ip", "-j", "neigh", "show"]
    assert result[0]["dst"] == "192.0.2.20"
