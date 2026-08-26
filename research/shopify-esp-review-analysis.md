# Shopify ESP Review Research: LTV.ai Campaign Angles

**Revision note:** This replaces the earlier draft, which used one generic complaint list
repeated across every ESP. Per direction, this version gives each ESP its own distinct,
sourced problem, filtered to what's actually relevant to LTV.ai, not every complaint reviewers
raise, only the ones a set of AI agents running proactivity, segmentation, and deliverability
actually addresses.

**What LTV.ai is, for reference:** a set of AI agents that runs a brand's email (and SMS)
program end to end: studying data, generating campaign ideas, designing and writing them,
building the audience, sending, and learning from each send. Three product hooks, each its own
cadence: **Proactivity** (agents build about 5 ready campaigns overnight, filling calendar gaps
and catching windows a team would miss), **Segmentation** (an Audience Agent auto-picks the
best of seven strategies per campaign), **Deliverability** (ISP-specific rendering and send
timing, optimized for the primary inbox, not just "sent"). Klaviyo gets separate treatment:
campaigns send through the brand's existing Klaviyo account, positioned as an add-on, not a
replacement.

Each ESP below gets **one** problem, the one with the strongest evidence and the tightest
link to a hook, not a shared checklist.

---

## Klaviyo: the inbox-placement blind spot

**The problem:** Klaviyo's own community and help center openly document that a large share of
campaign sends land in Gmail's Promotions tab rather than Primary, and that Klaviyo itself
doesn't give real-time visibility into DNS health, inbox placement, or blocklist status.
Merchants are pointed to third-party seed-list tools (e.g. GlockApps) to even find out. Gmail
also enforces hard thresholds (0.1% spam-complaint target, 0.3% block risk) that most merchants
have no live signal on inside Klaviyo.

This isn't a "Klaviyo is bad" story, it's a strong, well-run tool with a structural blind spot:
it optimizes for send, not for where the send lands.

**Why it matters to LTV.ai:** maps directly to the Deliverability hook, ISP-specific rendering
and per-customer send timing built to optimize for the primary inbox, not just delivery. It
also pairs naturally with the Klaviyo positioning: the brand keeps Klaviyo and its sending
reputation exactly as is, nothing to migrate. The angle is "your campaigns already go out, the
question is whether they're being seen," not a switch pitch.

