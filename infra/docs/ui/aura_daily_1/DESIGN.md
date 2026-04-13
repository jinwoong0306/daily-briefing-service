# Design System Document: Editorial Clarity & Tonal Depth

## 1. Overview & Creative North Star: "The Modern Curator"
This design system moves away from the cluttered, "noisy" interface of traditional news aggregators. The Creative North Star is **The Modern Curator**—an experience that feels less like a digital feed and more like a premium, high-end printed journal delivered to a glass screen.

To break the "template" look, we utilize **Intentional Asymmetry**. Rather than a rigid, centered grid, we lean into generous white space and overlapping elements. Headlines should breathe, and content should feel like it is floating on a series of layered, high-quality papers. We prioritize legibility through aggressive typographic scale and tonal depth rather than structural lines.

---

## 2. Colors & Surface Architecture
The palette is rooted in a "Morning Freshness" philosophy—bright, crisp, and authoritative.

### The "No-Line" Rule
To maintain a premium feel, **1px solid borders are strictly prohibited** for sectioning content. Visual boundaries must be achieved through:
- **Tonal Shifts:** Placing a `surface-container-low` card against a `surface` background.
- **Generous Negative Space:** Using the Spacing Scale (specifically `8` to `12`) to create mental groupings.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of materials. 
- **Base Layer:** `surface` (#f9f9f9).
- **Secondary Sections:** `surface-container-low` (#f3f3f3) for subtle grouping.
- **Interactive Cards:** `surface-container-lowest` (#ffffff) to create a "lifted" appearance of pure white on off-white.

### The "Glass & Signature" Rule
For top navigation bars or floating action buttons, use **Glassmorphism**. Apply `surface-container-lowest` at 80% opacity with a `20px` backdrop-blur. 
For primary CTAs or high-importance news categories, use a **Signature Gradient**: Transitioning from `primary` (#000666) to `primary_container` (#1a237e) at a 135-degree angle. This adds "soul" and dimension that flat hex codes cannot provide.

---

## 3. Typography: Editorial Authority
We use a dual-sans-serif approach to create a sophisticated hierarchy. **Manrope** provides a modern, geometric character for displays, while **Inter** ensures maximum readability for long-form consumption.

*   **Display & Headlines (Manrope):** Use `display-lg` and `headline-lg` for lead stories. The high contrast between these and the body text signals importance instantly.
*   **Body & Titles (Inter):** `body-lg` is our workhorse. We utilize a line-height of 1.6x the font size to ensure "Morning Freshness" translates to eye comfort.
*   **Labels (Inter):** Use `label-md` in all-caps with `0.05rem` letter spacing for metadata (e.g., "5 MIN READ" or "WORLD NEWS").

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are often a crutch for poor layout. In this system, depth is earned through tone.

*   **The Layering Principle:** Stack `surface-container-lowest` on top of `surface-container-high` to create a natural, shadowless lift.
*   **Ambient Shadows:** Where a floating effect is vital (e.g., a "Read More" sticky button), use an extra-diffused shadow: `Y: 8px, Blur: 24px, Color: rgba(26, 28, 28, 0.06)`. This mimics natural morning light.
*   **The "Ghost Border" Fallback:** If a container lacks contrast against a background, use a "Ghost Border": `outline-variant` at **15% opacity**. Never use 100% opacity lines.
*   **Rounding:** All primary containers and cards must use `xl` (1.5rem / 24px) or `lg` (1rem / 16px) corner radii to maintain a soft, approachable aesthetic.

---

## 5. Components & Primitives

### Cards & News Feed
*   **Constraint:** Forbid divider lines between news items.
*   **Implementation:** Use vertical spacing `8` (2.75rem) between items. Use `surface-container-lowest` cards with `xl` rounding for "Featured" stories, and simple typographic stacks for "Standard" stories.

### Buttons
*   **Primary:** Signature Gradient (Primary to Primary Container) with `full` rounding. White text.
*   **Secondary:** `surface-container-highest` background with `on_surface` text. No border.
*   **Tertiary:** Ghost style; text-only using `primary` color, strictly for low-emphasis actions like "Dismiss."

### Input Fields
*   **Style:** `surface-container-low` fill with an `xl` corner radius. 
*   **Focus State:** Transition the "Ghost Border" from 15% opacity to 100% `primary` color. No heavy "glow" effects.

### Chips (Category Filters)
*   **Unselected:** `surface-container-high` background, `on_surface_variant` text.
*   **Selected:** `primary` background, `on_primary` text. Use `full` rounding (pill shape).

---

## 6. Do's and Don'ts

### Do
*   **Do** use asymmetrical image cropping (e.g., a 4:5 aspect ratio for lead images) to feel more like a magazine than an app.
*   **Do** prioritize the `primary_fixed_dim` and `secondary_fixed` tokens for Dark Mode to ensure the "Deep Blue" remains sophisticated and doesn't vibrate against dark grays.
*   **Do** use `surface_bright` for the "Freshness" feel in Light Mode.

### Don't
*   **Don't** use pure black (#000000). Always use `on_surface` (#1a1c1c) for text to maintain a high-end ink-on-paper feel.
*   **Don't** use standard 1px dividers. If you feel the need for a line, increase the spacing token by one level instead.
*   **Don't** crowd the edges. Maintain a minimum horizontal padding of `6` (2rem) across all screens to ensure the content feels "curated" and not "stuffed."