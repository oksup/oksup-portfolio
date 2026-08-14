# Product One-Pager

*Working name: Style Report. Brand name TBD, see Naming below. Drafted 2026-07-25.*

---

**What it is (one sentence):**
A Bahasa-Indonesian AI style report that answers "what do I wear to this specific event," built from one selfie and a short quiz, emailed as a personalised plan with buyable items.

**Who pays for it:**
Indonesians roughly 20-35 with a dated event they care about and low confidence about what to wear. The buying trigger is a deadline, not a general interest in fashion. Primary v1 segment: **kondangan** (wedding guest), which is high frequency, socially high stakes, and recurring for the same person several times a year.

**What they do today instead:**
Ask a friend or sibling. Scroll TikTok and Instagram for "OOTD kondangan" and copy someone with a different face, colouring, budget and body. Buy something and hope. Or wear the same thing again and feel bad about it.

**Why they would switch:**
The TikTok answer is generic. It is one outfit on one person, with no reason it should work for you. This gives a reason: your colouring, your face shape, the specific dress code of that event, and then actual items you can buy in Indonesia at a stated price. It converts a vague anxiety into a shopping list.

**First version scope (what ships in week 1):**

| In | Out |
|---|---|
| One occasion only: kondangan | Every other occasion |
| Bahasa Indonesia only | English |
| Landing page + quiz (6-8 questions) + selfie upload | Native app, accounts, login |
| Free teaser emailed instantly (3 findings) | Anything requiring a user to come back |
| Paid full report emailed within ~15 min | Real-time generation on-page |
| Xendit checkout (QRIS first) | Stripe, subscriptions, refunds flow |
| One SEO landing page targeting the main keyword | Content programme |

**What it costs to run:**

| Item | Cost |
|---|---|
| Gemini vision + text per report | Cents. Flash for the teaser, Pro for the paid report. |
| Hosting (Vercel or Cloudflare free tier) | $0 until real traffic |
| Domain | ~$12/year |
| Email (Brevo free tier, 300/day) | $0 |
| Xendit | Per transaction, see the fee flag below |

Fixed cost is effectively zero. This is the right shape for something that might not work.

**How money arrives:**
Free teaser to capture the email, one-off paid unlock for the full report. No subscription. Xendit for QRIS, e-wallet and bank transfer, because Indonesian consumers largely do not pay with cards and Stripe is a poor fit here.

Suggested test price: **Rp 39.000**. Impulse territory, no deliberation, no asking a partner. See the fee flag before locking it.

**How I know it failed (the number that tells me to stop):**

| Check | At | Kill signal |
|---|---|---|
| Does anyone want it | 300 free teasers delivered | Under 3% convert to paid. The offer is wrong, not the traffic. |
| Does the SEO thesis hold | 8 weeks after the landing page is live | Under 100 organic visits/month. Your one real edge is not working. |
| Is it good | First 30 paid reports | More than 3 refund requests, or you would not send it to a friend. |

---

## Flags

**Transaction fees at a low price point.** QRIS merchant fee is regulated by Bank Indonesia at 0.7%, but Xendit also charges a fixed per-transaction processing fee, plus 11% PPN on the fees. On a Rp 39.000 product a fixed fee dominates the percentage fee. Run the numbers in Xendit's pricing calculator before setting the price. If fixed fees eat more than about 10%, either raise the price to Rp 59.000 or bundle two occasions.

**Brevo account separation.** The Nakula Brevo account and its wedding lists are a work asset. This product needs its own Brevo account, its own sending domain, and its own list. Do not cross them. Related: Nakula's own SPF and DKIM gap is a known open issue, so set those up correctly for this domain from day one rather than inheriting the same problem.

**Photo handling is the real risk here.** You are asking people to upload selfies. Decide before launch: how long you keep the image, whether it goes to Gemini's paid tier (it must, free tier may be used for training), and what the privacy page says. Get this wrong once and the product is dead. Delete the image after report generation and say so on the page.

**Do not copy FaceCard's assets.** Same category is fine. Their copy, page structure, report format and prompts are not. Write your own.

---

## Naming

The brand name is not chosen. Two things to weigh, and they pull in different directions:

- **"Padu padan"** is the standard Indonesian term for outfit coordination. If it has the search volume you would expect, an exact-match or near-match domain is a genuine SEO asset. Check it in your keyword tool before deciding, do not assume.
- Generic descriptive names rank easier but are near-impossible to defend or trademark. Six products already call themselves some version of "FaceCard" and none of them own the term.

Recommendation: pick a short brandable name for the product, and win the keywords with page titles and content rather than the domain. Decide after the keyword check, not before.

---

## Why this product, for this build

It is a good first target for the agent system regardless of whether it makes money:

- Small enough to ship in a week, so the control plane gets a real workload fast.
- You can test it on yourself, no external dependency.
- Clean monetisation with no subscription infrastructure.
- Every stage (spec, code, deploy, analytics, payments) maps to a channel you already planned.

If it fails, it fails cheaply and the control plane is still built.
