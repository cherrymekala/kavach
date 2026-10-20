from kavach.agents import checker
from kavach.agents.strategist import SCORE
from kavach.models import Argument, Assessment, Document, Source

REG = "After completion of sixty continuous months of coverage (including portability and migration) in health insurance policy, no policy and claim shall be contestable"


def test_quote_matching_ignores_case_spacing_and_quote_styles():
    assert checker.quote_in("sixty  continuous MONTHS of coverage", REG)
    assert checker.quote_in("“no policy and claim shall be contestable”", REG)
    assert checker.quote_in("sixty continuous months ... shall be contestable", REG)


def test_quote_matching_rejects_paraphrase_and_wrong_order():
    assert not checker.quote_in("after five years no claim can be contested", REG)
    assert not checker.quote_in("shall be contestable ... sixty continuous months", REG)
    assert not checker.quote_in("", REG)


def test_quote_matching_tolerates_pdf_spacing():
    assert checker.quote_in("pre-existing disease", "Pre-existingdisease means")


def test_verify_drops_unsupported_sources_and_empty_arguments(tmp_path):
    letter = tmp_path / "letter.txt"
    letter.write_text("The claim is repudiated under Code Excl 01.")
    docs = [
        Document(id="1", filename="letter.txt", gcs_uri=str(letter), doc_type="rejection_letter")
    ]
    sections = [{"ref": "cl. 8", "text": REG}]
    real = Argument(
        claim="a",
        explanation="",
        sources=[
            Source(kind="regulation", ref="cl. 8", quote="sixty continuous months"),
            Source(kind="regulation", ref="cl. 8", quote="seven years"),
        ],
    )
    letter_arg = Argument(
        claim="b",
        explanation="",
        sources=[
            Source(kind="rejection_letter", ref="p.1", quote="repudiated under Code Excl 01"),
        ],
    )
    invented = Argument(
        claim="c",
        explanation="",
        sources=[
            Source(kind="ruling", ref="in-ombud-x", quote="the Ombudsman ruled for the patient"),
        ],
    )
    draft = Assessment(strength="strong", score=0.8, arguments=[real, letter_arg, invented])

    out = checker.verify(draft, docs, sections, similar=[])

    assert [a.claim for a in out.arguments] == ["a", "b"]
    assert [s.quote for s in out.arguments[0].sources] == ["sixty continuous months"]
    assert all(s.verified for a in out.arguments for s in a.sources)


def test_ruling_citation_is_human_readable():
    r = {
        "id": "in-ombud-abc",
        "case_no": "GI/160/UII/09",
        "award_date": "2009-06-01",
        "insurer": "United India Insurance",
    }
    assert (
        checker.ruling_label(r)
        == "Insurance Ombudsman award, Case No. GI/160/UII/09 (2009, United India Insurance)"
    )


# ── The verdict must follow the arguments that survived ───────────────────────────────
#
# The checker's whole purpose is catching unsupported claims. Leaving the strategist's
# "strong" in place after dropping the arguments behind it defeats that: the UI would show a
# strong case whose every claim failed verification.


def _assessment(strength: str, arguments: list[Argument]) -> Assessment:
    return Assessment(strength=strength, score=SCORE[strength], arguments=arguments, disclaimer="x")


def _verified_assessment(strength: str, kept: int, dropped: int) -> Assessment:
    """`kept` arguments that quote a real regulation, plus `dropped` that do not."""
    real = Argument(
        claim="supported",
        explanation="",
        sources=[Source(kind="regulation", ref="cl. 8", quote="sixty continuous months")],
    )
    invented = Argument(
        claim="invented",
        explanation="",
        sources=[Source(kind="regulation", ref="cl. 8", quote="a clause that is not there")],
    )
    return _assessment(strength, [real] * kept + [invented] * dropped)


def _verify(assessment: Assessment) -> Assessment:
    return checker.verify(assessment, [], [{"ref": "cl. 8", "text": REG}], [])


def test_an_untouched_verdict_is_left_alone():
    result = _verify(_verified_assessment("strong", kept=2, dropped=0))
    assert (result.strength, result.score) == ("strong", SCORE["strong"])
    assert len(result.arguments) == 2


def test_losing_an_argument_costs_a_band():
    result = _verify(_verified_assessment("strong", kept=2, dropped=1))
    assert result.strength == "medium"
    assert result.score == SCORE["medium"]
    assert len(result.arguments) == 2


def test_a_case_with_nothing_left_verified_cannot_read_strong():
    result = _verify(_verified_assessment("strong", kept=0, dropped=3))
    assert result.arguments == []
    assert result.strength == "weak"
    assert result.score == SCORE["weak"]
