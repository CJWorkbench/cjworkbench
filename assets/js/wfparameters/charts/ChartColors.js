export const defaultColors = [
  '#ffaad3', // brand-learn
  '#48c8d7', // brand-workspace
  '#fbaa6d', // brand-orange
  '#2daaa8',
  '#e24f4a', // brand-red
  '#769bb0',
  '#a2a2a2' // medium-gray
]

export function getColor (idx) {
  return defaultColors[idx % defaultColors.length]
}
