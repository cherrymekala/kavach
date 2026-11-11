// Static, crawlable pages for search engines and AI assistants (SEO / AEO / GEO).
//
// The app is a single-page React app, so crawlers see an empty shell. This script runs after
// `vite build` and writes plain HTML pages into dist/ from data already in the repo:
//   /guides                         index of rejection reasons
//   /guides/<reason>                one page per rejection reason (real Ombudsman outcomes,
//                                   verbatim IRDAI rules, example awards, how to appeal, FAQ)
//   /guides/insurance-ombudsman-complaint   step-by-step complaint guide
//   /insurers/<slug>                per-insurer outcome pages
//   sitemap.xml, robots.txt, llms.txt
// Firebase Hosting serves these files before the SPA rewrite (cleanUrls: /guides/x -> x.html).
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const here = path.dirname(fileURLToPath(import.meta.url))
const web = path.resolve(here, '..')
const packs = path.resolve(web, '../../magellan/packs')
const dist = path.join(web, 'dist')
const SITE = (process.env.VITE_SITE_URL || readEnv('VITE_SITE_URL') || 'https://kavach-510312.web.app').replace(/\/$/, '')

const G = JSON.parse(fs.readFileSync(path.join(packs, 'IN.guides.json'), 'utf8'))
const I = JSON.parse(fs.readFileSync(path.join(packs, 'IN.insights.json'), 'utf8'))
const en = JSON.parse(fs.readFileSync(path.join(web, 'src/i18n/en.json'), 'utf8'))
const LABEL = en.summary.category
const MEANING = en.summary.meaning
const TODAY = new Date().toISOString().slice(0, 10)

function readEnv(key) {
  try {
    const line = fs.readFileSync(path.join(web, '.env'), 'utf8').split('\n').find((l) => l.startsWith(key + '='))
    return line ? line.slice(key.length + 1).trim() : ''
  } catch {
    return ''
  }
}

const esc = (s) => String(s ?? '').replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' })[c])
const num = (n) => n.toLocaleString('en-IN')
const OUTCOME = { allowed: 'Patient won', partly_allowed: 'Partly paid', dismissed: 'Insurer won' }
const OMBUDSMAN_SLUG = 'insurance-ombudsman-complaint'

const CSS = `
:root{--bg:#eeedf4;--card:#fff;--ink:#121027;--muted:#5d5a78;--line:#dddbe8;--indigo:#3b2bd9;--soft:#e4e1fb;--verm:#ff5a36;--mint:#12805c}
@media (prefers-color-scheme:dark){:root{--bg:#0f0e1a;--card:#1a1829;--ink:#ecebf5;--muted:#a9a6c2;--line:#2c2a40;--indigo:#8f85ff;--soft:#26224a;--verm:#ff7a5c;--mint:#3cc79c}}
*{box-sizing:border-box}html{-webkit-text-size-adjust:100%}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 Manrope,system-ui,sans-serif}
a{color:var(--indigo)}
.wrap{max-width:760px;margin:0 auto;padding:0 16px}
header.top{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 0}
.brand{display:flex;align-items:center;gap:8px;text-decoration:none;color:var(--ink);font:800 22px Unbounded,system-ui,sans-serif;letter-spacing:-.04em}
.brand svg{height:28px}
.cta{display:inline-block;background:var(--indigo);color:#fff;text-decoration:none;font-weight:800;border-radius:999px;padding:12px 22px}
.cta.small{padding:8px 16px;font-size:14px}
h1{font:700 clamp(28px,6vw,42px)/1.12 Unbounded,system-ui,sans-serif;letter-spacing:-.035em;margin:24px 0 12px}
h2{font:700 22px/1.25 Unbounded,system-ui,sans-serif;letter-spacing:-.03em;margin:40px 0 12px}
h3{font-size:17px;margin:0 0 6px}
.lead{font-size:18px;color:var(--muted)}
.card{background:var(--card);border-radius:22px;padding:20px;margin:12px 0;border:1px solid var(--line)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px}
.stat{background:var(--card);border-radius:18px;padding:16px;border:1px solid var(--line)}
.stat b{display:block;font:800 30px Unbounded,system-ui,sans-serif;letter-spacing:-.04em}
.stat.hero{background:var(--indigo);color:#fff;border:0}
.stat span{font-size:14px;color:inherit;opacity:.85}
blockquote{margin:8px 0 0;padding:12px 16px;border-left:4px solid var(--indigo);background:var(--soft);border-radius:0 14px 14px 0}
.ref{font-size:13px;color:var(--muted)}
.pill{display:inline-block;font-size:12px;font-weight:800;border-radius:999px;padding:3px 10px;margin-bottom:6px}
.pill.allowed,.pill.partly_allowed{background:#dff5ec;color:var(--mint)}.pill.dismissed{background:#ffe6df;color:#b8381a}
ol.steps{padding-left:20px}ol.steps li{margin:8px 0}
.list{list-style:none;padding:0;margin:0}.list li{border-bottom:1px solid var(--line)}.list a{display:flex;justify-content:space-between;gap:12px;padding:14px 4px;text-decoration:none;color:var(--ink)}.list b{color:var(--indigo)}
details{border-bottom:1px solid var(--line);padding:12px 0}summary{font-weight:700;cursor:pointer}
.note{font-size:14px;color:var(--muted)}
footer{margin:48px 0 32px;font-size:14px;color:var(--muted)}
.band{background:var(--card);border-radius:24px;padding:24px;margin:40px 0;border:1px solid var(--line);text-align:center}
`

