# Design System Document: The Editorial Precision Framework

## 1. Overview & Creative North Star: "The Digital Curator"
This design system is engineered to transform a standard news feed into a high-end, bespoke editorial experience. Our Creative North Star is **The Digital Curator**. Unlike generic news aggregators that rely on dense grids and heavy borders, this system treats information as a premium asset. 

We break the "template" look through **Intentional Asymmetry**—using white space as a structural element rather than a void. By leveraging high-contrast typography scales and overlapping "sheet" layering, we create a sense of depth and authority. The goal is a "quiet" interface that feels expensive, trustworthy, and surgically clean.

---

## 2. Colors & Tonal Depth
While the primary brand anchor is `#0064FF`, the soul of the system lies in its neutrals. We utilize a sophisticated palette of off-whites and cool grays to define hierarchy without ever resorting to a 1px line.

### The "No-Line" Rule
**Explicit Instruction:** Designers are prohibited from using 1px solid borders for sectioning content. Boundaries must be defined solely through:
1.  **Background Color Shifts:** Placing a `surface-container-low` (#f3f3f4) card on a `surface` (#f9f9f9) background.
2.  **Vertical Whitespace:** Utilizing the 8 (2.75rem) or 10 (3.5rem) spacing tokens to signal a change in context.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of fine vellum paper.
*   **Base:** `surface_container_lowest` (#ffffff) for the primary reading canvas.
*   **Secondary Content:** `surface_container_low` (#f3f3f4) for inset "briefing" modules.
*   **Elevated Highlights:** `surface_bright` (#f9f9f9) for floating navigation bars with backdrop blurs.

### The Glass & Gradient Rule
To prevent a "flat" or "cheap" appearance, main CTAs and Hero Headlines should utilize a subtle **Signature Texture**. Instead of a flat `#0064FF`, apply a linear gradient from `primary_container` (#0064ff) to `primary` (#004ecb) at a 135° angle. This adds "visual soul" and a sense of professional polish.

---

## 3. Typography: The Manrope Scale
We use **Manrope** exclusively. Its geometric yet humanist qualities provide the "Trustworthy" vibe requested.

*   **The Power of Scale:** To achieve a premium look, we pair `display-md` (2.75rem) headlines with `label-md` (0.75rem) metadata. This extreme variance creates an "editorial" feel common in high-end magazines.
*   **Headline-LG (2rem):** Used for top-tier news stories. Tracking should be set to -2% for a tighter, more authoritative presence.
*   **Body-LG (1rem):** The workhorse for article summaries. Line height must be generous (1.6x) to ensure the "minimal and clean" promise is kept.
*   **Title-SM (1rem, Bold):** Used for section headers to provide a clear anchor point for the eye.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are too "software-like." This system uses **Ambient Shadows** and **Tonal Layering**.

*   **The Layering Principle:** Depth is achieved by stacking. Place a `surface_container_lowest` (#ffffff) card on a `surface_container` (#eeeeee) background to create a soft, natural lift.
*   **Ambient Shadows:** If a floating element (like a FAB or Popover) is required, use a shadow with a blur of 32px and 4% opacity, using the `on_surface` (#1a1c1c) color. It should feel like a soft glow, not a dark smudge.
*   **The "Ghost Border" Fallback:** If accessibility requires a container edge, use the `outline_variant` (#c2c6d8) at **15% opacity**. This creates a hint of an edge that disappears into the white space.

---

## 5. Components

### Primary Actions (Buttons)
*   **Style:** Pill-shaped (`rounded-full`).
*   **Color:** `primary_container` (#0064ff) with a subtle 2px inner-glow gradient.
*   **Padding:** 1rem vertical, 2rem horizontal.
*   **Interaction:** On hover, shift to `on_primary_fixed_variant` (#003ea6). No shadows on hover; use a slight scale-up (1.02x).

### News Cards & Lists
*   **Card Design:** Forbid divider lines. Use `surface_container_low` as a background for the card, or simply use whitespace.
*   **Visual Anchor:** Every card should have a 4px vertical "accent bar" of `primary` color on the far left to denote "Unread" status, rather than a heavy border.

### Search & Input Fields
*   **Style:** "Ghost" style. No bottom line or box. Use `surface_container_highest` (#e2e2e2) as a subtle background fill with `rounded-md` (0.375rem).
*   **Text:** Use `on_surface_variant` (#424656) for placeholder text to maintain a soft contrast.

### The "Daily Progress" Component (App Specific)
*   A custom progress bar at the top of the feed using a gradient of `primary` to `tertiary`. It should be thin (2px) and sit flush against the top of the viewport to act as a "reading thread."

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use asymmetrical margins. For example, a 1.4rem (4) left margin and a 2.75rem (8) right margin for headline text to create an editorial "ragged" look.
*   **Do** use `primary` (#004ecb) for links and small highlights only. Let the white background dominate.
*   **Do** use `surface_container_lowest` (#ffffff) for the main reading area to ensure maximum legibility.

### Don’t:
*   **Don’t** use black (#000000). Use `on_surface` (#1a1c1c) for all primary text to reduce eye strain.
*   **Don’t** use standard "Grey" shadows. Always tint shadows with the primary or surface color.
*   **Don’t** use 1px dividers between news items. Use a `1.4rem` (4) gap of white space instead.
*   **Don’t** use "Alert Red" for everything. Use `tertiary` (#a03200) for breaking news to maintain a professional, sophisticated tone rather than an alarmist one.