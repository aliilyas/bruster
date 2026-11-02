# Bruster — Relay identity

Relay combines a forward-leaning lowercase **b** with an uppercase **R** in its
negative space. The ten-degree lean expresses motion; the broad silhouette and
open counter keep the mark compact. This is the selected **01 / Relay** design.

## Assets

| Asset | Use |
| --- | --- |
| [`logo.svg`](logo.svg) / [`logo.png`](logo.png) | Coral mark; transparent 512×512 PNG |
| [`logo-black.svg`](logo-black.svg) / [`logo-white.svg`](logo-white.svg) | Single-color reproduction |
| [`wordmark.svg`](wordmark.svg) | Outlined horizontal lockup for light backgrounds |
| [`wordmark-dark.svg`](wordmark-dark.svg) | Peach/paper horizontal lockup for dark backgrounds |
| [`avatar.svg`](avatar.svg) / [`avatar.png`](avatar.png) | Padded 512×512 profile picture; supports circular cropping |
| [`favicon.svg`](favicon.svg) | Adaptive coral/peach browser icon for light/dark browser chrome |
| [`favicon.ico`](favicon.ico) / [`favicon-32.png`](favicon-32.png) | 16/32/48 px ICO and 32 px PNG fallback |
| [`apple-touch-icon.png`](apple-touch-icon.png) | 180×180 touch icon on warm paper |
| [`social.png`](../site/assets/social.png) | 1200×630 website and GitHub social preview |

The website uses the outlined wordmark in its header and footer. The GitHub
README selects the matching light/dark lockup. For a GitHub repository social
preview upload, use `site/assets/social.png` in the repository's settings.

## Palette and type

| Role | Color |
| --- | --- |
| Coral / light-background mark | `#c6402b` |
| Coral hover | `#a53220` |
| Peach / dark-background mark | `#ff956f` |
| Wordmark ink | `#261c18` |
| Warm paper | `#faeee5` |

The wordmark is **Liberation Sans Bold Italic**, optically spaced at -20/1000 em
and converted to SVG paths. Liberation Fonts are licensed under
[SIL Open Font License 1.1](https://github.com/liberationfonts/liberation-fonts/blob/main/LICENSE).
The shipped logo and wordmark SVGs have no font or external-image dependencies.
The editable social SVG uses Liberation Sans and DejaVu Sans/Mono for its text;
the exported PNG is self-contained.

## Usage

- Keep the original proportions, lean, and b/R counterform.
- Leave clear space of at least one outer-stem width: 44 units on the 256-unit
  symbol canvas, or about one fifth of its visible height.
- Prefer 24 px or larger for the mark. At 16 px, the b silhouette leads and the
  internal R is subtler. Use the supplied favicon for that context.
- Use the horizontal lockup at 128 px wide or larger.
- Use `avatar.png` for circular crops; its extra padding protects the silhouette.
- Use the white mark or dark-background wordmark on dark surfaces.
- Avoid stretching, adding effects, or separately repositioning the inner R.

`logo.svg` is the canonical symbol geometry. The monochrome marks, wordmarks,
avatar, favicon and social source embed that exact path and lean transform.
Keep those copies synchronized when making an intentional geometry change.

## Raster exports

With librsvg and Pillow installed:

```sh
rsvg-convert -w 512 -h 512 assets/logo.svg -o assets/logo.png
rsvg-convert -w 512 -h 512 assets/avatar.svg -o assets/avatar.png
rsvg-convert -w 32 -h 32 assets/logo.svg -o assets/favicon-32.png
rsvg-convert -w 180 -h 180 assets/avatar.svg -o assets/apple-touch-icon.png
rsvg-convert site/assets/social.svg -o site/assets/social.png
python3 -c 'from PIL import Image; Image.open("assets/logo.png").save("assets/favicon.ico", sizes=[(16,16),(32,32),(48,48)])'
```
