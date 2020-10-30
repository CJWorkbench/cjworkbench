/* globals expect, test */
import placeTile from './placeTile'

test('replace first loading tile with loaded tile', () => {
  const loadedTile = [['foo', 'bar']]
  expect(
    placeTile([[null, null]], 0, 0, loadedTile)
  ).toEqual([[loadedTile, null]])
})

test('replace a loading tile with an error', () => {
  const errorTile = {error: { name: 'x', message: 'y'}}
  expect(
    placeTile([[null, null]], 0, 1, errorTile)
  ).toEqual([[null, errorTile]])
})

test('replace middle loading tile with loaded tile', () => {
  const row1 = [[['A1']], [['B1']], [['C1']]]
  const row2 = [[['A2']], [['B2']], [['C2']]]
  const row3 = [[['A3']], null, [['C3']]]
  const row4 = [[['A4']], [['B4']], [['C4']]]
  const result = placeTile([row1, row2, row3, row4], 2, 1, [['B3']])
  expect(result).toEqual([row1, row2, [[['A3']], [['B3']], [['C3']]], row4])
  // We'll test rows for "is", not "equals". Unchanged rows shouldn't re-render.
  expect(result[0]).toBe(row1)
  expect(result[1]).toBe(row2)
  expect(result[3]).toBe(row4)
})

test('skip a RowGapTile', () => {
  const result = placeTile([
    [[['A1']]],
    2,
    [null],
    [[['A5']]],
  ], 3, 0, [['A4']])
  expect(result).toEqual([
    [[['A1']]],
    2,
    [[['A4']]],
    [[['A5']]],
  ])
})
