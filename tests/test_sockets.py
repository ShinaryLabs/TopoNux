from toponux.analyzers.sockets import normalize_sockets
from toponux.collectors import sockets


def test_collect_sockets_parses_ss_output(monkeypatch):
    captured = {}
    output = (
        "tcp LISTEN 0 4096 127.0.0.1:8080 0.0.0.0:* "
        'users:(("python",pid=123,fd=3))'
        "\n"
        "udp ESTAB 0 0 192.0.2.10%eth0:68 192.0.2.1:67 "
    )

    def fake_run_text(command):
        captured["command"] = command
        return output

    monkeypatch.setattr(sockets, "run_text", fake_run_text)

    records = sockets.collect_sockets()

    assert captured["command"] == ["ss", "-H", "-t", "-u", "-a", "-n", "-p"]
    assert records == [
        {
            "netid": "tcp",
            "state": "LISTEN",
            "local": "127.0.0.1:8080",
            "peer": "0.0.0.0:*",
            "processes": [{"name": "python", "pid": 123}],
        },
        {
            "netid": "udp",
            "state": "ESTAB",
            "local": "192.0.2.10%eth0:68",
            "peer": "192.0.2.1:67",
            "processes": [],
        },
    ]


def test_normalize_sockets_separates_listeners_and_remote_connections():
    entries = [
        {
            "netid": "tcp",
            "state": "LISTEN",
            "local": "0.0.0.0:22",
            "peer": "0.0.0.0:*",
            "processes": [{"name": "sshd", "pid": 10}],
        },
        {
            "netid": "udp",
            "state": "UNCONN",
            "local": "127.0.0.53:53",
            "peer": "0.0.0.0:*",
            "processes": [{"name": "systemd-resolve", "pid": 11}],
        },
        {
            "netid": "tcp",
            "state": "ESTAB",
            "local": "192.0.2.10:50000",
            "peer": "203.0.113.5:443",
            "processes": [{"name": "curl", "pid": 20}],
        },
        {
            "netid": "tcp",
            "state": "ESTAB",
            "local": "127.0.0.1:50001",
            "peer": "127.0.0.1:8080",
            "processes": [],
        },
        {
            "netid": "tcp",
            "state": "ESTAB",
            "local": "192.0.2.10:50002",
            "peer": "192.0.2.10:22",
            "processes": [],
        },
        {
            "netid": "tcp",
            "state": "TIME-WAIT",
            "local": "192.0.2.10:50003",
            "peer": "203.0.113.6:443",
            "processes": [],
        },
        {
            "netid": "tcp",
            "state": "ESTAB",
            "local": "[2001:db8::10]:50004",
            "peer": "[2001:db8::20]:443",
            "processes": [],
        },
    ]
    interfaces = [{"addr_info": [{"local": "192.0.2.10"}]}]

    view = normalize_sockets(entries, interfaces)

    assert view["available"] is True
    assert [item["local_port"] for item in view["listeners"]] == [22, 53]
    assert [item["peer_address"] for item in view["connections"]] == ["2001:db8::20", "203.0.113.5"]
    assert view["connections"][1]["processes"] == [{"name": "curl", "pid": 20}]


def test_normalize_sockets_reports_collection_error():
    view = normalize_sockets([], [], "Command not found: ss")

    assert view == {
        "available": False,
        "error": "Command not found: ss",
        "listeners": [],
        "connections": [],
    }
