import pytest

from social_downloader import main


def test_main_prints_greeting(capsys: pytest.CaptureFixture[str]) -> None:
    main()

    captured = capsys.readouterr()
    assert "social-downloader" in captured.out