const MARK = `<svg viewBox="0 0 60 68" aria-hidden="true"><path d="M30 2 56 11v22c0 17-11 29-26 33C15 62 4 50 4 33V11z" fill="none" stroke="currentColor" stroke-width="5"/><path d="M14 22 30 29 46 22" fill="none" stroke="currentColor" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/><path d="M14 38 30 45 46 38" fill="none" stroke="#FF5A36" stroke-width="7" stroke-linecap="round" stroke-linejoin="round"/></svg>`

function page({ urlPath, title, description, body, jsonld = [] }) {
  const url = SITE + urlPath
  return `<!doctype html>
<html lang="en-IN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(title)}</title>
<meta name="description" content="${esc(description)}">
<link rel="canonical" href="${url}">
<meta property="og:type" content="article"><meta property="og:title" content="${esc(title)}"><meta property="og:description" content="${esc(description)}"><meta property="og:url" content="${url}"><meta property="og:site_name" content="Kavach">
<meta name="twitter:card" content="summary">
<meta name="theme-color" content="#eeedf4">
<link rel="icon" type="image/svg+xml" href="/icons/icon.svg">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;700;800&family=Unbounded:wght@700;800&display=swap" rel="stylesheet">
<style>${CSS}</style>
${jsonld.map((j) => `<script type="application/ld+json">${JSON.stringify(j)}</script>`).join('\n')}
</head>
<body>
<div class="wrap">
<header class="top"><a class="brand" href="/guides">${MARK}kavach</a><a class="cta small" href="/">Check my claim</a></header>
<main>
${body}
</main>
<footer>
<p>Kavach helps patients in India, Singapore and Malaysia appeal rejected health-insurance claims. This page is general information, not legal advice. Figures come from ${num(I.overall.total)} Insurance Ombudsman award synopses published by the Council for Insurance Ombudsmen (${esc(I.period.from)}–${esc(I.period.to)}).</p>
<p><a href="/guides">All guides</a> · <a href="/guides/${OMBUDSMAN_SLUG}">How to complain to the Ombudsman</a> · <a href="/insights">Rejection patterns</a></p>
</footer>
</div>
</body>
</html>
`
}

function ladderHtml() {
  return `<ol class="steps">${G.ladder
    .map((s) => `<li><b>${esc(s.step)}</b> (${esc(s.dispute_body)}). Use: ${esc(s.form)}. They should reply within ${s.deadline_days} days.</li>`)
    .join('')}</ol>
<p>You have <b>${Math.round(G.limitation.days / 30)} months (${G.limitation.days} days)</b> from ${esc(G.limitation.from)} to approach the ${esc(G.limitation.body)}. Complaining to the Ombudsman is free and you do not need a lawyer.</p>`
}

function faq(qas) {
  return {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: qas.map(([q, a]) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a } })),
  }
}

function article(urlPath, title, description) {
  return {
    '@context': 'https://schema.org',
    '@type': 'Article',
    headline: title,
    description,
    url: SITE + urlPath,
    dateModified: TODAY,
    inLanguage: 'en-IN',
    publisher: { '@type': 'Organization', name: 'Kavach', url: SITE },
    isBasedOn: { '@type': 'Dataset', name: 'Insurance Ombudsman award synopses (health and group mediclaim)', creator: 'Council for Insurance Ombudsmen' },
  }
}

