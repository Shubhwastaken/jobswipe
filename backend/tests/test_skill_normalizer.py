from app.services.skill_normalizer import normalize_skill, normalize_skill_set


def test_alias_js_equals_javascript():
    assert normalize_skill("js") == "javascript"
    assert normalize_skill("js") == normalize_skill("javascript")


def test_alias_is_case_insensitive():
    assert normalize_skill("JS") == "javascript"
    assert normalize_skill("  Js ") == "javascript"


def test_postgres_and_postgresql_unify():
    assert normalize_skill("postgres") == "postgresql"
    assert normalize_skill("postgres") == normalize_skill("postgresql")


def test_unknown_skill_passes_through():
    assert normalize_skill("Rust") == "rust"
    assert "rust" in normalize_skill_set(["Rust"])


def test_normalize_skill_set_deduplicates():
    # "js" -> "javascript" collides with "JavaScript" after normalization
    result = normalize_skill_set(["js", "JavaScript", "PY", "python", ""])
    assert result == {"javascript", "python"}
