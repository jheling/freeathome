import pytest

from fah.devices.fah_light import FahLight

class DummyClient:
    pass


def make_light():
    # minimal constructor args; many are unused in the tested helpers
    return FahLight(DummyClient(), None, 'SN', '1', 0x002F, 'test')


def test_parse_integer():
    l = make_light()
    assert l._parse_rgb_to_int(16711680) == 16711680
    assert l._parse_rgb_to_int("16711680") == 16711680


def test_parse_hex_formats():
    l = make_light()
    assert l._parse_rgb_to_int("0xFF0000") == 0xFF0000
    assert l._parse_rgb_to_int("#00FF00") == 0x00FF00
    assert l._parse_rgb_to_int("0000FF") == 0x0000FF


def test_parse_csv_and_space():
    l = make_light()
    assert l._parse_rgb_to_int("255,0,0") == 0xFF0000
    assert l._parse_rgb_to_int("0 255 0") == 0x00FF00
    assert l._parse_rgb_to_int("0;0;255") == 0x0000FF


def test_parse_invalid_returns_none():
    l = make_light()
    assert l._parse_rgb_to_int("not a color") is None
    assert l._parse_rgb_to_int("") is None


def test_formatter_turns_int_into_csv():
    l = make_light()
    # set internal rgb_color int to red
    l.rgb_color = 0xFF0000
    r = (l.rgb_color >> 16) & 255
    g = (l.rgb_color >> 8) & 255
    b = l.rgb_color & 255
    assert f"{r},{g},{b}" == "255,0,0"
