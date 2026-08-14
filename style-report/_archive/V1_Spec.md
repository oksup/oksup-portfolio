# V1 Build Spec

Scope is `Product_One_Pager.md`. This is how it gets built. Target: shippable in a week of evenings.

---

## Stack, and one uncomfortable recommendation

**Recommendation: Next.js on Vercel. Not Python.**

You are a Python person and your instinct will be Streamlit, because that is what Crypto Trader uses. Do not do that here, for one specific reason: **Streamlit renders client-side and cannot rank in Google.** Your entire competitive thesis is SEO. Choosing a stack that cannot be indexed throws away the only advantage you have over six better-funded competitors.

| Layer | Choice | Why |
|---|---|---|
| Site + app | Next.js on Vercel | Server-rendered, indexable, free tier, one deploy |
| Report generation | Next.js API route calling Gemini | One language, one repo, no separate worker to host |
| Image handling | Vercel Blob or Cloudflare R2, deleted after generation | Never store selfies longer than you need |
| Email | Brevo transactional API (own account) | You already know it. SPF and DKIM set up properly this time. |
| Payment | Xendit invoice or QRIS | Local payment methods, webhook to trigger the paid report |
| Database | Postgres on Neon or Supabase free tier | Orders, emails, report status. SQLite does not survive serverless. |

You will write some JavaScript. It is a week of discomfort against a permanent structural advantage. If that trade genuinely is not worth it to you, the fallback is Astro for the content pages plus a small FastAPI service for generation, but that is two deploys and more moving parts.

---

## The pipeline

```
Landing page (SEO, Bahasa)
   -> Quiz: 6-8 questions + selfie upload
   -> Store submission, queue job
   -> [FREE] Gemini Flash: 3-finding teaser
   -> Email teaser instantly + unlock link
   -> Xendit checkout (Rp 39.000)
   -> Webhook: payment.succeeded
   -> [PAID] Gemini Pro: full report
   -> Render PDF or hosted HTML page
   -> Email the report
   -> Delete the selfie
```

Two model calls, deliberately different. The teaser must be fast and cheap because most people never pay. The paid report is where quality matters and Pro earns its cost.

**Quiz questions (draft):** gender presentation, age bracket, event formality (akad, resepsi, afterparty), time of day, indoor or outdoor, budget band, hijab or not, anything they already own and want to build around.

Keep it under 8. Every extra question costs completions.

**Full report sections:** colour palette with hex swatches, face shape read and what it implies, the outfit formula for that dress code, 5-8 specific buyable items with price and link, an avoid-list, hair or hijab note, grooming note.

The buyable items are the part people pay for. Everything else is context. Get those right before polishing anything else.

---

## Build order

Each step is independently verifiable. Do not move on until the checkpoint passes.

| # | Step | Checkpoint |
|---|---|---|
| 1 | Next.js app, deployed to Vercel, one static page | Live URL loads |
| 2 | Quiz form, no upload yet, writes to Postgres | Submission appears in the DB |
| 3 | Selfie upload to blob storage | File lands, URL stored, you can open it |
| 4 | Gemini Flash teaser from selfie + answers, printed to console | Output is good enough that you would send it |
| 5 | Brevo transactional email with the teaser | Arrives in inbox, not spam. Check SPF and DKIM. |
| 6 | Gemini Pro full report, rendered as an HTML page | You would pay Rp 39.000 for it |
| 7 | Xendit checkout + webhook | Test payment triggers the paid report |
| 8 | Delete selfie after generation, privacy page live | Blob is gone, page states the policy |
| 9 | SEO landing page for the main keyword | Indexed, correct title and meta, real Bahasa copy |

**Step 4 and 6 are the whole product.** If the report is not good, nothing else matters. Spend disproportionate time on those two prompts and run them on yourself, your wife, and three friends before building any checkout.

---

## Seed backlog

Once the orchestrator is running, this is the first real thing you give it. In `#tasks`, one message per line:

```
add a task to check padu padan keyword volume before picking a domain
add a task to set up a separate Brevo account with SPF and DKIM
add a task to run Xendit pricing calculator at Rp 39.000 and Rp 59.000
add a task to write the kondangan report prompt and test it on 5 people
add a task to deploy a hello world Next.js app to Vercel
add a task to write the privacy policy covering selfie deletion
```

That is your dogfood moment: the first tasks the agent tracks are the tasks for building the product it exists to serve.

---

## What the agent owns, and what it does not

You decided the agent tracks while you build v1. Concretely:

**Agent owns:** task capture and status, spec notes in `#wiki`, later on PR descriptions and changelog, log triage.

**You own:** all product code, the two Gemini prompts, the price, anything touching money or selfies.

Revisit after v1 ships. The natural first handover is prompt iteration: once you have 30 real reports and know what good looks like, that becomes an eval set the agent can optimise against.

---

## Open decisions

| # | Decision | Needed by |
|---|---|---|
| 1 | Brand name and domain | Step 1 |
| 2 | Price: Rp 39.000 or Rp 59.000, after fee maths | Step 7 |
| 3 | Report delivery: PDF attachment or hosted page | Step 6. Hosted page is easier and gives you analytics. |
| 4 | Whether v1 covers women only, or both | Step 4. Women only halves the prompt work and is the bigger kondangan market. |
