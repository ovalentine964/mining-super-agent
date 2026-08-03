# Sovereign Resource DAO — App Icon Specifications

## Design Concept
A **stylized diamond/crystal** with circuit patterns inside, representing the intersection of natural mineral resources and blockchain/AI technology. The Africa continent outline is subtly embedded within the crystal facets.

## Symbolism
- **Diamond shape**: Mining, minerals, precious resources, value
- **Circuit patterns**: Technology, AI, digital infrastructure
- **Africa outline**: The continent, sovereignty, the miners being protected
- **Gold on dark blue**: Value (gold) on trust/technology (blue)

## Color Palette

| Color | Hex | Usage |
|-------|-----|-------|
| Brand Gold | `#8B6914` | Primary icon color, diamond body |
| Gold Light | `#A67B1E` | Highlight facets |
| Gold Dark | `#6B5010` | Shadow facets |
| Gold Highlight | `#C49A2A` | Shine/specular highlight |
| Dark Blue | `#1A1A2E` | Background, circuit lines |
| Dark Blue Light | `#2A2A48` | Background subtle elements |
| White | `#FFFFFF` | Text, contrast elements |

## Android Adaptive Icon

### Structure
- **Foreground**: Diamond crystal with circuit pattern (inset 25%)
- **Background**: Dark blue with subtle concentric circles and network nodes
- **Safe zone**: 66dp circle within 108dp canvas (72dp inner, 18dp outer padding)

### Files
| File | Purpose |
|------|---------|
| `drawable/ic_launcher_foreground.xml` | Vector: gold diamond + circuit + Africa |
| `drawable/ic_launcher_background.xml` | Vector: dark blue + network pattern |
| `mipmap-anydpi-v26/ic_launcher.xml` | Adaptive icon config |
| `values/colors.xml` | Brand color definitions |

## Icon Sizes (for rasterized fallbacks)

| Density | Size (px) | Usage |
|---------|-----------|-------|
| mdpi | 48×48 | Baseline |
| hdpi | 72×72 | 1.5× |
| xhdpi | 96×96 | 2× |
| xxhdpi | 144×144 | 3× |
| xxxhdpi | 192×192 | 4× |

> **Note**: With adaptive icons (API 26+), the vector drawable scales to all sizes. Rasterized PNGs are only needed for API < 26 fallback.

## Splash Screen
- Full dark blue background (`#1A1A2E`)
- Centered diamond logo (same design, larger)
- Subtle golden glow ring around diamond
- Brand text area below logo

## Visibility Checklist
- ✅ Recognizable at 48×48dp (simple diamond silhouette)
- ✅ Works on light backgrounds (dark blue provides contrast)
- ✅ Works on dark backgrounds (gold diamond stands out)
- ✅ Notification icon: monochrome version can be derived (white diamond on transparent)
- ✅ Splash screen: centered logo on brand dark blue

## File Locations
All files under:
```
mobile/flutter/android/app/src/main/res/
├── drawable/
│   ├── ic_launcher_foreground.xml
│   ├── ic_launcher_background.xml
│   └── splash_screen.xml
├── mipmap-anydpi-v26/
│   └── ic_launcher.xml
└── values/
    └── colors.xml
```
