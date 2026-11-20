"""Normalize raw firewall output into a stable, renderable model.

The collectors return either the nftables JSON array or the iptables-save
text. Both formats are flattened here into one structure so the web layer
never has to know which backend produced the rules.

Nothing in this module modifies firewall state: it only reads the payload
already collected.
"""

from __future__ import annotations

import re
import shlex
from typing import Any

NAT_TARGETS = {"DNAT", "SNAT", "MASQUERADE", "REDIRECT", "NETMAP", "TPROXY"}
TERMINAL_VERDICTS = {"ACCEPT": "accept", "DROP": "drop", "REJECT": "reject", "RETURN": "return"}
PASSIVE_VERDICTS = {"LOG": "log"}
COUNTER_RE = re.compile(r"\[(\d+):(\d+)\]")
VERDICT_KEYS = ("rules", "accept", "drop", "reject", "return", "jump", "nat", "log", "other")

# iptables flags mapped to the same vocabulary used by the nftables parser.
IPTABLES_FLAGS = {
    "-i": "iifname",
    "--in-interface": "iifname",
    "-o": "oifname",
    "--out-interface": "oifname",
    "-s": "ip saddr",
    "--source": "ip saddr",
    "-d": "ip daddr",
    "--destination": "ip daddr",
    "-p": "proto",
    "--protocol": "proto",
    "--dport": "dport",
    "--sport": "sport",
    "--dports": "dports",
    "--sports": "sports",
    "--ctstate": "ct state",
    "--dst-type": "dst-type",
    "--src-type": "src-type",
    "--to-destination": "to-destination",
    "--to-ports": "to-ports",
    "--to-source": "to-source",
    "--reject-with": "reject-with",
    "--limit": "limit",
}


