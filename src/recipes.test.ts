import { expect, test } from 'bun:test';
import { VARIANT_RECIPES } from './fonts';

test('every weight/modifier combination samples all spacing and width levels', () => {
  for (const weight of ['thin', 'regular', 'bold', 'black']) {
    for (const modifier of ['regular', 'italic', 'underline', 'strikethrough', 'small-caps']) {
      const recipes = VARIANT_RECIPES.filter(recipe => recipe.weight === weight && recipe.modifier === modifier);
      expect(recipes).toHaveLength(3);
      for (const axis of ['kerning', 'lineHeight', 'widthId'] as const) {
        expect(new Set(recipes.map(recipe => recipe[axis])).size).toBe(3);
      }
    }
  }
});

test('card width and tracking cannot determine line-height labels', () => {
  for (const axis of ['widthId', 'kerning'] as const) {
    for (const value of new Set(VARIANT_RECIPES.map(recipe => recipe[axis]))) {
      const recipes = VARIANT_RECIPES.filter(recipe => recipe[axis] === value);
      expect(new Set(recipes.map(recipe => recipe.lineHeight)).size).toBe(3);
      const counts = ['tight', 'normal', 'loose'].map(level => recipes.filter(recipe => recipe.lineHeight === level).length);
      expect(Math.max(...counts) / recipes.length).toBeLessThanOrEqual(0.5);
    }
  }
  expect(new Set(VARIANT_RECIPES.map(recipe => recipe.variantIndex)).size).toBe(VARIANT_RECIPES.length);
});
