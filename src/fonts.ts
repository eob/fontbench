export type TypographicCategory = 'serif' | 'non-serif' | 'mono' | 'handwriting' | 'other';
export type TypographicWeight = 'thin' | 'regular' | 'bold' | 'black';
export type TypographicModifier = 'regular' | 'italic' | 'underline' | 'strikethrough' | 'small-caps';
export type TypographicKerning = 'tight' | 'normal' | 'loose';
export type TypographicLineHeight = 'tight' | 'normal' | 'loose';
export type ContainerWidthId = 'narrow' | 'medium' | 'wide';

export interface FontSpec {
  id: string;
  name: string;
  cssFamily: string;
  cssUrl: string;
  // Curated declarations when the provider stylesheet misidentifies its faces.
  cssOverride?: string;
  category: TypographicCategory;
  subCategory: string;
  aliases: string[];
  description: string;
}

export interface RenderWidth {
  id: ContainerWidthId;
  widthPx: number;
  label: string;
}

export const WIDTH_VARIANTS: RenderWidth[] = [
  { id: 'narrow', widthPx: 220, label: 'Narrow (220px, wraps ~4 lines)' },
  { id: 'medium', widthPx: 320, label: 'Medium (320px, wraps ~3 lines)' },
  { id: 'wide', widthPx: 440, label: 'Wide (440px, wraps ~2 lines)' },
];

export const WEIGHT_NUMERIC_MAP: Record<TypographicWeight, number> = {
  thin: 200,
  regular: 400,
  bold: 700,
  black: 900,
};

export const KERNING_CSS_MAP: Record<TypographicKerning, string> = {
  tight: '-0.05em',
  normal: '0em',
  loose: '0.12em',
};

export const LINE_HEIGHT_CSS_MAP: Record<TypographicLineHeight, number> = {
  tight: 1.15,
  normal: 1.45,
  loose: 1.9,
};

export interface VariantRecipe {
  variantIndex: number;
  weight: TypographicWeight;
  modifier: TypographicModifier;
  kerning: TypographicKerning;
  lineHeight: TypographicLineHeight;
  widthId: ContainerWidthId;
}

// 20 recipes per font (up to 50 fonts * 20 = 1,000 supported tasks)
export const VARIANT_RECIPES: VariantRecipe[] = [
  { variantIndex: 1,  weight: 'thin',    modifier: 'regular',       kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 2,  weight: 'regular', modifier: 'italic',        kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 3,  weight: 'bold',    modifier: 'underline',     kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 4,  weight: 'black',   modifier: 'strikethrough', kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 5,  weight: 'thin',    modifier: 'small-caps',    kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 6,  weight: 'regular', modifier: 'regular',       kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 7,  weight: 'bold',    modifier: 'italic',        kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 8,  weight: 'black',   modifier: 'underline',     kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 9,  weight: 'thin',    modifier: 'strikethrough', kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 10, weight: 'regular', modifier: 'small-caps',    kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 11, weight: 'bold',    modifier: 'regular',       kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 12, weight: 'black',   modifier: 'italic',        kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 13, weight: 'thin',    modifier: 'underline',     kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 14, weight: 'regular', modifier: 'strikethrough', kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 15, weight: 'bold',    modifier: 'small-caps',    kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 16, weight: 'black',   modifier: 'regular',       kerning: 'normal', lineHeight: 'normal', widthId: 'narrow' },
  { variantIndex: 17, weight: 'thin',    modifier: 'italic',        kerning: 'tight',  lineHeight: 'loose',  widthId: 'medium' },
  { variantIndex: 18, weight: 'regular', modifier: 'underline',     kerning: 'loose',  lineHeight: 'tight',  widthId: 'wide'   },
  { variantIndex: 19, weight: 'bold',    modifier: 'strikethrough', kerning: 'tight',  lineHeight: 'tight',  widthId: 'narrow' },
  { variantIndex: 20, weight: 'black',   modifier: 'small-caps',    kerning: 'loose',  lineHeight: 'loose',  widthId: 'wide'   },
];

