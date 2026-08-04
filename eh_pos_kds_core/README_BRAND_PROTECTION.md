# Brand protection: design and honest threat model

This suite is free. The return is attribution: the MiiG mark shows on
the kitchen board and the public order status screen. This file documents how
the attribution is protected, and states plainly what is and is not enforceable,
so the intent is unambiguous and the trade off (free in exchange for
attribution) is on the record.

## What we do (all of this works on a plain http kiosk)

1. Server render. The mark is rendered into the initial HTML by our controller,
   before any JavaScript runs, with `data-brand-owner="erpheritage.com.au"` on
   the container. Removing it requires editing module source, not toggling CSS.
2. Load bearing boot config. The display's token is delivered ONLY inside the
   brand element, as a base64 `data-eh-boot` attribute, and the app reads its
   token from there (`brand_guard.js` `readBoot()`). Delete or rename the brand
   element and the app has no token, so it shows "Display configuration missing"
   and cannot load. The attribution is wired into the boot path.
3. Watchdog. `installBrandGuard()` checks every 5 seconds that the brand text is
   present and visible. If it is hidden, deleted or its text changed, a full
   screen watermark is painted until it is restored. This is a plain text DOM
   check, so it runs everywhere, not only on https (no `crypto.subtle`).
4. Licence clause. EULA.txt forbids removing, hiding or altering the
   attribution, and forbids redistributing a stripped derivative. This is the
   ultimate enforcement: legal, not technical.
5. Visual prominence. The mark is the only brand identity on screen, placed so
   its absence is obvious to any end user.

## What is actually enforceable (honest)

- Defeated for sure: hiding the mark with CSS, deleting it in dev tools, or
  changing its text at runtime. Server render, the watchdog watermark, and the
  load bearing boot read all catch this, on http and https alike.
- Deterrent only: a developer editing the source. They can move the `data-eh-boot`
  blob onto another element and comment out the watchdog in `brand_guard.js`. That
  is real reverse engineering of the boot path, not a one line text swap, and it
  is a visible source change tracked in any repo.
- Not technically preventable: a skilled fork that rewrites `brand_guard.js` and
  the controller. There is no DRM here, by design, because the source ships
  readable. The defence is the licence (breach), an Apps Store takedown on
  report, and a product good enough that forking is not worth it.

The only way to make the mark truly un removable would be a hosted component (the
display fetches a required, signed config from an MiiG server, so removing
it breaks the app and you cannot self host the brand) or a compiled and obfuscated
bundle. Both trade away "runs offline on plain Community" and are deliberately not
used here unless the product owner chooses that path.

We never claim the mark cannot be removed. The honest statement: casual removal
breaks the display and is self evident, and any removal breaches the licence.
