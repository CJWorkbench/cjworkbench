export const defaultColors = [
  '#e24f4a', // brand-red
  '#ffaad3', // brand-learn
  '#fbaa6d', // brand-orange
  '#48c8d7', // brand-workspace
  '#2daaa8',
  '#769bb0',
  '#a2a2a2' // medium-gray
]

export function getColor (idx) {
  return defaultColors[idx % defaultColors.length]
}
