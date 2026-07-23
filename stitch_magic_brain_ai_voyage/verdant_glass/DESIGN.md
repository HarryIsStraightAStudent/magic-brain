---
name: Verdant Glass
colors:
  surface: '#faf9f3'
  surface-dim: '#dbdad4'
  surface-bright: '#faf9f3'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f4ee'
  surface-container: '#efeee8'
  surface-container-high: '#e9e8e2'
  surface-container-highest: '#e3e3dd'
  on-surface: '#1b1c19'
  on-surface-variant: '#3d4a3d'
  inverse-surface: '#30312d'
  inverse-on-surface: '#f2f1eb'
  outline: '#6d7b6c'
  outline-variant: '#bccbb9'
  surface-tint: '#006e2f'
  primary: '#006e2f'
  on-primary: '#ffffff'
  primary-container: '#22c55e'
  on-primary-container: '#004b1e'
  inverse-primary: '#4ae176'
  secondary: '#1f6c3a'
  on-secondary: '#ffffff'
  secondary-container: '#a4f1b2'
  on-secondary-container: '#24703e'
  tertiary: '#55615a'
  on-tertiary: '#ffffff'
  tertiary-container: '#a2afa7'
  on-tertiary-container: '#37433c'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#6bff8f'
  primary-fixed-dim: '#4ae176'
  on-primary-fixed: '#002109'
  on-primary-fixed-variant: '#005321'
  secondary-fixed: '#a6f4b5'
  secondary-fixed-dim: '#8bd79b'
  on-secondary-fixed: '#00210b'
  on-secondary-fixed-variant: '#005226'
  tertiary-fixed: '#d9e6dd'
  tertiary-fixed-dim: '#bdcac1'
  on-tertiary-fixed: '#131e19'
  on-tertiary-fixed-variant: '#3e4943'
  background: '#faf9f3'
  on-background: '#1b1c19'
  surface-variant: '#e3e3dd'
typography:
  headline-xl:
    fontFamily: Manrope
    fontSize: 48px
    fontWeight: '800'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Manrope
    fontSize: 32px
    fontWeight: '700'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Manrope
    fontSize: 28px
    fontWeight: '700'
    lineHeight: 36px
  headline-md:
    fontFamily: Manrope
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  body-lg:
    fontFamily: Manrope
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Manrope
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Manrope
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.01em
  label-sm:
    fontFamily: Manrope
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 8px
  container-max: 1280px
  gutter: 24px
  margin-mobile: 16px
  margin-desktop: 40px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style

This design system is built upon the concept of "Organic Tech"—a fusion of high-precision technology and the restorative safety of nature. By pivoting from warm ambers to a spectrum of fresh greens and creamy whites, the brand evokes feelings of vitality, growth, and clarity. 

The aesthetic is anchored in **Glassmorphism**, specifically a "liquid glass" execution. Surfaces feel like polished, translucent membranes that catch the light, creating a UI that is both ethereal and structurally sound. The target audience values innovation but seeks an environment that feels approachable and non-threatening. The emotional response is one of "High-Tech Serenity"—fast, capable, but fundamentally calm and safe.

## Colors

The palette is strictly curated to eliminate all warmth derived from red or yellow wavelengths, replacing them with a "Warm Cream" base and "High-Tech Green" accents.

- **Primary Green (#22c55e):** A vibrant, high-energy green used for primary actions, success states, and key brand highlights.
- **Deep Forest Green (#166534):** Used for high-contrast text and grounding elements to ensure legibility.
- **Mint Tint (#f0fdf4):** A subtle, translucent green used for secondary surfaces and glass highlights.
- **Cream Base (#fdfcf6):** A soft, warm off-white that prevents the interface from feeling "hospital cold," maintaining the "safe" brand promise.
- **Glass White:** Pure white at varying opacities (10-40%) used for the liquid glass material.

## Typography

**Manrope** is the sole typeface for this design system, chosen for its modern, refined, and balanced characteristics. Its geometric foundation provides the "tech" feel, while its open counters and humanist touches provide the "warmth."

For headlines, we use tighter letter spacing and heavier weights to create impact against the ethereal glass backgrounds. Body text maintains generous line heights to ensure a relaxed reading experience. All labels are set with a slightly increased font weight to remain legible when placed over translucent or vibrant green surfaces.

## Layout & Spacing

The design system utilizes a **Fixed Grid** model for desktop to maintain the integrity of the glass compositions, while transitioning to a **Fluid Grid** for mobile.

- **Desktop:** A 12-column grid centered in a 1280px container. Large margins (40px) create a sense of breathability.
- **Mobile:** A 4-column grid with 16px margins. 
- **Spacing Rhythm:** Based on an 8px scale. Component internal padding should be generous (typically 16px or 24px) to emphasize the "liquid" and expansive feel of the surfaces. Elements should "float" within their containers rather than feeling cramped against edges.

## Elevation & Depth

Depth is conveyed through **Liquid Glass** material properties rather than traditional shadows.

1.  **Backdrop Blur:** All elevated surfaces (cards, modals, navigation bars) must apply a `backdrop-filter: blur(20px)`.
2.  **Translucent Tints:** Surfaces are filled with a semi-transparent white (`rgba(255, 255, 255, 0.4)`) or a soft mint green (`rgba(240, 253, 244, 0.6)`).
3.  **Glass Strokes:** Instead of shadows, use 1px inner borders (top and left) in a brighter, more opaque white to simulate a light source hitting the edge of a glass pane.
4.  **Green Glow:** High-priority elements (like active cards) may utilize a soft, diffuse green outer glow (`#22c55e` at 15% opacity) to signify focus without breaking the flat-glass aesthetic.

## Shapes

The shape language is "Organic Geometric." We avoid sharp corners to maintain the safe, approachable feel. 

Standard components use a **0.5rem (8px)** corner radius. Larger containers like cards use **1rem (16px)**, and major layout sections or modal overlays use **1.5rem (24px)**. This nesting of curves creates a soft, cohesive visual flow that mimics the appearance of liquid tension.

## Components

- **Buttons:** Primary buttons are solid **Vibrant Green (#22c55e)** with white text. Secondary buttons use a glass treatment (white translucent fill) with a green border and green text.
- **Glass Cards:** The signature component. These feature the 20px backdrop blur, a 1px soft white border, and are placed over a background that may have subtle organic green gradients to show off the refraction.
- **Inputs:** Fields are semi-transparent with a 1px border that turns solid Green on focus. Labels sit just above the glass surface in Forest Green.
- **Chips:** Small, pill-shaped elements with a soft Mint Green background and Deep Forest Green text. Used for filtering and categorization.
- **Selection Controls:** Checkboxes and radio buttons use the Primary Green for the "on" state. The "off" state is a simple glass-style ring.
- **Navigation:** Top bars and bottom sheets must be persistent "liquid glass" elements that blur the content passing beneath them, creating a sense of continuous space.