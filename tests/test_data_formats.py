"""Extra tests for the data-family converters and their edge cases."""

import json

import pytest

from app.converters import ConversionError, convert


def test_xml_nested_and_repeated_round_trip():
    src = json.dumps({"root": {"item": ["x", "y"], "meta": {"k": "v"}}}).encode()
    xml = convert(src, "json", "xml")
    assert b"<root>" in xml
    back = json.loads(convert(xml, "xml", "json"))
    assert back == {"root": {"item": ["x", "y"], "meta": {"k": "v"}}}


def test_xml_list_at_root_wraps_in_root_element():
    src = json.dumps([1, 2, 3]).encode()
    xml = convert(src, "json", "xml").decode()
    assert "<root>" in xml
    assert "<item>" in xml


def test_xml_sanitizes_numeric_tag_names():
    src = json.dumps({"1bad": {"x": "y"}}).encode()
    xml = convert(src, "json", "xml").decode()
    # A tag cannot start with a digit; it is prefixed with an underscore.
    assert "<_1bad>" in xml


def test_csv_with_varying_keys():
    src = json.dumps([{"a": 1}, {"a": 2, "b": 3}]).encode()
    out = convert(src, "json", "csv").decode()
    assert "a,b" in out
    assert "1," in out


def test_csv_scalar_nested_value_is_json_encoded():
    src = json.dumps([{"a": {"nested": 1}}]).encode()
    out = convert(src, "json", "csv").decode()
    assert "nested" in out


def test_dict_with_single_list_value_becomes_rows():
    src = json.dumps({"rows": [{"a": 1}, {"a": 2}]}).encode()
    out = convert(src, "json", "csv").decode()
    assert out.splitlines()[0] == "a"


def test_toml_null_value_raises():
    src = json.dumps({"a": None}).encode()
    with pytest.raises(ConversionError):
        convert(src, "json", "toml")


def test_invalid_json_raises():
    with pytest.raises(ConversionError):
        convert(b"{not valid json", "json", "yaml")


def test_invalid_yaml_raises():
    with pytest.raises(ConversionError):
        convert(b"key: : : broken\n  - x\n bad", "yaml", "json")


def test_invalid_xml_raises():
    with pytest.raises(ConversionError):
        convert(b"<unclosed>", "xml", "json")


def test_empty_list_to_xlsx_and_back():
    xlsx = convert(b"[]", "json", "xlsx")
    assert xlsx[:2] == b"PK"
    assert json.loads(convert(xlsx, "xlsx", "json")) == []


def test_empty_list_to_ods_and_back():
    ods = convert(b"[]", "json", "ods")
    assert ods[:2] == b"PK"
    assert json.loads(convert(ods, "ods", "json")) == []


def test_yaml_to_toml_table():
    src = b"title: Demo\nowner:\n  name: Kiro\n"
    out = convert(src, "yaml", "toml").decode()
    assert 'title = "Demo"' in out
    assert "[owner]" in out
