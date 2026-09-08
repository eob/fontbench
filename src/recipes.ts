import type { VariantRecipe } from './fonts';

const weights = ['thin', 'regular', 'bold', 'black'] as const;
const modifiers = ['regular', 'italic', 'underline', 'strikethrough', 'small-caps'] as const;
const levels = ['tight', 'normal', 'loose'] as const;
const widths = ['narrow', 'medium', 'wide'] as const;

// Each supported face/modifier contributes every level on each layout axis.
// Rotating the phases avoids the old width-to-line-height answer shortcut.
export const VARIANT_RECIPES: VariantRecipe[] = weights.flatMap((weight, w) =>
  modifiers.flatMap((modifier, m) => levels.map((kerning, repeat) => ({
    variantIndex: (w * modifiers.length + m) * levels.length + repeat + 1,
    weight,
    modifier,
    kerning,
    lineHeight: levels[(repeat + m) % levels.length]!,
    widthId: widths[(repeat + w + Math.floor(m / 3)) % widths.length]!,
  }))),
);
