from kavach.agents import filing


def test_indian_digit_grouping():
    assert filing._money(112000, "INR") == "Rs. 1,12,000"
    assert filing._money(38400, "INR") == "Rs. 38,400"
    assert filing._money(12345678, "INR") == "Rs. 1,23,45,678"
    assert filing._money(950, "INR") == "Rs. 950"
    assert filing._money(2500, "SGD") == "S$ 2,500"


def test_letter_pdf_renders_indic_scripts():
    from kavach.models import Letter

    letter = Letter(
        subject="अपील", english="Appeal", local="दावा ₹38,400 · தமிழ் · తెలుగు", language="hi"
    )
    pdf = filing.render_letter_pdf(letter, local=True)
    assert pdf.startswith(b"%PDF") and b"NotoSansDevanagari" in pdf
