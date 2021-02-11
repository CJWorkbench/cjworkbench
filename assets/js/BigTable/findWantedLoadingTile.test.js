/* globals expect, test */
import findWantedLoadingTile from './findWantedLoadingTile'

test('find null on empty grid', () => {
  expect(findWantedLoadingTile([], 0, 1, 0, 1)).toBe(null)
})

test('find the first tile on a one-tile grid', () => {
  expect(findWantedLoadingTile([[null]], 0, 1, 0, 1)).toEqual({
    tileRow: 0,
    tileColumn: 0
  })
})

test('find nothing when the grid is all loaded', () => {
  expect(findWantedLoadingTile([[[['X']]]], 0, 1, 0, 1)).toBe(null)
})

test('skip gaps', () => {
  expect(
    findWantedLoadingTile(
      [[null, null, null], 2, [null, null, null]],
      3,
      4,
      1,
      2
    )
  ).toEqual({ tileRow: 3, tileColumn: 1 })
})

test('find the first loading tile in a row', () => {
  expect(
    findWantedLoadingTile([[null, [['B1']], [['C1']], null]], 0, 1, 1, 4)
  ).toEqual({ tileRow: 0, tileColumn: 3 })
})

test('skip an all-loaded row and search the next row', () => {
  expect(
    findWantedLoadingTile(
      [
        [null, [['B1']], [['C1']], [['D1']]],
        [null, [['B2']], null, [['D2']]]
      ],
      0,
      2,
      1,
      4
    )
  ).toEqual({ tileRow: 1, tileColumn: 2 })
})
