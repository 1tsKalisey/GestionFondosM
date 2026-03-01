from gf_mobile.core.config import get_settings


def test_db_path_expands_user_home() -> None:
    settings = get_settings()
    db_path_str = str(settings.DB_PATH)
    assert "~" not in db_path_str
