# Design System Specification: Editorial Clarity & Tonal Depth

## 1. Overview & Creative North Star: "The Digital Lithograph"
This design system rejects the "templated" look of modern SaaS in favor of a high-end editorial experience. Our Creative North Star is **The Digital Lithograph**—a philosophy where the UI feels like a premium print publication brought to life through light and layering.

We move beyond the rigid grid by embracing **Intentional Asymmetry**. By using generous white space (referencing our `spacing-24` and `spacing-20` tokens) and overlapping elements, we create a sense of curated motion. The goal is "Editorial Clarity": information is not just displayed; it is composed. We prioritize tonal depth over structural lines, ensuring the interface feels atmospheric and immersive rather than boxed-in.

---

## 2. Colors & The Chromatic Experience
The palette is anchored by a vibrant, high-energy Primary Blue (`#0064FF`), balanced against a sophisticated spectrum of periwinkle-tinted neutrals.

### Surface Hierarchy & Nesting
We utilize a "Physical Layering" model. Instead of flat layouts, treat the UI as stacked sheets of fine paper or frosted glass.
*   **Base:** `surface` (`#f8f5ff`) acts as the canvas.
*   **Depth:** Use `surface-container-low` (`#f1efff`) for large secondary regions.
*   **Focus:** Use `surface-container-lowest` (`#ffffff`) for cards or high-priority modules to create a "lifted" effect against the tinted background.

### The "No-Line" Rule
**Strict Mandate:** Prohibit 1px solid borders for sectioning. Boundaries must be defined solely through background color shifts. A `surface-container-high` (`#e0e0ff`) element sitting on a `surface` background creates a clean, sophisticated edge that a border would only clutter.

### Signature Textures (Glass & Gradient)
To achieve a "signature" look, main CTAs and Hero sections should utilize **The Aura Gradient**: a subtle transition from `primary` (`#0051d2`) to `primary-container` (`#7a9dff`) at a 135-degree angle. For floating navigation or overlays, apply **Glassmorphism**: 
*   **Fill:** `surface` at 70% opacity.
*   **Effect:** 20px Backdrop Blur.
*   **Result:** The background colors bleed through, softening the interface.

---

## 3. Typography: The Manrope Scale
We use **Manrope** exclusively. Its geometric yet humanist qualities allow it to function as both an authoritative headline face and a highly legible functional font.

*   **Display (lg/md/sm):** Used for "Hero" moments. Use `display-lg` (3.5rem) with tighter letter-spacing (-0.02em) to create a bold, editorial impact.
*   **Headlines:** `headline-lg` (2rem) should be used for section starters, paired with generous `spacing-8` margins below.
*   **The Narrative Body:** `body-lg` (1rem) is our standard for reading. Always ensure a line height of 1.6 for maximum clarity.
*   **Functional Labels:** `label-md` (0.75rem) in `on-surface-variant` (`#555881`) provides a quiet, professional hierarchy for metadata.

---

## 4. Elevation & Depth: Tonal Layering
Traditional drop shadows are largely replaced by **Tonal Layering**.

*   **The Layering Principle:** Stacking `surface-container-lowest` on `surface-container-low` creates a soft, natural lift without the "dirty" look of grey shadows.
*   **Ambient Shadows:** If a floating element (like a FAB or Popover) requires a shadow, use a "Tinted Shadow." 
    *   *Recipe:* Color: `on-surface` (`#282b51`) at 6% opacity, Blur: 32px, Y-Offset: 16px.
*   **The "Ghost Border" Fallback:** If accessibility requires a stroke (e.g., high-contrast mode), use a "Ghost Border": `outline-variant` (`#a7aad7`) at 15% opacity. Never use 100% opaque borders.

---

## 5. Component Guidelines

### Buttons (The Kinetic Signature)
*   **Primary:** Fill with `primary` (`#0051d2`) or the "Aura Gradient." Text is `on-primary`. Corner radius is fixed at `ROUND_EIGHT` (0.5rem).
*   **Secondary:** Fill with `secondary-container` (`#cbceff`). This provides a softer, periwinkle alternative that doesn't compete with the primary action.
*   **Tertiary:** No fill, no border. Use `primary` text color. Use only for low-emphasis actions.

### Cards & Lists (The Borderless Container)
*   **Structure:** Cards must never have a border. Use `surface-container-lowest` and an ambient shadow or a shift to `surface-container-low` to define the shape.
*   **Dividers:** Forbid the use of 1px divider lines. Separate list items using `spacing-1.5` (0.5rem) of vertical white space or alternating subtle background tints.

### Inputs & Interaction
*   **Fields:** Background should be `surface-container-highest` (`#d9daff`) with a `label-sm` floating above it. 
*   **Focus State:** A 2px glow using `primary` at 30% opacity. No harsh black outlines.
*   **Chips:** Use `secondary-fixed-dim` (`#babfff`) for unselected states and `primary` for selected states to create a vibrant "pop" of color.

---

## 6. Do's and Don'ts

### Do:
*   **Do** use asymmetrical spacing (e.g., more padding on the left than the right) to create editorial rhythm.
*   **Do** leverage the `tertiary` (`#8d3a8a`) accents for "Discovery" or "New" badges to provide a sophisticated color counterpoint to the blue.
*   **Do** treat white space as a functional element, not "empty" space.

### Don't:
*   **Don't** use 1px solid borders to separate sections.
*   **Don't** use pure black (#000000) for text. Always use `on-surface` (`#282b51`) for better tonal depth.
*   **Don't** use default Material Design shadows. They are too "heavy" for this system; keep shadows tinted and diffused.
*   **Don't** cram content. If in doubt, increase the spacing token by one level (e.g., from `spacing-4` to `spacing-5`).