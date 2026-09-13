from pathlib import Path


def test_typo_correction_preserves_trailing_spaces_in_pico_parser():
    source = Path("ams-shell/src/Ams.UI/Services/AutoCycleFirmwareBundle.cs").read_text(encoding="utf-8")
    assert "PreserveKtextWhitespace" in source
    assert 'raw.decode(\"utf-8\", \"replace\").rstrip(\"\\\\r\")' in source
    assert '.decode(\"utf-8\", \"replace\").strip()' not in source

    # A typo correction flushes a word chunk before the slip and sends the
    # separator as the final KTEXT character. Only CR may be removed; the
    # literal space must survive framing and reach HID.
    framed = b"KTEXT|80,220,how \\r\n"
    payload = framed.split(b"\\n", 1)[0].decode("utf-8").rstrip("\\r")
    assert payload.endswith("how ")