**Sources:**
- [Klaviyo Community, daily campaign emails landing in Promotions tab](https://community.klaviyo.com/analytics-and-deliverability-72/seeking-advice-daily-campaign-emails-landing-in-promotions-tab-10687)
- [Klaviyo Help Center, email deliverability FAQs](https://help.klaviyo.com/hc/en-us/articles/16425927010075)
- [Klaviyo Help Center, troubleshooting why emails go to spam](https://help.klaviyo.com/hc/en-us/articles/12034571748251)
- [Klaviyo Community, enhancing email deliverability](https://community.klaviyo.com/marketing-30/how-can-we-enhance-email-deliverability-15952)

---

## Omnisend: segmentation without a predictive layer

**The problem:** Independent comparisons (built from user experience and reviews, not vendor
copy) consistently land on the same verdict: Omnisend covers the core ecommerce journeys and is
faster to set up, but its segmentation is rule-based and comparatively shallow, it doesn't
reach predictive depth like expected next order date, churn risk, or lifetime-value tiering.
Merchants trade segmentation granularity for simplicity and multichannel coverage in one tool.

**Why it matters to LTV.ai:** maps directly to the Segmentation hook. The Audience Agent
auto-selects from seven strategies per campaign, including purchase frequency, AOV tier, and
category affinity, which is exactly the behavioral/predictive layer Omnisend reviewers say is
missing. The angle isn't "Omnisend's segmentation is broken," it's "your list is being split by
static rules someone set once, not by who's actually about to buy, churn, or spend more."

**Sources:**
- [Omnisend vs Klaviyo, Maestra comparison](https://maestra.io/blog/comparisons/klaviyo-vs-omnisend)
- [Omnisend vs Klaviyo, Hustler Marketing verdict](https://www.hustlermarketing.com/klaviyo-vs-omnisend-which-email-sms-platform-wins-for-ecommerce/)
- [Omnisend vs Klaviyo, onsaas.me testing writeup](https://www.onsaas.me/blog/omnisend-vs-klaviyo)

---

## Postscript: sends that fail silently

**The problem:** Reviews describe a reliability gap specific to Postscript: automations that
either fail to send or send in error, and cases where merchants report being billed while
messages weren't actually delivered, with slow support follow-up on the billing side. This is
a different failure mode than Klaviyo's (which sends reliably but lands in the wrong tab),
Postscript's issue is trusting that the send happened at all.

**Why it matters to LTV.ai:** maps to the Deliverability hook, but on the reliability axis
rather than inbox-placement, per-customer send timing and delivery optimization matter more,
not less, on SMS, where there's no "Promotions tab" fallback: a failed send is just gone. The
angle is "you're paying for messages your customers never see, with no visibility into which
ones."

**Sources:**
- [Postscript Shopify App Store reviews](https://apps.shopify.com/postscript-sms-marketing/reviews)
- [Postscript alternatives roundup, txtcartapp](https://txtcartapp.com/blog/best-postscript-alternatives-for-shopify-sms-marketing/)
- [Postscript Capterra profile](https://www.capterra.com/p/199013/Postscript/)

---

## Attentive: a cost structure that rations the calendar

**The problem:** The most consistent complaint pattern for Attentive isn't feature depth, it's
commercial: undisclosed pricing (demo-and-negotiate rather than published rates), a base fee
plus per-message charges, and 6 to 12 month minimum commitments, sometimes with exclusivity
clauses. Layered on top, reported revenue frequently doesn't reconcile with Shopify or GA4, with
limited attribution-window customization. The combined effect reviewers describe: teams get
conservative about how often they send, because every additional campaign has a negotiated,
opaque cost attached, and they can't fully trust the numbers that would justify sending more.

**Why it matters to LTV.ai:** maps to the Proactivity hook, from the opposite direction than
Klaviyo/Postscript. Those two ESPs' merchants are sending but not landing or not delivering,
Attentive's cost structure pushes merchants toward under-sending: calendar gaps, skipped
slow-week campaigns, missed windows. The angle is "the gaps in your calendar aren't a strategy
problem, they're a cost-avoidance habit." That's exactly what an overnight agent filling
calendar gaps and catching windows (a competitor move, a restock, an underused day) is built to
counter.

**Sources:**
- [Attentive Capterra reviews](https://www.capterra.com/p/179576/Attentive/reviews/)
- [Attentive Reviews, SoftwareReviews](https://www.softwarereviews.com/products/attentive?c_id=273)
- [Attentive Alternatives, Ringly](https://www.ringly.io/blog/attentive-alternatives)

---

## Segment definition (who this research should turn into a list)

Not "anyone using one of these four apps," that's too broad and reads as a mass competitor
blast, which is explicitly the wrong play. Match the ESP-specific signal:

- **Klaviyo:** brands with visible send volume but detectable Promotions-tab/engagement patterns
  (seed-inbox behavioral signal, this is already a specced play).
- **Omnisend:** smaller/multichannel Shopify brands where Omnisend is the whole stack (not
  paired with a separate CDP/segmentation tool).
- **Postscript:** brands running SMS at meaningful volume (detectable send cadence) where
  reliability complaints are more likely to bite.
- **Attentive:** brands on Attentive with visibly sparse or bursty campaign cadence, long gaps
  between sends, activity clustered only around major sale dates, which is the observable
  fingerprint of "rationing the calendar."

## Guardrails for whoever turns this into copy

Per the brand copy rules: no em-dashes, no "helps/empowers/enables/our AI," never say "we
replace your ESP" (Klaviyo copy must state sends go through the brand's existing Klaviyo,
nothing to migrate), fight the manual workflow, not the named competitor, don't invent or
imply per-send pricing, and remember LTV.ai runs **campaigns only, never flows**: none of the
four angles above should be built into a cart-abandon, welcome-flow, or post-purchase play.
