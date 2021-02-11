/**
 * Escape a string so it can be included in a RegExp.
 *
 * Copy-pasted from:
 * https://developer.mozilla.org/en-US/docs/Web/JavaScript/Guide/Regular_Expressions#Escaping
 */
export function escapeRegExp (string) {
  return string.replace(/[.*+?^${}()|[\]\\]/g, '\\$&') // $& means the whole matched string
}

/**
 * Generate a tab name with a unique number, like "Tab 1" or "Tabname (3)".
 *
 * @param RegExp parseFormat Regexp for tab names that may conflict with this
 *                           new one (depending on the number).
 * @param String generateFormat String with '%d' that the new tab must have.
 *                              Escape '%' by writing '%%'.
 * @param Array tabNames Existing tab names. (The number in the returned String
 *                       will be one higher than the largest existing tab name
 *                       matching parseFormat.)
 * @return String Unique, numbered tab name.
 */
export function generateTabName (
  parseFormat,
  generateFormat,
  existingTabNames
) {
  const parseNumber = tabName => {
    const match = parseFormat.exec(tabName)
    return match ? +match[1] : null
  }

  const numbers = existingTabNames.map(parseNumber).filter(n => n !== null)
  const nextNumber = Math.max(0, ...numbers) + 1
  // Replace '%%' with '%', '%d' with nextNumber. Any other '%' is invalid,
  // because the user didn't understand the calling convention.
  return generateFormat.replace(/%(.)/g, (_, c) => {
    switch (c) {
      case 'd':
        return String(nextNumber)
      case '%':
        return '%'
      default:
        throw new Error(
          'Invalid %-escape pattern informat string: ' + generateFormat
        )
    }
  })
}
