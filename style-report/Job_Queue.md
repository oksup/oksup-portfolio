# Job Queue

**You do not paste these.** Load them into the tracker once, then drive the whole queue from Discord.

```bash
cd ~/Documents/"Cowork OS"/"Personal Projects"/"Agent Control Plane"/orchestrator
source .venv/bin/activate
python seed_tasks.py
```

That reads this file and creates one task per job below. From then on, in `#code`:

| You say | What happens |
|---|---|
| `next` | Takes the next unfinished task and builds it. No retyping. |
| (wait) | It posts a PR link when the build passes |
| `ship agent/...` | Merges it, marks the task done, tells you how many are left |
| `next` | On to the next one |

So the whole queue is `next`, test, `ship`, `next`, test, `ship`.

**Why it stops for you between jobs:** A4 builds on A3. If A3 came out wrong and the queue kept running, A5 through A8 would build on a broken foundation and waste an evening's quota. Also, only you can tell whether the Bahasa sounds natural or whether the report layout is worth paying for.

Edit the blocks below before seeding if you want different wording. Re-running `seed_tasks.py` skips anything already queued, so it is safe to run twice.

The order matters: everything in Phase A needs **no accounts, no signups, no API keys**. That is roughly a week of visible progress you can start on tonight. Signups only appear in Phase B.

---

## Phase A: the whole thing, with fake data

The goal of Phase A is a product you can click through end to end, where the report is hardcoded nonsense. That sounds backwards. It is not. It lets you judge the flow and the design before spending a single API call, and it means when you do wire up the AI, that is the only thing that can be broken.

---

### A1. Landing page

```
Replace the home page with a landing page in Bahasa Indonesia for a wedding-guest style advice service.

Headline: Bingung mau pakai apa ke kondangan?
Subheading: Upload satu selfie, jawab 6 pertanyaan singkat. Kami kirimkan panduan gaya khusus buat kamu, lengkap dengan rekomendasi yang bisa langsung dibeli.
Button: Mulai, gratis

The button links to /quiz. Centre everything, make it work on a phone first. Keep it plain and clean, no stock photos, no icons.
```

**Check on preview:** reads correctly on your phone, button goes to /quiz (which will 404 for now, that is expected).

---

### A2. Quiz shell, one question

```
Create a page at /quiz with a single question and four answer buttons.

Question: Acaranya apa?
Options: Akad, Resepsi, Ngunduh mantu, Afterparty

Selecting an option highlights it. A Lanjut button at the bottom is disabled until something is selected. It does nothing yet.

Same plain style as the landing page, phone first.
```

**Check:** you can select, only one stays highlighted, Lanjut enables.

---

### A3. All six questions, one per screen

```
Turn /quiz into a six step flow, one question per screen, with a back button and a progress indicator showing step X of 6. Keep the answers in memory as the user moves between steps, so going back shows what they picked.

1. Acaranya apa? — Akad / Resepsi / Ngunduh mantu / Afterparty
2. Kapan acaranya? — Pagi / Siang / Sore / Malam
3. Di mana? — Indoor (gedung atau hotel) / Outdoor (garden atau beach) / Di rumah / Belum tahu
4. Kamu berpakaian sebagai? — Perempuan / Laki-laki
5. Pakai hijab? — Ya / Tidak
6. Budget outfit? — Di bawah 300rb / 300rb sampai 700rb / 700rb sampai 1,5jt / Di atas 1,5jt

On the last step the button says Lanjut ke foto and goes to /quiz/foto, which does not exist yet.
```

**Check:** all six work, back preserves answers, progress bar counts correctly.

---

### A4. Photo step

```
Add a page at /quiz/foto that asks for one selfie.

Heading: Terakhir, upload satu selfie
Small text below: Wajah terlihat jelas, cahaya cukup, tanpa filter. Foto kamu dihapus setelah laporan dikirim.

A single upload button that accepts images only. After choosing, show a small preview of the photo and a Kirim button. Nothing is uploaded anywhere yet, keep the image in the browser only.
```

