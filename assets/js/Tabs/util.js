export function generateTabName (parseFormat, generateFormat, existingTabNames) {
  const parseNumber = (tabName) => {
    const match = parseFormat.exec(tabName)
    return match? +match[1] : null
  }

  const numbers = existingTabNames.map(parseNumber).filter(n => n !== null)
  const nextNumber = Math.max(0, ...numbers) + 1
  return generateFormat.replace('%d', nextNumber)
}
