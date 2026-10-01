#!/usr/bin/env bash
# Downloads public source PDFs into magellan/sources/ (git-ignored: awards contain real names).
set -euo pipefail
cd "$(dirname "$0")/../sources" 2>/dev/null || { mkdir -p "$(dirname "$0")/../sources"; cd "$(dirname "$0")/../sources"; }
mkdir -p awards/txt policies regulations

dl() {
  curl -sfL -A "Mozilla/5.0" --max-time 90 -o "$1" "$2" && file -b "$1" | grep -q PDF \
    && echo "ok   $1" || { echo "fail $1"; rm -f "$1"; }
}

# Insurance Ombudsman health ("mediclaim") award books, 2005-2012, ~2,700 cases.
for i in $(seq 1 40); do
  dl "awards/Mediclaim-Book$i.pdf" "https://www.cioins.co.in/GIC/mediclaim/Mediclaim-Book$i.pdf" 2>/dev/null || true
done

dl regulations/IRDAI_Health_Master_Circular_2024.pdf "https://irdai.gov.in/documents/37343/365525/%e0%a4%b8%e0%a5%8d%e0%a4%b5%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%a5%e0%a5%8d%e0%a4%af+%e0%a4%ac%e0%a5%80%e0%a4%ae%e0%a4%be+%e0%a4%b5%e0%a5%8d%e0%a4%af%e0%a4%b5%e0%a4%b8%e0%a4%be%e0%a4%af+%e0%a4%aa%e0%a4%b0+%e0%a4%ae%e0%a4%be%e0%a4%b8%e0%a5%8d%e0%a4%9f%e0%a4%b0+%e0%a4%aa%e0%a4%b0%e0%a4%bf%e0%a4%aa%e0%a4%a4%e0%a5%8d%e0%a4%b0+_+Master+Circular++on+Health++Insurance+Business++29052024.pdf/5e707a91-b5de-1ec1-cf18-b66273a6839d?t=1716962621002&version=1.0"

dl policies/Star_Family_Health_Optima_V21.pdf "https://d28c6jni2fmamz.cloudfront.net/Policy_Family_Health_Optima_Insurance_Plan_V_21_bbe089bd74.pdf"
dl policies/HDFC_ERGO_Optima_Secure.pdf "https://www.hdfcergo.com/docs/default-source/downloads/policy-wordings/health/optima-secure-revision-pw.pdf"
dl policies/Niva_Bupa_ReAssure_3.pdf "https://transactions.nivabupa.com/pages/doc/policy_wording/ReAssure30_Policy_Wordings.pdf"
dl policies/Care_Supreme.pdf "https://s3.ap-south-1.amazonaws.com/ditto-partners/Care_Supreme_Policy_Wording_dd859b2a9f.pdf"
dl policies/Bajaj_Health_Care_Supreme.pdf "https://www.bajajgeneralinsurance.com/download-documents/health-insurance/Health-PW/Health-Care-Supreme_PW.pdf"

if command -v pdftotext >/dev/null; then
  for f in awards/*.pdf; do pdftotext -layout "$f" "awards/txt/$(basename "${f%.pdf}").txt"; done
fi