def normalize_firewall(raw: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a renderable view of the firewall payload.

    The result is always a dict with ``backend``, ``available``, ``tables``,
    ``totals`` and ``warnings``. Unknown backends yield an empty rule set
    rather than an exception, so the UI can show a clear message.
    """
    raw = raw or {}
    backend = str(raw.get("backend") or "unavailable")
    rules = raw.get("rules")
    warnings: list[str] = []

    for key in ("error", "nft_error"):
        message = raw.get(key)
        if message:
            warnings.append(str(message))

    tables: list[dict[str, Any]] = []
    if backend == "nftables":
        items: Any = rules
        if isinstance(items, dict):
            items = items.get("nftables")
        if isinstance(items, list):
            tables = _tables_from_nft(items, warnings)
        else:
            warnings.append("nftables payload has an unexpected shape")
    elif backend == "iptables" and isinstance(rules, dict):
        for family_key, text in rules.items():
            if not text:
                continue
            family = "ip6" if family_key == "ipv6" else "ip"
            tables.extend(_tables_from_iptables(str(text), family, warnings))

    totals = _finalize(tables, warnings)
    sets = [item for table in tables for item in table.get("sets", [])]
    maps = [item for table in tables for item in table.get("maps", [])]
    if backend == "nftables":
        for table in tables:
            table["command"] = f"nft -j list table {table['family']} {table['name']}"
    elif backend == "iptables":
        for table in tables:
            table["command"] = "iptables-save" if table["family"] == "ip" else "ip6tables-save"
    command = "nft -j list ruleset" if backend == "nftables" else ("iptables-save" if backend == "iptables" else None)
    analytics = _firewall_analytics(tables, backend, command)
    return {
        "backend": backend,
        "available": bool(tables) and backend in {"nftables", "iptables"},
        "tables": tables,
        "sets": sets,
        "maps": maps,
        "totals": totals,
        "analytics": analytics,
        "command": command,
        "warnings": warnings,
    }


# --------------------------------------------------------------------------
# Shared helpers
# --------------------------------------------------------------------------


def _new_table(store: dict[tuple[str, str], dict[str, Any]], family: str, name: str) -> dict[str, Any]:
    key = (family, name)
    if key not in store:
        store[key] = {"family": family, "name": name, "chains": {}, "sets": [], "maps": [], "stats": {}}
    return store[key]


def _new_chain(table: dict[str, Any], name: str) -> dict[str, Any]:
    chains = table["chains"]
    if name not in chains:
        chains[name] = {
            "name": name,
            "hook": None,
            "type": None,
            "priority": None,
            "policy": None,
            "rules": [],
            "stats": {},
        }
    return chains[name]


def _match(kind: str, text: str) -> dict[str, str]:
    return {"kind": kind, "text": text}


def _dedupe(matches: list[dict[str, str]]) -> list[dict[str, str]]:
    seen: set[str] = set()
    unique: list[dict[str, str]] = []
    for item in matches:
        if item["text"] in seen:
            continue
        seen.add(item["text"])
        unique.append(item)
    return unique


# --------------------------------------------------------------------------
# nftables
# --------------------------------------------------------------------------


def _tables_from_nft(items: list[Any], warnings: list[str]) -> list[dict[str, Any]]:
    store: dict[tuple[str, str], dict[str, Any]] = {}
    for item in items:
        if not isinstance(item, dict):
            continue
        if "table" in item:
            spec = item["table"]
            _new_table(store, str(spec.get("family", "ip")), str(spec.get("name", "?")))
        elif "chain" in item:
            spec = item["chain"]
            table = _new_table(store, str(spec.get("family", "ip")), str(spec.get("table", "?")))
            chain = _new_chain(table, str(spec.get("name", "?")))
            for source, target in (("hook", "hook"), ("type", "type"), ("prio", "priority"), ("policy", "policy")):
                if source in spec:
                    chain[target] = spec[source]
        elif "rule" in item:
            spec = item["rule"]
            table = _new_table(store, str(spec.get("family", "ip")), str(spec.get("table", "?")))
            chain = _new_chain(table, str(spec.get("chain", "?")))
            try:
                chain["rules"].append(_nft_rule(spec))
            except (TypeError, ValueError, AttributeError) as exc:
                warnings.append(f"unparsed nft rule {spec.get('handle', '?')}: {exc}")
        elif "set" in item:
            spec = item["set"]
            table = _new_table(store, str(spec.get("family", "ip")), str(spec.get("table", "?")))
            table["sets"].append(_nft_set(spec))
        elif "map" in item:
            spec = item["map"]
            table = _new_table(store, str(spec.get("family", "ip")), str(spec.get("table", "?")))
            table["maps"].append(_nft_map(spec))
    return list(store.values())


def _nft_rule(spec: dict[str, Any]) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    counter: dict[str, int] | None = None
    verdict = "other"
    target: str | None = None

    for expr in spec.get("expr") or []:
        if not isinstance(expr, dict):
            continue
        if "match" in expr:
            matches.append(_match("match", _nft_match(expr["match"])))
        elif "counter" in expr:
            data = expr["counter"] or {}
            counter = {"packets": int(data.get("packets", 0)), "bytes": int(data.get("bytes", 0))}
        elif "accept" in expr:
            verdict = "accept"
        elif "drop" in expr:
            verdict = "drop"
        elif "reject" in expr:
            verdict = "reject"
        elif "return" in expr:
            verdict = "return"
        elif "jump" in expr or "goto" in expr:
            key = "jump" if "jump" in expr else "goto"
            target = str((expr[key] or {}).get("target", "?"))
            verdict = "target"
        elif "xt" in expr:
            xt = expr["xt"] or {}
            name = str(xt.get("name", "xt"))
            if xt.get("type") == "target":
                target = name
                verdict = "target"
            else:
                matches.append(_match("module", name))
        elif any(key in expr for key in ("masquerade", "dnat", "snat", "redirect", "netmap", "tproxy")):
            for key in ("masquerade", "dnat", "snat", "redirect", "netmap", "tproxy"):
                if key in expr:
                    target = key.upper()
                    verdict = "target"
                    break
        elif "log" in expr:
            matches.append(_match("module", "log"))
        elif "limit" in expr:
            matches.append(_match("module", "limit"))
        elif "notrack" in expr:
            matches.append(_match("module", "notrack"))

    return {
        "handle": spec.get("handle"),
        "comment": spec.get("comment"),
        "verdict": verdict,
        "target": target,
        "matches": _dedupe(matches),
        "counter": counter,
    }


def _nft_set(spec: dict[str, Any]) -> dict[str, Any]:
    elements = _nft_elements(spec)
    return {
        "kind": "set",
        "family": str(spec.get("family", "ip")),
        "table": str(spec.get("table", "?")),
        "name": str(spec.get("name", "?")),
        "handle": spec.get("handle"),
        "type": spec.get("type"),
        "flags": spec.get("flags") or [],
        "elements": elements,
        "size": len(elements),
        "command": f"nft -j list set {spec.get('family', 'ip')} {spec.get('table', '?')} {spec.get('name', '?')}",
    }


def _nft_map(spec: dict[str, Any]) -> dict[str, Any]:
    elements = _nft_elements(spec)
    return {
        "kind": "map",
        "family": str(spec.get("family", "ip")),
        "table": str(spec.get("table", "?")),
        "name": str(spec.get("name", "?")),
        "handle": spec.get("handle"),
        "type": spec.get("type"),
        "map_type": spec.get("map"),
        "flags": spec.get("flags") or [],
        "elements": elements,
        "size": len(elements),
        "command": f"nft -j list map {spec.get('family', 'ip')} {spec.get('table', '?')} {spec.get('name', '?')}",
    }


def _nft_elements(spec: dict[str, Any]) -> list[Any]:
    raw = spec.get("elem")
    if raw is None:
        return []
    if not isinstance(raw, list):
        raw = [raw]
    elements: list[Any] = []
    for item in raw:
        if isinstance(item, dict) and "elem" in item:
            elem = item["elem"]
            if isinstance(elem, dict):
                if "key" in elem and "val" in elem:
                    elements.append({"key": _scalar(elem["key"]), "value": _scalar(elem["val"])})
                elif "val" in elem:
                    elements.append(_scalar(elem["val"]))
                else:
                    elements.append({key: _scalar(value) for key, value in elem.items()})
            else:
                elements.append(_scalar(elem))
        elif isinstance(item, dict):
            if "key" in item and "val" in item:
                elements.append({"key": _scalar(item["key"]), "value": _scalar(item["val"])})
            else:
                elements.append({key: _scalar(value) for key, value in item.items()})
        else:
            elements.append(_scalar(item))
    return elements


def _scalar(value: Any) -> str:
    if isinstance(value, dict):
        if "prefix" in value:
            prefix = value["prefix"] or {}
            return f"{_scalar(prefix.get('addr', '?'))}/{prefix.get('len', '?')}"
        if "range" in value:
            bounds = value["range"] or []
            if len(bounds) >= 2:
                return f"{_scalar(bounds[0])}-{_scalar(bounds[-1])}"
            return ", ".join(_scalar(item) for item in bounds)
        if "set" in value:
            return ", ".join(_scalar(item) for item in value["set"] or [])
        if "quoted" in value:
            return str(value["quoted"])
        if "proto" in value:
            return str(value["proto"])
        return " ".join(f"{key} {_scalar(item)}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(_scalar(item) for item in value)
    if value is True:
        return ""
    return str(value)


def _nft_match(spec: dict[str, Any]) -> str:
    if not isinstance(spec, dict):
        return str(spec)
    left = _nft_left(spec.get("left"))
    right = _nft_right(spec.get("right"))
    op = spec.get("op", "==")
    if left and right:
        return f"{left} {right}" if op == "==" else f"{left} {op} {right}"
    return left or right or "match"


def _nft_left(desc: Any) -> str:
    if not isinstance(desc, dict):
        return str(desc)
    if "meta" in desc:
        return str((desc["meta"] or {}).get("key", "meta"))
    if "payload" in desc:
        payload = desc["payload"] or {}
        return " ".join(part for part in (payload.get("protocol"), payload.get("field")) if part) or "payload"
    if "ct" in desc:
        return f"ct {(desc['ct'] or {}).get('key', '')}".strip()
    if "cmp" in desc:
        cmp = desc["cmp"] or {}
        left = _nft_left(cmp.get("left"))
        right = _nft_right(cmp.get("right"))
        op = cmp.get("op", "==")
        return f"{left} {op} {right}".strip()
    if "fib" in desc:
        fib = desc["fib"] or {}
        return f"fib {fib.get('key', '')}".strip()
    if "exthdr" in desc:
        return "exthdr"
    return "match"


def _nft_right(value: Any) -> str:
    if isinstance(value, dict):
        if "prefix" in value:
            prefix = value["prefix"] or {}
            return f"{prefix.get('addr', '?')}/{prefix.get('len', '?')}"
        if "range" in value:
            bounds = value["range"] or []
            if len(bounds) >= 2:
                return f"{_nft_right(bounds[0])}-{_nft_right(bounds[-1])}"
            return ", ".join(_nft_right(item) for item in bounds)
        if "set" in value:
            return ", ".join(_nft_right(item) for item in value["set"] or [])
        if "proto" in value:
            return str(value["proto"])
        if "quoted" in value:
            return str(value["quoted"])
        return " ".join(f"{key} {_nft_right(item)}" for key, item in value.items())
    if isinstance(value, list):
        return ", ".join(_nft_right(item) for item in value)
    if value is True:
        return ""
    return str(value)


# --------------------------------------------------------------------------
# iptables / ip6tables
# --------------------------------------------------------------------------


def _tables_from_iptables(text: str, family: str, warnings: list[str]) -> list[dict[str, Any]]:
    tables: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("*"):
            current = {"family": family, "name": line[1:].strip(), "chains": {}, "stats": {}}
            tables.append(current)
            continue
        if line == "COMMIT":
            current = None
            continue
        if current is None:
            continue
        if line.startswith(":"):
            name, _, rest = line[1:].partition(" ")
            policy, _, _ = rest.partition(" ")
            chain = _new_chain(current, name)
            if policy and policy != "-":
                chain["policy"] = policy.lower()
            counter = COUNTER_RE.search(rest)
            if counter:
                chain["policy_counter"] = {
                    "packets": int(counter.group(1)),
                    "bytes": int(counter.group(2)),
                }
            continue
        if line.startswith("-A "):
            try:
                args = shlex.split(line)
            except ValueError as exc:
                warnings.append(f"unparsed iptables rule: {exc}")
                continue
            if len(args) < 3:
                continue
            chain = _new_chain(current, args[1])
            chain["rules"].append(_iptables_rule(args[2:]))
    return tables


def _iptables_rule(args: list[str]) -> dict[str, Any]:
    matches: list[dict[str, str]] = []
    target: str | None = None
    comment: str | None = None
    negate = False
    index = 0
    while index < len(args):
        token = args[index]
        if token == "!":
            negate = True
            index += 1
            continue
        if token in ("-j", "--jump", "-g", "--goto"):
            if index + 1 < len(args):
                target = args[index + 1]
            index += 2
            negate = False
            continue
        if token in ("-m", "--match"):
            if index + 1 < len(args) and args[index + 1] not in {"comment", "tcp", "udp", "sctp", "icmp", "icmp6"}:
                matches.append(_match("module", args[index + 1]))
            index += 2
            negate = False
            continue
        if token == "--comment":
            if index + 1 < len(args):
                comment = args[index + 1]
            index += 2
            negate = False
            continue
        label = IPTABLES_FLAGS.get(token)
        if label and index + 1 < len(args):
            value = args[index + 1]
            prefix = "! " if negate else ""
            matches.append(_match("match", f"{prefix}{label} {value}"))
            index += 2
            negate = False
            continue
        # Unknown flag with a value: keep it visible instead of dropping it.
        if token.startswith("-") and index + 1 < len(args) and not args[index + 1].startswith("-"):
            matches.append(_match("match", f"{token} {args[index + 1]}"))
            index += 2
            negate = False
            continue
        index += 1
        negate = False

    return {
        "handle": None,
        "comment": comment,
        "verdict": "target" if target else "other",
        "target": target,
        "matches": _dedupe(matches),
        "counter": None,
    }


# --------------------------------------------------------------------------
# Final pass: verdict classification and counters
# --------------------------------------------------------------------------


def _finalize(tables: list[dict[str, Any]], warnings: list[str]) -> dict[str, int]:
    totals = dict.fromkeys(VERDICT_KEYS, 0)
    for table in tables:
        chains = list(table["chains"].values())
        chain_names = {chain["name"] for chain in chains}
        for chain in chains:
            _classify_rules(chain, chain_names, warnings)
            counts = dict.fromkeys(VERDICT_KEYS, 0)
            packets = 0
            bytes_total = 0
            for rule in chain["rules"]:
                counts["rules"] += 1
                counts[rule["verdict"]] = counts.get(rule["verdict"], 0) + 1
                counter = rule.get("counter")
                if counter:
                    packets += counter["packets"]
                    bytes_total += counter["bytes"]
            chain["stats"] = {
                "rules": counts["rules"],
                "by_verdict": {key: value for key, value in counts.items() if key != "rules" and value},
                "packets": packets,
                "bytes": bytes_total,
            }
            for key, value in counts.items():
                totals[key] = totals.get(key, 0) + value
        table_counts = dict.fromkeys(VERDICT_KEYS, 0)
        for chain in chains:
            for key, value in chain["stats"]["by_verdict"].items():
                table_counts[key] = table_counts.get(key, 0) + value
        table["chains"] = chains
        table["stats"] = {
            "rules": table_counts["rules"],
            "chains": len(chains),
            "by_verdict": {key: value for key, value in table_counts.items() if key != "rules" and value},
        }
    return totals


def _firewall_analytics(tables: list[dict[str, Any]], backend: str, command: str | None) -> dict[str, Any]:
    zero_counter_rules: list[dict[str, Any]] = []
    uncounted_rules: list[dict[str, Any]] = []
    uncommented_rules: list[dict[str, Any]] = []

    for table in tables:
        for chain in table["chains"]:
            for rule in chain["rules"]:
                counter = rule.get("counter")
                location = {
                    "table": table["name"],
                    "family": table["family"],
                    "chain": chain["name"],
                    "handle": rule.get("handle"),
                    "verdict": rule.get("verdict"),
                    "target": rule.get("target"),
                    "matches": [match.get("text") for match in rule.get("matches", []) if match.get("text")],
                    "comment": rule.get("comment"),
                    "counter": counter,
                    "command": table.get("command"),
                }
                if isinstance(counter, dict) and counter.get("packets", 0) == 0 and counter.get("bytes", 0) == 0:
                    zero_counter_rules.append(location)
                if counter is None:
                    uncounted_rules.append(location)
                if not rule.get("comment"):
                    uncommented_rules.append(location)

    return {
        "backend": backend,
        "command": command,
        "zero_counter_rules": zero_counter_rules,
        "uncounted_rules": uncounted_rules,
        "uncommented_rules": uncommented_rules,
        "counts": {
            "zero_counter": len(zero_counter_rules),
            "uncounted": len(uncounted_rules),
            "uncommented": len(uncommented_rules),
            "sets": sum(len(table.get("sets", [])) for table in tables),
            "maps": sum(len(table.get("maps", [])) for table in tables),
        },
    }


def _classify_rules(chain: dict[str, Any], chain_names: set[str], warnings: list[str]) -> None:
    for rule in chain["rules"]:
        target = rule.get("target")
        if rule["verdict"] != "target":
            continue
        name = str(target or "")
        upper = name.upper()
        if upper in TERMINAL_VERDICTS:
            rule["verdict"] = TERMINAL_VERDICTS[upper]
            rule["target"] = None
        elif upper in PASSIVE_VERDICTS:
            rule["verdict"] = PASSIVE_VERDICTS[upper]
            rule["target"] = None
        elif upper in NAT_TARGETS:
            rule["verdict"] = "nat"
            rule["target"] = upper
        elif name in chain_names:
            rule["verdict"] = "jump"
        else:
            lowered = {existing.lower(): existing for existing in chain_names}
            if name.lower() in lowered:
                rule["verdict"] = "jump"
                rule["target"] = lowered[name.lower()]
            else:
                rule["verdict"] = "other"
                warnings.append(f"unknown jump target in {chain['name']}: {name or '?'}")
