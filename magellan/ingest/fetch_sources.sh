#!/usr/bin/env bash
# Downloads public source PDFs into magellan/sources/ (git-ignored: awards contain real names).
set -euo pipefail
cd "$(dirname "$0")/../sources" 2>/dev/null || { mkdir -p "$(dirname "$0")/../sources"; cd "$(dirname "$0")/../sources"; }
mkdir -p awards/txt policies regulations codes

dl() {
  curl -sfL -A "Mozilla/5.0" --max-time 90 -o "$1" "$2" && file -b "$1" | grep -q PDF \
    && echo "ok   $1" || { echo "fail $1"; rm -f "$1"; }
}

# Insurance Ombudsman health ("mediclaim") award books, 2005-2012, ~2,700 cases.
# Individual + group mediclaim books (2005-2016, ~3,250 awards). No directory listing exists,
# so these are the known file-name patterns.
B=https://www.cioins.co.in/GIC
for i in $(seq 1 40); do
  dl "awards/Mediclaim-Book$i.pdf" "$B/mediclaim/Mediclaim-Book$i.pdf" 2>/dev/null || true
  dl "awards/GroupMediclaim-Book$i.pdf" "$B/groupmediclaim/GroupMediclaim-Book$i.pdf" 2>/dev/null || true
done
dl awards/Mediclaim_2014-10_to_2015-03.pdf "$B/mediclaim/GENERAL_INSURANCE_MEDICLAIM_AWARDS1-10-2014TO31.3.2015.pdf"
dl awards/Mediclaim_2015-04_to_2015-09.pdf "$B/mediclaim/GENERAL_INSURANCE_MEDICLAIM_APRIL_2015TOSEPT-2015.pdf"
dl awards/GroupMediclaim-Gen.pdf "$B/groupmediclaim/Group%20Mediclaim%20Gen.pdf"
dl awards/GroupMediclaim-General26.pdf "$B/groupmediclaim/Group%20Medi%20Claim%20-%20General26.pdf"
dl awards/GroupMediclaim-Gen27.pdf "$B/groupmediclaim/Group%20Mediclaim-%20Gen27.pdf"

dl regulations/IRDAI_Health_Master_Circular_2024.pdf "https://irdai.gov.in/documents/37343/365525/%e0%a4%b8%e0%a5%8d%e0%a4%b5%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%a5%e0%a5%8d%e0%a4%af+%e0%a4%ac%e0%a5%80%e0%a4%ae%e0%a4%be+%e0%a4%b5%e0%a5%8d%e0%a4%af%e0%a4%b5%e0%a4%b8%e0%a4%be%e0%a4%af+%e0%a4%aa%e0%a4%b0+%e0%a4%ae%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%9f%e0%a4%b0+%e0%a4%aa%e0%a4%b0%e0%a4%bf%e0%a4%aa%e0%a4%a4%e0%a5%8d%e0%a4%b0+_+Master+Circular++on+Health++Insurance+Business++29052024.pdf/5e707a91-b5de-1ec1-cf18-b66273a6839d?t=1716962621002&version=1.0"

dl regulations/IRDAI_Insurance_Products_Regulations_2024.pdf "https://irdai.gov.in/documents/37343/366405/%E0%A4%86%E0%A4%88%E0%A4%86%E0%A4%B0%E0%A4%A1%E0%A5%80%E0%A4%8F%E0%A4%86%E0%A4%88+%28%E0%A4%AC%E0%A5%80%E0%A4%AE%E0%A4%BE+%E0%A4%89%E0%A4%A4%E0%A5%8D%E0%A4%AA%E0%A4%BE%E0%A4%A6%29+%E0%A4%B5%E0%A4%BF%E0%A4%A8%E0%A4%BF%E0%A4%AF%E0%A4%AE%2C+2024+_+IRDAI+%28Insurance+Products%29+Regulations%2C+2024.pdf/eb55db8a-a617-d492-b313-f13cfb11afeb?version=1.2&t=1712320142367&download=true"

dl regulations/IRDAI_Standardization_Master_Circular_2020.pdf "https://irdai.gov.in/documents/37343/366029/Master+Circular+on+Standardization+of+Health+Insurance+Products.pdf/40548736-71a8-1b76-e28d-0df899407e1e?version=1.2&t=1665033878433&download=true"

dl policies/Star_Family_Health_Optima_V21.pdf "https://d28c6jni2fmamz.cloudfront.net/Policy_Family_Health_Optima_Insurance_Plan_V_21_bbe089bd74.pdf"
dl policies/HDFC_ERGO_Optima_Secure.pdf "https://www.hdfcergo.com/docs/default-source/downloads/policy-wordings/health/optima-secure-revision-pw.pdf"
dl policies/Niva_Bupa_ReAssure_3.pdf "https://transactions.nivabupa.com/pages/doc/policy_wording/ReAssure30_Policy_Wordings.pdf"
dl policies/Care_Supreme.pdf "https://s3.ap-south-1.amazonaws.com/ditto-partners/Care_Supreme_Policy_Wording_dd859b2a9f.pdf"
dl policies/Bajaj_Health_Care_Supreme.pdf "https://www.bajajgeneralinsurance.com/download-documents/health-insurance/Health-PW/Health-Care-Supreme_PW.pdf"

# Singapore Integrated Shield plan contracts (published by MOH).
mkdir -p sg/policies
dl sg/policies/AIA_HealthShield_Gold_Max_2025.pdf "https://isomer-user-content.by.gov.sg/3/b3641f37-3948-481f-ae58-013608545f14/AIA%20HSG%20Max_202510.PDF"
dl sg/policies/PRUShield_2026.pdf "https://isomer-user-content.by.gov.sg/3/a3986bc4-5532-41fb-bcfa-2c4434492b73/PRUShield%20V2%20-%20Apr2026.pdf"

# NHCX claim adjudication reason codes (source of magellan/packs/IN.json rejection_codes).
curl -sfL --max-time 60 -o codes/ndhm-adjudication-reason.json \
  https://nrces.in/ndhm/fhir/r4/CodeSystem-ndhm-adjudication-reason.json && echo "ok   codes/ndhm-adjudication-reason.json"

if command -v pdftotext >/dev/null; then
  for f in awards/*.pdf; do pdftotext -layout "$f" "awards/txt/$(basename "${f%.pdf}").txt"; done
fi
