# Padanin Warna: Product analytics for a consumer AI app

**Role:** Independent product builder. I owned product scope, the customer journey, funnel measurement and release validation.

**Status:** Deployed consumer product with an Indonesian and English experience.

[Try the color quiz](https://padanin.shop/warna) · [View the sample styling guide (PDF)](https://padanin.shop/warna/warna-studio-sample.pdf)

## The decision

Padanin Warna gives visitors a free seasonal color result and offers a more detailed paid styling guide. I wanted to understand where customers stopped between seeing their free result and opening the paid guide. Each step has a different implication for the product: people may miss the offer, open checkout without proceeding, or need help completing payment.

## What I built

- **A visible offer.** I moved the result, price and unlock action into the initial mobile view and added a link to a full sample so customers could inspect the guide before deciding.
- **A funnel with distinct steps.** I tracked free results, price views, checkout starts, payment claims, approved orders and report opens. Approved orders came from server-side records. I separated internal and simulated activity from customer totals.
- **A way to compare releases.** I tagged the checkout version and set up a comparison of checkout starts per free result for traffic from the same acquisition source. Approved orders and revenue provided separate outcome checks.

## What I verified and learned

I checked the deployed Indonesian and English flows at narrow mobile widths using synthetic results and simulated checkout. The checks covered the sample guide, checkout state and recovery after a page reload. The 12 November release also passed 194 automated tests.

The new layout put the unlock action within the initial 320 × 680 viewport in the tested states. The tracking definition for a price view also changed with the release, so I used free results as the denominator for the comparison. The rollout had no concurrent control group. The release checks establish that the flow and instrumentation worked in the tested scenarios. A conversion-lift estimate would require more evidence.
