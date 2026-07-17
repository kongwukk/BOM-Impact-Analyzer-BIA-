from types import SimpleNamespace

from app.services.impact import _candidate_score, _search_terms


def test_search_terms_split_name_and_model() -> None:
    assert _search_terms("WF模块,IXC32-18-XHHIX-313-E08") == [
        "WF模块",
        "IXC32-18-XHHIX-313-E08",
    ]


def test_exact_part_number_ranks_above_description_match() -> None:
    query = "IXC32-18-XHHIX-313-E08"
    terms = _search_terms(query)
    exact = SimpleNamespace(
        part_number=query, description="WF模块", manufacturer=None, attributes={}
    )
    description = SimpleNamespace(
        part_number="X015010026",
        description=f"WF模块, {query}",
        manufacturer=None,
        attributes={"material_code": "18X801080098"},
    )

    assert _candidate_score(exact, query, terms) > _candidate_score(
        description, query, terms
    )