export const TOP_50_FONTS: FontSpec[] = [
  // --- NON-SERIF / SANS-SERIF (20) ---
  {
    id: 'arial',
    name: 'Arial',
    cssFamily: 'Arial',
    cssUrl: 'https://fonts.cdnfonts.com/css/arial',
    cssOverride: `
      @font-face { font-family: 'Arial'; font-style: normal; font-weight: 400; src: url('https://fonts.cdnfonts.com/s/29105/ARIAL.woff') format('woff'); }
      @font-face { font-family: 'Arial'; font-style: italic; font-weight: 400; src: url('https://fonts.cdnfonts.com/s/29105/ARIALI.woff') format('woff'); }
      @font-face { font-family: 'Arial'; font-style: normal; font-weight: 700; src: url('https://fonts.cdnfonts.com/s/29105/ARIALBD.woff') format('woff'); }
      @font-face { font-family: 'Arial'; font-style: italic; font-weight: 700; src: url('https://fonts.cdnfonts.com/s/29105/ARIALBI.woff') format('woff'); }
      @font-face { font-family: 'Arial'; font-style: normal; font-weight: 900; src: url('https://fonts.cdnfonts.com/s/29105/ARIBLK.woff') format('woff'); }
    `,
    category: 'non-serif',
    subCategory: 'neo-grotesque',
    aliases: ['arial', 'arial mt'],
    description: 'Monotype neo-grotesque sans-serif with angled stroke terminals.'
  },
  {
    id: 'helvetica',
    name: 'Helvetica',
    cssFamily: 'Helvetica',
    cssUrl: 'https://fonts.cdnfonts.com/css/helvetica-2',
    category: 'non-serif',
    subCategory: 'neo-grotesque',
    aliases: ['helvetica', 'helvetica neue'],
    description: 'Classic Swiss neo-grotesque with strictly horizontal terminals and uniform stroke weight.'
  },
  {
    id: 'roboto',
    name: 'Roboto',
    cssFamily: 'Roboto',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Roboto:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'neo-grotesque',
    aliases: ['roboto'],
    description: 'Christian Robertson dual-nature sans-serif with mechanical skeleton and friendly open curves.'
  },
  {
    id: 'inter',
    name: 'Inter',
    cssFamily: 'Inter',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'neo-grotesque',
    aliases: ['inter'],
    description: 'Rasmus Andersson interface font with tall x-height and high screen readability.'
  },
  {
    id: 'montserrat',
    name: 'Montserrat',
    cssFamily: 'Montserrat',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Montserrat:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'geometric-sans',
    aliases: ['montserrat'],
    description: 'Julieta Ulanovsky geometric sans-serif inspired by urban typography in Buenos Aires.'
  },
  {
    id: 'open-sans',
    name: 'Open Sans',
    cssFamily: 'Open Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Open+Sans:ital,wght@0,300..800;1,300..800&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['open sans', 'opensans'],
    description: 'Steve Matteson humanist sans-serif with upright stress and open forms.'
  },
  {
    id: 'lato',
    name: 'Lato',
    cssFamily: 'Lato',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Lato:ital,wght@0,100;0,300;0,400;0,700;0,900;1,100;1,300;1,400;1,700;1,900&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['lato'],
    description: 'Łukasz Dziedzic warm humanist sans-serif featuring semi-rounded letter details.'
  },
  {
    id: 'poppins',
    name: 'Poppins',
    cssFamily: 'Poppins',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Poppins:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap',
    category: 'non-serif',
    subCategory: 'geometric-sans',
    aliases: ['poppins'],
    description: 'Indian Type Foundry pure geometric sans-serif with near-monoline strokes.'
  },
  {
    id: 'source-sans-3',
    name: 'Source Sans 3',
    cssFamily: 'Source Sans 3',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Source+Sans+3:ital,wght@0,200..900;1,200..900&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['source sans 3', 'source sans pro', 'source sans'],
    description: 'Paul D. Hunt Adobe open source typeface designed for UI legibility.'
  },
  {
    id: 'oswald',
    name: 'Oswald',
    cssFamily: 'Oswald',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Oswald:wght@200..700&display=swap',
    category: 'non-serif',
    subCategory: 'condensed-sans',
    aliases: ['oswald'],
    description: 'Vernon Adams reworking of the classic Alternate Gothic grotesque style.'
  },
  {
    id: 'raleway',
    name: 'Raleway',
    cssFamily: 'Raleway',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Raleway:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'geometric-sans',
    aliases: ['raleway'],
    description: 'Matt McInerney elegant geometric sans-serif featuring a distinctive crossed W.'
  },
  {
    id: 'nunito',
    name: 'Nunito',
    cssFamily: 'Nunito',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Nunito:ital,wght@0,200..1000;1,200..1000&display=swap',
    category: 'non-serif',
    subCategory: 'rounded-sans',
    aliases: ['nunito'],
    description: 'Vernon Adams well-balanced rounded terminal sans-serif.'
  },
  {
    id: 'rubik',
    name: 'Rubik',
    cssFamily: 'Rubik',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Rubik:ital,wght@0,300..900;1,300..900&display=swap',
    category: 'non-serif',
    subCategory: 'rounded-sans',
    aliases: ['rubik'],
    description: 'Philipp Hubert and Sebastian Fischer sans-serif with slightly rounded corners.'
  },
  {
    id: 'work-sans',
    name: 'Work Sans',
    cssFamily: 'Work Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Work+Sans:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'grotesque-sans',
    aliases: ['work sans'],
    description: 'Wei Huang early grotesque sans-serif optimized for screen text at medium sizes.'
  },
  {
    id: 'fira-sans',
    name: 'Fira Sans',
    cssFamily: 'Fira Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Fira+Sans:ital,wght@0,100;0,200;0,300;0,400;0,500;0,600;0,700;0,800;0,900;1,100;1,200;1,300;1,400;1,500;1,600;1,700;1,800;1,900&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['fira sans', 'fira'],
    description: 'Erik Spiekermann humanist sans-serif designed for Mozilla Firefox OS.'
  },
  {
    id: 'pt-sans',
    name: 'PT Sans',
    cssFamily: 'PT Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=PT+Sans:ital,wght@0,400;0,700;1,400;1,700&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['pt sans'],
    description: 'ParaType universal pan-Cyrillic and Latin humanist sans-serif.'
  },
  {
    id: 'dm-sans',
    name: 'DM Sans',
    cssFamily: 'DM Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,100..1000;1,9..40,100..1000&display=swap',
    category: 'non-serif',
    subCategory: 'geometric-sans',
    aliases: ['dm sans'],
    description: 'Colophon Foundry low-contrast geometric sans-serif for clean interface legibility.'
  },
  {
    id: 'plus-jakarta-sans',
    name: 'Plus Jakarta Sans',
    cssFamily: 'Plus Jakarta Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:ital,wght@0,200..800;1,200..800&display=swap',
    category: 'non-serif',
    subCategory: 'geometric-sans',
    aliases: ['plus jakarta sans', 'jakarta sans'],
    description: 'Tokotype fresh contemporary geometric sans-serif with clean proportions.'
  },
  {
    id: 'noto-sans',
    name: 'Noto Sans',
    cssFamily: 'Noto Sans',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Noto+Sans:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'non-serif',
    subCategory: 'humanist-sans',
    aliases: ['noto sans', 'noto'],
    description: 'Monotype universal typeface covering all worldwide scripts without tofu glyphs.'
  },
  {
    id: 'verdana',
    name: 'Verdana',
    cssFamily: 'Verdana',
    cssUrl: 'https://fonts.cdnfonts.com/css/verdana',
    category: 'non-serif',
    subCategory: 'screen-humanist-sans',
    aliases: ['verdana'],
    description: 'Matthew Carter screen humanist sans-serif with wide spacing and large counters.'
  },

  // --- SERIF (15) ---
  {
    id: 'times-new-roman',
    name: 'Times New Roman',
    cssFamily: 'Times New Roman',
    cssUrl: 'https://fonts.cdnfonts.com/css/times-new-roman',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['times new roman', 'times'],
    description: 'Stanley Morison newspaper serif designed for high legibility in narrow columns.'
  },
  {
    id: 'georgia',
    name: 'Georgia',
    cssFamily: 'Georgia',
    cssUrl: 'https://fonts.cdnfonts.com/css/georgia-2',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['georgia'],
    description: 'Matthew Carter screen serif featuring wide proportions, open counters, and ball terminals.'
  },
  {
    id: 'playfair-display',
    name: 'Playfair Display',
    cssFamily: 'Playfair Display',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&display=swap',
    category: 'serif',
    subCategory: 'didone-modern-serif',
    aliases: ['playfair display', 'playfair'],
    description: 'Claus Eggers Sørensen high-contrast transitional/modern display serif.'
  },
  {
    id: 'merriweather',
    name: 'Merriweather',
    cssFamily: 'Merriweather',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Merriweather:ital,wght@0,300..900;1,300..900&display=swap',
    category: 'serif',
    subCategory: 'editorial-serif',
    aliases: ['merriweather'],
    description: 'Eben Sorkin text typeface designed to be highly readable on digital screens.'
  },
  {
    id: 'eb-garamond',
    name: 'EB Garamond',
    cssFamily: 'EB Garamond',
    cssUrl: 'https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400..800;1,400..800&display=swap',
    category: 'serif',
    subCategory: 'old-style-serif',
    aliases: ['eb garamond', 'garamond'],
    description: 'Georg Duffner revival of Claude Garamont classic Renaissance Roman typefaces.'
  },
  {
    id: 'lora',
    name: 'Lora',
    cssFamily: 'Lora',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Lora:ital,wght@0,400..700;1,400..700&display=swap',
    category: 'serif',
    subCategory: 'contemporary-serif',
    aliases: ['lora'],
    description: 'Olga Karpushina contemporary serif with calligraphic roots and brushed terminals.'
  },
  {
    id: 'pt-serif',
    name: 'PT Serif',
    cssFamily: 'PT Serif',
    cssUrl: 'https://fonts.googleapis.com/css2?family=PT+Serif:ital,wght@0,400;0,700;1,400;1,700&display=swap',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['pt serif'],
    description: 'ParaType universal serif pairing with PT Sans.'
  },
  {
    id: 'libre-baskerville',
    name: 'Libre Baskerville',
    cssFamily: 'Libre Baskerville',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['libre baskerville', 'baskerville'],
    description: 'Impallari Type screen-optimized revival of John Baskerville 1757 typeface.'
  },
  {
    id: 'cormorant-garamond',
    name: 'Cormorant Garamond',
    cssFamily: 'Cormorant Garamond',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,300..700;1,300..700&display=swap',
    category: 'serif',
    subCategory: 'classical-display-serif',
    aliases: ['cormorant garamond', 'cormorant'],
    description: 'Christian Thalmann traditional display serif with sharp, expressive flourishes.'
  },
  {
    id: 'cinzel',
    name: 'Cinzel',
    cssFamily: 'Cinzel',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Cinzel:wght@400..900&display=swap',
    category: 'serif',
    subCategory: 'classical-roman-serif',
    aliases: ['cinzel'],
    description: 'Natanael Gama Roman-inscription all-caps serif inspired by 1st century gravures.'
  },
  {
    id: 'bodoni-moda',
    name: 'Bodoni Moda',
    cssFamily: 'Bodoni Moda',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Bodoni+Moda:ital,opsz,wght@0,6..96,400..900;1,6..96,400..900&display=swap',
    category: 'serif',
    subCategory: 'didone-modern-serif',
    aliases: ['bodoni moda', 'bodoni'],
    description: 'Modern high-contrast Didone fashion typeface with hairline serifs and vertical stress.'
  },
  {
    id: 'bitter',
    name: 'Bitter',
    cssFamily: 'Bitter',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Bitter:ital,wght@0,100..900;1,100..900&display=swap',
    category: 'serif',
    subCategory: 'slab-serif',
    aliases: ['bitter'],
    description: 'Sol Matas contemporary slab serif designed for comfortable reading on e-readers.'
  },
  {
    id: 'arvo',
    name: 'Arvo',
    cssFamily: 'Arvo',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Arvo:ital,wght@0,400;0,700;1,400;1,700&display=swap',
    category: 'serif',
    subCategory: 'geometric-slab-serif',
    aliases: ['arvo'],
    description: 'Anton Koovit clean geometric slab serif suited for both screen and print.'
  },
  {
    id: 'crimson-text',
    name: 'Crimson Text',
    cssFamily: 'Crimson Text',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Crimson+Text:ital,wght@0,400;0,600;0,700;1,400;1,600;1,700&display=swap',
    category: 'serif',
    subCategory: 'old-style-serif',
    aliases: ['crimson text', 'crimson'],
    description: 'Sebastian Kosch classical book production serif in the tradition of Garamond and Minion.'
  },
  {
    id: 'spectral',
    name: 'Spectral',
    cssFamily: 'Spectral',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Spectral:ital,wght@0,200;0,300;0,400;0,500;0,600;0,700;0,800;1,200;1,300;1,400;1,500;1,600;1,700;1,800&display=swap',
    category: 'serif',
    subCategory: 'screen-editorial-serif',
    aliases: ['spectral'],
    description: 'Production Type screen-first editorial serif designed for Google Docs.'
  },

  // --- MONOSPACE (6) ---
  {
    id: 'courier-new',
    name: 'Courier New',
    cssFamily: 'Courier New',
    cssUrl: 'https://fonts.cdnfonts.com/css/courier-new',
    category: 'mono',
    subCategory: 'slab-serif-mono',
    aliases: ['courier new', 'courier'],
    description: 'Howard Kettler typewriter monospaced slab serif with uniform character advance.'
  },
  {
    id: 'roboto-mono',
    name: 'Roboto Mono',
    cssFamily: 'Roboto Mono',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Roboto+Mono:ital,wght@0,100..700;1,100..700&display=swap',
    category: 'mono',
    subCategory: 'geometric-mono',
    aliases: ['roboto mono'],
    description: 'Monospaced addition to the Roboto family optimized for programming and data tables.'
  },
  {
    id: 'fira-code',
    name: 'Fira Code',
    cssFamily: 'Fira Code',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Fira+Code:wght@300..700&display=swap',
    category: 'mono',
    subCategory: 'coding-ligature-mono',
    aliases: ['fira code'],
    description: 'Nikita Prokopov monospace typeface with programming ligatures based on Fira Mono.'
  },
  {
    id: 'source-code-pro',
    name: 'Source Code Pro',
    cssFamily: 'Source Code Pro',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Source+Code+Pro:ital,wght@0,200..900;1,200..900&display=swap',
    category: 'mono',
    subCategory: 'humanist-mono',
    aliases: ['source code pro', 'source code'],
    description: 'Paul D. Hunt monospaced companion to Source Sans designed for code editors.'
  },
  {
    id: 'space-mono',
    name: 'Space Mono',
    cssFamily: 'Space Mono',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Space+Mono:ital,wght@0,400;0,700;1,400;1,700&display=swap',
    category: 'mono',
    subCategory: 'display-mono',
    aliases: ['space mono'],
    description: 'Colophon Foundry original monospace type family developed for editorial usage.'
  },
  {
    id: 'jetbrains-mono',
    name: 'JetBrains Mono',
    cssFamily: 'JetBrains Mono',
    cssUrl: 'https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,100..800;1,100..800&display=swap',
    category: 'mono',
    subCategory: 'developer-mono',
    aliases: ['jetbrains mono'],
    description: 'JetBrains typeface tailored for developers with increased letter height and distinctive symbols.'
  },

  // --- HANDWRITING (5) ---
  {
    id: 'comic-sans-ms',
    name: 'Comic Sans MS',
    cssFamily: 'Comic Sans MS',
    cssUrl: 'https://fonts.cdnfonts.com/css/comic-sans-ms',
    category: 'handwriting',
    subCategory: 'casual-script',
    aliases: ['comic sans ms', 'comic sans'],
    description: 'Vincent Connare casual marker-pen script inspired by comic book speech bubbles.'
  },
  {
    id: 'pacifico',
    name: 'Pacifico',
    cssFamily: 'Pacifico',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Pacifico&display=swap',
    category: 'handwriting',
    subCategory: 'brush-script',
    aliases: ['pacifico'],
    description: 'Vernon Adams fun and creative brush script inspired by 1950s American surf culture.'
  },
  {
    id: 'dancing-script',
    name: 'Dancing Script',
    cssFamily: 'Dancing Script',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Dancing+Script:wght@400..700&display=swap',
    category: 'handwriting',
    subCategory: 'casual-cursive',
    aliases: ['dancing script'],
    description: 'Pablo Impallari lively casual cursive script where letters bounce dynamically.'
  },
  {
    id: 'caveat',
    name: 'Caveat',
    cssFamily: 'Caveat',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Caveat:wght@400..700&display=swap',
    category: 'handwriting',
    subCategory: 'handwritten-marker',
    aliases: ['caveat'],
    description: 'Pablo Impallari cheerful handwriting typeface with subtle open strokes.'
  },
  {
    id: 'shadows-into-light',
    name: 'Shadows Into Light',
    cssFamily: 'Shadows Into Light',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Shadows+Into+Light&display=swap',
    category: 'handwriting',
    subCategory: 'neat-handwriting',
    aliases: ['shadows into light'],
    description: 'Kimberly Geswein neat and feminine handwriting font with rounded edges.'
  },

  // --- OTHER / DISPLAY (4) ---
  {
    id: 'impact',
    name: 'Impact',
    cssFamily: 'Impact',
    cssUrl: 'https://fonts.cdnfonts.com/css/impact',
    category: 'other',
    subCategory: 'industrial-display',
    aliases: ['impact'],
    description: 'Geoffrey Lee ultra-thick condensed display face famous for internet meme typography.'
  },
  {
    id: 'bebas-neue',
    name: 'Bebas Neue',
    cssFamily: 'Bebas Neue',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap',
    category: 'other',
    subCategory: 'condensed-display',
    aliases: ['bebas neue', 'bebas'],
    description: 'Ryoichi Tsunekawa condensed all-caps display font popular in posters and headlines.'
  },
  {
    id: 'lobster',
    name: 'Lobster',
    cssFamily: 'Lobster',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Lobster&display=swap',
    category: 'other',
    subCategory: 'retro-display',
    aliases: ['lobster'],
    description: 'Pablo Impallari bold condensed retro script with lots of alternates and ligatures.'
  },
  {
    id: 'bungee',
    name: 'Bungee',
    cssFamily: 'Bungee',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Bungee&display=swap',
    category: 'other',
    subCategory: 'urban-sign-display',
    aliases: ['bungee'],
    description: 'David Jonathan Ross display typeface celebrating urban signage and vertical typesetting.'
  }
];

export const STANDARD_PANGRAM = "The quick brown fox jumps over the lazy dog.";
