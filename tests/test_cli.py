"""Tests for the command-line interface."""

from app.cli import main


def test_cli_convert_document(tmp_path):
    inp = tmp_path / "a.md"
    inp.write_text("# Hi\n\nHello", encoding="utf-8")
    out = tmp_path / "a.html"
    assert main([str(inp), str(out)]) == 0
    assert "<h1>Hi</h1>" in out.read_text(encoding="utf-8")


def test_cli_convert_data(tmp_path):
    inp = tmp_path / "d.json"
    inp.write_text('{"name": "Kiro"}', encoding="utf-8")
    out = tmp_path / "d.yaml"
    assert main([str(inp), str(out)]) == 0
    assert "name: Kiro" in out.read_text(encoding="utf-8")


def test_cli_target_override(tmp_path):
    inp = tmp_path / "note.md"
    inp.write_text("# Title", encoding="utf-8")
    out = tmp_path / "out.bin"
    assert main([str(inp), str(out), "--to", "html"]) == 0
    assert "<h1>Title</h1>" in out.read_text(encoding="utf-8")


def test_cli_merge(tmp_path):
    a = tmp_path / "a.md"
    a.write_text("# A", encoding="utf-8")
    b = tmp_path / "b.md"
    b.write_text("# B", encoding="utf-8")
    out = tmp_path / "merged.html"
    assert main([str(a), str(b), str(out)]) == 0
    text = out.read_text(encoding="utf-8")
    assert "A" in text and "B" in text


def test_cli_toc_option(tmp_path):
    inp = tmp_path / "a.md"
    inp.write_text("# One\n\n## Two", encoding="utf-8")
    out = tmp_path / "a.html"
    assert main([str(inp), str(out), "--toc"]) == 0
    assert 'class="toc"' in out.read_text(encoding="utf-8")


def test_cli_missing_output_arg():
    assert main(["only-one-path"]) == 2


def test_cli_nonexistent_input(tmp_path):
    out = tmp_path / "out.html"
    assert main([str(tmp_path / "missing.md"), str(out)]) == 1


def test_cli_invalid_conversion(tmp_path):
    inp = tmp_path / "a.md"
    inp.write_text("# Hi", encoding="utf-8")
    out = tmp_path / "a.json"  # document -> data has no bridge
    assert main([str(inp), str(out)]) == 1
