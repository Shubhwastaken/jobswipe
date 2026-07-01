from app.services.talentforge_matcher import _overlap_score


def test_single_token_alias_unifies():
    # "js" student vs "javascript" job -> full required overlap (0.7 weight)
    assert _overlap_score(["js"], ["javascript"], []) == 1.0


def test_multiword_alias_target_unifies():
    # "ml" -> "machine learning" must match a job listing "machine learning"
    assert _overlap_score(["ml"], ["machine learning"], []) == 1.0
    # and the reverse direction
    assert _overlap_score(["machine learning"], ["ml"], []) == 1.0


def test_deep_learning_alias_unifies():
    assert _overlap_score(["dl"], ["deep learning"], []) == 1.0


def test_alias_inside_multiskill_string():
    # aliases embedded in a comma-joined skill string still normalize
    assert _overlap_score(["React, JS"], ["javascript"], []) == 1.0


def test_unrelated_skills_do_not_overlap():
    # non-empty required AND preferred, neither matching -> zero overlap.
    # (An empty preferred list intentionally scores 1.0 for that component; that
    # existing math is unchanged.)
    assert _overlap_score(["python"], ["rust"], ["go"]) == 0.0
