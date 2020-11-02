/* globals expect, test */
import splitGapsIntoLoadingTiles from './splitGapsIntoLoadingTiles'

test('return input when no gaps impact us', () => {
  const sparseTileGrid = [
    [[['0']]],
    3,
    [[['4']]],
    [null],
    [[['6']]],
    [[['9']]]
  ]
  const result = splitGapsIntoLoadingTiles(sparseTileGrid, 4, 6)
  expect(result).toBe(sparseTileGrid)
})

test('split a gap at its start', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    4
  ], 1, 3)
  expect(result).toEqual([
    [[['0']]],
    [null],
    [null],
    2
  ])
})

test('split a gap at its end', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    4,
    [[['5']]]
  ], 3, 5)
  expect(result).toEqual([
    [[['0']]],
    2,
    [null],
    [null],
    [[['5']]]
  ])
})

test('split a gap in its middle', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    4,
    [[['5']]]
  ], 2, 4)
  expect(result).toEqual([
    [[['0']]],
    1,
    [null],
    [null],
    1,
    [[['5']]]
  ])
})

test('split an end-gap at its end, leaving a number before', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    4
  ], 3, 5)
  expect(result).toEqual([
    [[['0']]],
    2,
    [null],
    [null]
  ])
})

test('split an end-gap completely', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    2
  ], 1, 3)
  expect(result).toEqual([
    [[['0']]],
    [null],
    [null]
  ])
})

test('create the same number of loading tiles as there are tiles in the first tile-row', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['A1']], [['A2']], [['A3']]],
    1
  ], 1, 2)
  expect(result).toEqual([
    [[['A1']], [['A2']], [['A3']]],
    [null, null, null]
  ])
})

test('split an end-gap completely, even when wanted start overlaps', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    2
  ], 0, 3)
  expect(result).toEqual([
    [[['0']]],
    [null],
    [null]
  ])
})

test('split a gap when end overlaps', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    2,
    [[['3']]]
  ], 2, 4)
  expect(result).toEqual([
    [[['0']]],
    1,
    [null],
    [[['3']]]
  ])
})

test('split multiple gaps', () => {
  const result = splitGapsIntoLoadingTiles([
    [[['0']]],
    1,
    [[['2']]],
    2,
    [[['5']]]
  ], 0, 6)
  expect(result).toEqual([
    [[['0']]],
    [null],
    [[['2']]],
    [null],
    [null],
    [[['5']]]
  ])
})
