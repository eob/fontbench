export interface FontSpec {
  id: string;
  name: string;
  cssFamily: string;
  cssUrl: string;
  category: 'sans-serif' | 'serif' | 'monospace' | 'display' | 'handwriting';
  subCategory?: string;
  aliases: string[];
  description: string;
}

export interface RenderWidth {
  id: 'narrow' | 'medium' | 'wide';
  widthPx: number;
  label: string;
}

export const WIDTH_VARIANTS: RenderWidth[] = [
  { id: 'narrow', widthPx: 220, label: 'Narrow (Wraps ~4 lines)' },
  { id: 'medium', widthPx: 320, label: 'Medium (Wraps ~3 lines)' },
  { id: 'wide', widthPx: 440, label: 'Wide (Wraps ~2 lines)' },
];

export const PILOT_FONTS: FontSpec[] = [
  {
    id: 'arial',
    name: 'Arial',
    cssFamily: 'Arial',
    cssUrl: 'https://fonts.cdnfonts.com/css/arial',
    category: 'sans-serif',
    subCategory: 'neo-grotesque',
    aliases: ['arial', 'arial mt'],
    description: 'Monotype neo-grotesque sans-serif with angled stroke terminals (contrast with Helvetica).'
  },
  {
    id: 'helvetica',
    name: 'Helvetica',
    cssFamily: 'Helvetica',
    cssUrl: 'https://fonts.cdnfonts.com/css/helvetica-2',
    category: 'sans-serif',
    subCategory: 'neo-grotesque',
    aliases: ['helvetica', 'helvetica neue'],
    description: 'Classic Swiss neo-grotesque with strictly horizontal terminals and uniform stroke weight.'
  },
  {
    id: 'times-new-roman',
    name: 'Times New Roman',
    cssFamily: 'Times New Roman',
    cssUrl: 'https://fonts.cdnfonts.com/css/times-new-roman',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['times new roman', 'times'],
    description: 'Stanley Morison newspaper serif designed for high legibility in narrow newsprint columns.'
  },
  {
    id: 'georgia',
    name: 'Georgia',
    cssFamily: 'Georgia',
    cssUrl: 'https://fonts.cdnfonts.com/css/georgia-2',
    category: 'serif',
    subCategory: 'transitional-serif',
    aliases: ['georgia'],
    description: 'Matthew Carter screen serif featuring wide proportions, open counters, and distinct ball terminals.'
  },
  {
    id: 'courier-new',
    name: 'Courier New',
    cssFamily: 'Courier New',
    cssUrl: 'https://fonts.cdnfonts.com/css/courier-new',
    category: 'monospace',
    subCategory: 'slab-serif-mono',
    aliases: ['courier new', 'courier'],
    description: 'Howard Kettler typewriter monospaced slab serif with uniform character advance.'
  },
  {
    id: 'comic-sans-ms',
    name: 'Comic Sans MS',
    cssFamily: 'Comic Sans MS',
    cssUrl: 'https://fonts.cdnfonts.com/css/comic-sans-ms',
    category: 'handwriting',
    subCategory: 'casual-script',
    aliases: ['comic sans ms', 'comic sans'],
    description: 'Vincent Connare casual marker-pen script inspired by comic book lettering.'
  },
  {
    id: 'roboto',
    name: 'Roboto',
    cssFamily: 'Roboto',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap',
    category: 'sans-serif',
    subCategory: 'neo-grotesque',
    aliases: ['roboto'],
    description: 'Christian Robertson dual-nature sans-serif with mechanical skeleton and friendly open curves.'
  },
  {
    id: 'inter',
    name: 'Inter',
    cssFamily: 'Inter',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap',
    category: 'sans-serif',
    subCategory: 'interface-neo-grotesque',
    aliases: ['inter'],
    description: 'Rasmus Andersson interface font with tall x-height, square dots, and high screen readability.'
  },
  {
    id: 'playfair-display',
    name: 'Playfair Display',
    cssFamily: 'Playfair Display',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&display=swap',
    category: 'serif',
    subCategory: 'didone-modern-serif',
    aliases: ['playfair display', 'playfair'],
    description: 'Claus Eggers Sørensen high-contrast transitional/modern display serif influenced by Baskerville.'
  },
  {
    id: 'montserrat',
    name: 'Montserrat',
    cssFamily: 'Montserrat',
    cssUrl: 'https://fonts.googleapis.com/css2?family=Montserrat:wght@400;700&display=swap',
    category: 'sans-serif',
    subCategory: 'geometric-sans',
    aliases: ['montserrat'],
    description: 'Julieta Ulanovsky geometric sans-serif inspired by urban typography in Buenos Aires.'
  }
];

export const STANDARD_PANGRAM = "The quick brown fox jumps over the lazy dog.";