function guidePage(g) {
  const s = g.stats
  const label = LABEL[g.key] ?? g.key
  const urlPath = `/guides/${g.slug}`
  const title = `Health insurance claim rejected for “${label}”? What the Ombudsman decided in ${num(s.total)} cases`
  const description = `${s.won_pct}% of ${num(s.total)} published Insurance Ombudsman cases about “${label}” ended with the claim paid in full or in part. The IRDAI rules, real decisions and how to appeal.`
  const qas = [
    [`Can I appeal a health claim rejected for “${label}”?`, `Yes. Write to the insurer's grievance cell first, then IRDAI's Bima Bharosa portal, then the Insurance Ombudsman. In ${num(s.total)} published Ombudsman cases on this ground, ${s.won_pct}% ended with the claim paid in full or in part.`],
    ['How long do I have to complain to the Insurance Ombudsman?', `Within ${Math.round(G.limitation.days / 30)} months (${G.limitation.days} days) of ${G.limitation.from}, after the insurer has replied to your complaint or not replied within ${G.ladder[0].deadline_days} days.`],
    ['Does it cost money to go to the Insurance Ombudsman?', 'No. Complaints to the Insurance Ombudsman are free, and you can present your case yourself.'],
  ]
  const body = `
<p class="note">Guide · Rejection reason</p>
<h1>Claim rejected for “${esc(label)}”?</h1>
<p class="lead">${esc(MEANING[g.key] ?? '')}</p>

<div class="stats">
  <div class="stat hero"><b>${s.won_pct}%</b><span>ended with the claim paid in full or in part</span></div>
  <div class="stat"><b>${num(s.allowed)}</b><span>paid in full</span></div>
  <div class="stat"><b>${num(s.partly_allowed)}</b><span>paid in part</span></div>
  <div class="stat"><b>${num(s.dismissed)}</b><span>rejection upheld</span></div>
</div>
<p class="note">From ${num(s.total)} published Insurance Ombudsman awards on this ground. ${esc(G.note)}</p>

<h2>What the rules say</h2>
${g.rules.map((r) => `<div class="card"><h3>${esc(r.title ?? r.ref)}</h3><blockquote>${esc(r.text)}</blockquote><p class="ref">${esc(r.ref)}${r.text.includes('####') ? ' · “####” is filled in by each policy: check yours for the number of months' : ''}</p></div>`).join('')}

<h2>Real Ombudsman decisions</h2>
${g.examples
  .map((e) => `<div class="card"><span class="pill ${e.decision}">${OUTCOME[e.decision]}</span><p style="margin:0">${esc(e.summary)}</p><p class="ref">${[e.insurer, e.year, e.case_no ? `Case ${e.case_no}` : null].filter(Boolean).map(esc).join(' · ')}</p></div>`)
  .join('')}

<h2>How to appeal</h2>
${ladderHtml()}
<p><a href="/guides/${OMBUDSMAN_SLUG}">Step-by-step: how to file an Insurance Ombudsman complaint →</a></p>

<div class="band">
  <h2 style="margin-top:0">Check your own rejection</h2>
  <p>Upload your rejection letter and policy. Kavach finds the rules and past decisions that apply to your case, writes the appeal and fills the forms.</p>
  <a class="cta" href="/">Check my claim</a>
</div>

<h2>Common questions</h2>
${qas.map(([q, a]) => `<details><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join('')}

<h2>Other rejection reasons</h2>
<ul class="list">${G.guides
    .filter((o) => o.slug !== g.slug)
    .map((o) => `<li><a href="/guides/${o.slug}"><span>${esc(LABEL[o.key] ?? o.key)}</span><b>${o.stats.won_pct}%</b></a></li>`)
    .join('')}</ul>`
  return { urlPath, html: page({ urlPath, title, description, body, jsonld: [article(urlPath, title, description), faq(qas)] }) }
}

function indexPage() {
  const urlPath = '/guides'
  const title = 'Health insurance claim rejected in India? Guides by rejection reason'
  const description = `How ${num(I.overall.total)} Insurance Ombudsman cases ended, by rejection reason: room rent, pre-existing disease, waiting periods, non-disclosure and more. Rules, real decisions and how to appeal.`
  const body = `
<h1>Claim rejected? Start with the reason.</h1>
<p class="lead">Across ${num(I.overall.total)} published Insurance Ombudsman cases, <b>${I.overall.won_pct}%</b> ended with the claim paid in full or in part. Pick the reason on your rejection letter to see the rules, real decisions and how to appeal.</p>
<ul class="list">${G.guides
    .map((g) => `<li><a href="/guides/${g.slug}"><span>${esc(LABEL[g.key] ?? g.key)} <span class="note">· ${num(g.stats.total)} cases</span></span><b>${g.stats.won_pct}%</b></a></li>`)
    .join('')}</ul>
