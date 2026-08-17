from mp3_processor.gui.app import _format_duration


def test_format_duration_uses_hours_minutes_and_seconds() -> None:
    assert _format_duration(0) == "00:00:00"
    assert _format_duration(65) == "00:01:05"
    assert _format_duration(60_001) == "16:40:01"
