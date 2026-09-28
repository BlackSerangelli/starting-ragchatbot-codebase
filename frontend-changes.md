# Frontend Changes: Dark/Light Theme Toggle

Adds a sun/moon toggle button in the top-right corner that switches the UI between the existing dark theme and a new light theme.

## Files changed

### `frontend/index.html`
- Added an inline script in `<head>` (before the stylesheet) that sets `data-theme` on `<html>` from `localStorage` (`theme` key), falling back to the OS `prefers-color-scheme`. Running before first paint avoids a flash of the wrong theme.
- Added `<button id="themeToggle" class="theme-toggle">` as the first child of `<body>`, containing sun and moon SVG icons (`aria-hidden="true"`). It is a native `<button type="button">`, so it is reachable with Tab and activated with Enter/Space. It has an `aria-label` and `title`.
- Bumped cache-busters: `style.css?v=12`, `script.js?v=11`.

### `frontend/style.css`
- **New variables** (defined for both themes), replacing hardcoded colors:
  - `--code-bg`: inline code and `pre` backgrounds.
  - `--error-bg`, `--error-text`, `--error-border`: `.error-message`.
  - `--success-bg`, `--success-text`, `--success-border`: `.success-message`.
  - `--welcome-shadow`: shadow of the welcome message.
  - `--toggle-shadow`: shadow of the toggle button.
- **Light theme:** a `:root[data-theme="light"]` block overrides every color variable. The palette uses Tailwind slate/blue colors:

  | Variable | Value |
  |---|---|
  | `--background` | `#f8fafc` |
  | `--surface` | `#ffffff` |
  | `--surface-hover` | `#f1f5f9` |
  | `--text-primary` | `#0f172a` |
  | `--text-secondary` | `#475569` (about 7.5:1 on white) |
  | `--border-color` | `#cbd5e1` |
  | `--primary-color` | `#2563eb` (about 5.2:1 on white) |
  | error text | `#b91c1c` |
  | success text | `#15803d` |

  Text and primary colors meet WCAG AA contrast. The dark theme stays the default in `:root` and is unchanged.
- **`.theme-toggle` button:**
  - A fixed 40px circle at `top: 1rem; right: 1rem`, styled with the surface, border and text variables.
  - On hover it lifts and turns the primary color, like the send button.
  - With keyboard focus (`:focus-visible`) it shows the `--focus-ring` shadow.
  - The sun and moon icons are stacked and crossfade with a rotate and scale animation over 0.3s. The dark theme shows the sun ("switch to light"); the light theme shows the moon.
- **Smooth switching:** a temporary `html.theme-transition` class makes all elements animate `background-color`, `color`, `border-color` and `box-shadow` over 0.3s. It is applied only while the theme is switching, so the existing hover and transform transitions are not affected.
- **Reduced motion:** under `prefers-reduced-motion: reduce`, both the theme transitions and the icon transitions are turned off.
- **Bug fix:** `.message-content blockquote` used an undefined `var(--primary)`. It now uses `var(--primary-color)`.

### `frontend/script.js`
- New `themeToggle` DOM reference, with a click listener wired in `setupEventListeners()`.
- `toggleTheme()`:
  - Flips `document.documentElement.dataset.theme`.
  - Adds the `theme-transition` class for 300ms.
  - Saves the choice to `localStorage`, guarded with try/catch.
  - Updates the button label.
- `updateThemeToggleLabel()` keeps `aria-label` and `title` in sync ("Switch to light theme" / "Switch to dark theme"). It runs on load and after each toggle.
- `getCurrentTheme()` is a small helper that reads the current theme.
