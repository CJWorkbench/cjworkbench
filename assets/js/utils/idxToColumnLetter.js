/**
 * Return 'A' for 0, 'B' for 1, 'AA' for 26, and so on.
 */
export default function idxToColumnLetter (idx) {
  let letters = ''
  let cidx = parseInt(idx)
  cidx += 1
  do {
    cidx -= 1
    letters = String.fromCharCode((cidx % 26) + 65) + letters
    cidx = Math.floor(cidx / 26)
  } while (cidx > 0)
  return letters
}
