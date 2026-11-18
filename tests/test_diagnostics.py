import pytest

from toponux.collectors.diagnostics import validate_target


@pytest.mark.parametrize(
    "target",
    ["192.0.2.10", "2001:db8::1", "example.org", "host-1.lab.local", "a", "example.org."],
)
def test_validate_target_accepts_ip_and_dns(target):
    assert validate_target(f"  {target}  ") == target


@pytest.mark.parametrize(
    "target",
    ["", "   ", "-rf", "--help", "a b", "foo..bar", "a/b", "a;b", "a$(id)", "x" * 254],
)
def test_validate_target_rejects_unsafe_input(target):
    with pytest.raises(ValueError):
        validate_target(target)
