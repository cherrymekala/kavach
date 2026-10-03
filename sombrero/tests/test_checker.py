from kavach.agents import checker
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