<p class="note">Percent = share of published Ombudsman cases on that ground that ended with the claim paid in full or in part.</p>
<h2>Going to the Ombudsman</h2>
<p><a href="/guides/${OMBUDSMAN_SLUG}">How to file an Insurance Ombudsman complaint, step by step →</a></p>
<h2>By insurer</h2>
<ul class="list">${I.insurers.map((i) => `<li><a href="/insurers/${i.slug}"><span>${esc(i.key)} <span class="note">· ${num(i.total)} cases</span></span><b>${i.won_pct}%</b></a></li>`).join('')}</ul>`
  return { urlPath, html: page({ urlPath, title, description, body, jsonld: [article(urlPath, title, description)] }) }
}

function ombudsmanPage() {
  const urlPath = `/guides/${OMBUDSMAN_SLUG}`
  const title = 'How to file an Insurance Ombudsman complaint for a rejected health claim'
  const description = 'Step by step: when you can go to the Insurance Ombudsman, the time limit, the Annexure VI-A form, which office to choose and what happens at the hearing. Free, no lawyer needed.'
  const offices = JSON.parse(fs.readFileSync(path.join(packs, 'IN.json'), 'utf8')).ombudsman_offices ?? []
  const qas = [
    ['When can I go to the Insurance Ombudsman?', `After you have complained to the insurer and it rejected your complaint, did not reply within ${G.ladder[0].deadline_days} days, or you are not satisfied with its reply.`],
    ['What is the time limit?', `Within ${Math.round(G.limitation.days / 30)} months (${G.limitation.days} days) of ${G.limitation.from}.`],
    ['Which form do I use?', 'The complaint form in Annexure VI-A of the Insurance Ombudsman Rules, 2017, sent to the Ombudsman office for your area. You can also complain online.'],
    ['Do I need a lawyer and does it cost anything?', 'No. Complaints are free and you present your case yourself at the hearing.'],
  ]
  const body = `
<p class="note">Guide · Insurance Ombudsman</p>
<h1>How to file an Insurance Ombudsman complaint</h1>
<p class="lead">The Insurance Ombudsman decides disputes between policyholders and insurers. It is free, you do not need a lawyer, and in ${num(I.overall.total)} published health cases <b>${I.overall.won_pct}%</b> ended with the claim paid in full or in part.</p>
<h2>The steps, in order</h2>
${ladderHtml()}
<h2>What to send with your complaint</h2>
<ol class="steps">
<li>The completed Annexure VI-A form, signed.</li>
<li>The insurer's rejection letter and its reply to your complaint (or proof that it did not reply).</li>
<li>Your policy document and schedule.</li>
<li>Hospital papers: discharge summary, bills, reports.</li>
<li>A short, dated account of what happened and what you are asking for.</li>
</ol>
<h2>Which office?</h2>
<p>Send it to the Ombudsman office that covers the area where you live. There are ${offices.length} offices:</p>
${offices.map((o) => `<div class="card"><h3>${esc(o.centre)}</h3><p style="margin:0">Covers: ${esc(o.jurisdiction)}</p><p class="ref">${esc(o.address)}${o.email ? ` · ${esc(o.email)}` : ''}${o.phone ? ` · ${esc(o.phone)}` : ''}</p></div>`).join('')}
<p class="note">Office details from cioins.co.in. Check the Council for Insurance Ombudsmen website before sending, as addresses can change.</p>
<h2>The hearing</h2>
<p>The Ombudsman hears both sides, in person or by video. Keep your answers short and stick to dates and documents. Kavach lets you rehearse it with a live AI Ombudsman and insurer's representative.</p>
<div class="band"><h2 style="margin-top:0">Let Kavach fill the form</h2><p>Upload your rejection letter and policy. Kavach writes your appeal, fills the Annexure VI-A form and picks the right office from your address.</p><a class="cta" href="/">Check my claim</a></div>
<h2>Common questions</h2>
${qas.map(([q, a]) => `<details><summary>${esc(q)}</summary><p>${esc(a)}</p></details>`).join('')}`
  return { urlPath, html: page({ urlPath, title, description, body, jsonld: [article(urlPath, title, description), faq(qas)] }) }
}

function insurerPage(ins) {
  const urlPath = `/insurers/${ins.slug}`
  const title = `${ins.key} health claim rejected? How ${num(ins.total)} Ombudsman cases ended`
  const description = `${ins.won_pct}% of ${num(ins.total)} published Insurance Ombudsman cases against ${ins.key} ended with the claim paid in full or in part. Breakdown by rejection reason and how to appeal.`
  const body = `