**Check:** on your phone the upload button opens the camera roll, the preview appears, Kirim is only enabled after a photo is chosen.

---

### A5. Waiting screen

```
After pressing Kirim on /quiz/foto, go to /quiz/selesai showing:

Heading: Lagi kami siapkan
Text: Panduan gaya kamu lagi disusun. Biasanya selesai dalam 15 menit dan kami kirim ke email kamu.

Add an email input above the Kirim button on the photo page, required, so we have somewhere to send it. Do not send anything yet.
```

**Check:** an invalid email is rejected, and you land on the waiting screen.

---

### A6. The report page, with fake content

```
Create a page at /laporan/contoh showing an example style report in Bahasa Indonesia. Use hardcoded placeholder content, no AI, no database.

Sections in this order:
- Palet warna kamu — five colour swatches with names
- Bentuk wajah — one short paragraph
- Formula outfit untuk resepsi sore — three or four lines
- Rekomendasi item — five items, each with a name, a price in rupiah, and a Lihat link that goes nowhere
- Hindari ini — three bullet points
- Catatan rambut dan hijab — one short paragraph

Make it read like a real report someone paid for. Phone first.
```

**Check:** this is the one that matters. Would you pay Rp 39.000 for this layout if the content were real? If not, say what is missing before going further.

---

### A7. Mobile pass

```
Go through the landing page, all six quiz steps, the photo page, the waiting page and /laporan/contoh on a narrow phone screen. Fix anything cramped, overflowing, too small to tap, or with text running under the notch. Do not redesign anything, only fix what is broken at that width.
```

**Check:** every page on your actual phone, not a desktop browser shrunk down.

---

### A8. Findable on Google

```
Add page titles and meta descriptions in Bahasa Indonesia to every page, targeting people searching for what to wear to a wedding in Indonesia. Home page title should target the phrase "outfit kondangan". Also add a proper favicon and an Open Graph image so links look right when shared on WhatsApp.
```

**Check:** share the link to yourself on WhatsApp and see whether the preview card looks right.

---

## After Phase A

You have a complete, clickable product with fake content. Now the signups start, one per phase, so nothing is blocked waiting on a verification email.

| Phase | What it adds | What you need to sign up for first |
|---|---|---|
| **B** | Real AI report from the selfie and answers | Google AI Studio key (you have one). Move to pay-as-you-go before real users, free tier may train on your prompts. |
| **C** | Saving answers, emailing the report | A database (Neon or Supabase, free) and your own Brevo account, separate from Nakula's |
| **D** | Taking money | Xendit. Start this early, business verification is slow. |
| **E** | Content that ranks | Nothing. This is writing, and it is your actual edge. |

Start the Xendit signup during Phase A, not Phase D. It is the only step where someone else's timeline blocks you.

---

## Three jobs never to give the agent

From `../Agent Control Plane/Operating_Model.md`, made concrete for this product:

**1. Anything that sets a price.** Set Rp 39.000 in Xendit's dashboard, never in code. An agent cannot get a number wrong that it never touches.

**2. Deleting the selfie.** The agent can write it. You test it by hand, every single release: upload a photo, wait for the report, confirm the file is gone. Ninety seconds. This is the one that can end the product.

**3. Anything on the live site once people are paying.** Branch, preview, test, ship. No "quick fix" straight to main.

---

## When a job goes wrong

Three attempts, then stop and bring it to me. Past that the agent is guessing.

The most common failure is a job that was too big. If you find yourself writing more than about six lines, split it. "Build the quiz" fails. "Add one question with four options" works.

---

## A note on the Bahasa

I wrote the copy above, and I am not a native speaker. It is grammatically fine but the tone may be stiffer than you want for a 25-year-old audience. Change it freely before pasting. You are the one who knows whether "Bingung mau pakai apa ke kondangan?" sounds right or sounds like a bank advert.