<p class="note">Insurer · Ombudsman outcomes</p>
<h1>${esc(ins.key)}: how disputes ended</h1>
${ins.now_known_as ? `<p class="note">Now known as ${esc(ins.now_known_as)}.</p>` : ''}
<div class="stats">
  <div class="stat hero"><b>${ins.won_pct}%</b><span>paid in full or in part</span></div>
  <div class="stat"><b>${num(ins.total)}</b><span>published cases (${esc(ins.period?.from)}–${esc(ins.period?.to)})</span></div>
  <div class="stat"><b>${I.overall.won_pct}%</b><span>all insurers</span></div>
</div>
<p class="note">${esc(I.note)}</p>
<h2>By rejection reason</h2>
<ul class="list">${(ins.grounds ?? [])
    .map((gr) => {
      const g = G.guides.find((x) => x.key === gr.key)
      const name = esc(LABEL[gr.key] ?? gr.key)
      const inner = `<span>${name} <span class="note">· ${num(gr.total)} cases · all insurers ${gr.everyone_won_pct}%</span></span><b>${gr.won_pct}%</b>`
      return `<li>${g ? `<a href="/guides/${g.slug}">${inner}</a>` : `<a>${inner}</a>`}</li>`
    })
    .join('')}</ul>
<h2>How to appeal</h2>
${ladderHtml()}
<div class="band"><h2 style="margin-top:0">Rejected by ${esc(ins.key)}?</h2><p>Kavach reads your rejection letter and policy, finds the rules and past decisions that apply, and writes your appeal.</p><a class="cta" href="/">Check my claim</a></div>`
  return { urlPath, html: page({ urlPath, title, description, body, jsonld: [article(urlPath, title, description)] }) }
}

function write(urlPath, html) {
  const file = path.join(dist, urlPath.replace(/^\//, '') + '.html')
  fs.mkdirSync(path.dirname(file), { recursive: true })
  fs.writeFileSync(file, html)
}

const pages = [indexPage(), ombudsmanPage(), ...G.guides.map(guidePage), ...I.insurers.map(insurerPage)]
for (const p of pages) write(p.urlPath, p.html)

const urls = ['/', '/insights', ...pages.map((p) => p.urlPath)]
fs.writeFileSync(
  path.join(dist, 'sitemap.xml'),
  `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls.map((u) => `  <url><loc>${SITE}${u === '/' ? '/' : u}</loc><lastmod>${TODAY}</lastmod></url>`).join('\n')}\n</urlset>\n`,
)
fs.writeFileSync(path.join(dist, 'robots.txt'), `User-agent: *\nAllow: /\nDisallow: /case/\nDisallow: /app\nDisallow: /join\n\nSitemap: ${SITE}/sitemap.xml\n`)
fs.writeFileSync(
  path.join(dist, 'llms.txt'),
  `# Kavach

> Kavach helps patients appeal rejected health-insurance claims in India, Singapore and Malaysia. It reads the rejection letter and policy, finds the regulations and past Ombudsman decisions that apply, writes the appeal, fills the official forms, rehearses the hearing and tracks deadlines. General information, not legal advice.

Key fact: in ${num(I.overall.total)} published Insurance Ombudsman health cases in India (${I.period.from}–${I.period.to}), ${I.overall.won_pct}% ended with the claim paid in full or in part. Complaints to the Ombudsman are free.

## Guides by rejection reason (India)
${G.guides.map((g) => `- [${LABEL[g.key] ?? g.key}](${SITE}/guides/${g.slug}): ${g.stats.won_pct}% of ${g.stats.total} Ombudsman cases ended with the claim paid in full or in part`).join('\n')}

## How to appeal
- [How to file an Insurance Ombudsman complaint](${SITE}/guides/${OMBUDSMAN_SLUG})

## By insurer
${I.insurers.map((i) => `- [${i.key}](${SITE}/insurers/${i.slug}): ${i.won_pct}% of ${i.total} cases`).join('\n')}

## Source
Insurance Ombudsman award synopses (health and group mediclaim) published by the Council for Insurance Ombudsmen; IRDAI regulations quoted verbatim.
`,
)
console.log(`seo: ${pages.length} pages, sitemap with ${urls.length} URLs, site ${SITE}`)
