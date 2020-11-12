/* globals expect, test */
import getCellRange from './getCellRange'

test('get 0 rows', () => {
  expect(getCellRange([[null]], 10, 5, 0, 0, 0, 1)).toEqual([])
})

test('get loaded cells at start', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1', 'C1', 'D1'],
            ['A2', 'B2', 'C2', 'D2'],
            ['A3', 'B3', 'C3', 'D3']
          ]
        ]
      ], 10, 5, 0, 2, 0, 3
    )
  ).toEqual([['A1', 'B1', 'C1'], ['A2', 'B2', 'C2']])
})

test('skip within a tile', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1', 'C1', 'D1'],
            ['A2', 'B2', 'C2', 'D2'],
            ['A3', 'B3', 'C3', 'D3']
          ]
        ]
      ], 10, 5, 1, 2, 2, 3
    )
  ).toEqual([['C2']])
})

test('render a loading tile as nulls', () => {
  expect(
    getCellRange(
      [[null]],
      10, 5, 1, 3, 2, 5
    )
  ).toEqual([[null, null, null], [null, null, null]])
})

test('skip a gap', () => {
  expect(
    getCellRange(
      [
        3,
        [
          [
            ['A1', 'B1', 'C1', 'D1'],
            ['A2', 'B2', 'C2', 'D2'],
            ['A3', 'B3', 'C3', 'D3']
          ]
        ]
      ], 10, 5, 30, 32, 0, 3
    )
  ).toEqual([['A1', 'B1', 'C1'], ['A2', 'B2', 'C2']])
})

test('skip a tile', () => {
  expect(
    getCellRange(
      [
        [
          null, // simplest form of tile
          [
            ['A1', 'B1', 'C1', 'D1'],
            ['A2', 'B2', 'C2', 'D2'],
            ['A3', 'B3', 'C3', 'D3']
          ]
        ]
      ], 10, 5, 0, 2, 5, 8
    )
  ).toEqual([['A1', 'B1', 'C1'], ['A2', 'B2', 'C2']])
})

test('span tiles horizontally', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1', 'C1'],
            ['A2', 'B2', 'C2']
          ],
          [
            ['D1', 'E1', 'F1'],
            ['D2', 'E2', 'F2']
          ],
          [
            ['G1', 'H1', 'I1'],
            ['G2', 'H2', 'I2']
          ]
        ]
      ], 10, 3, 0, 2, 2, 8
    )
  ).toEqual([['C1', 'D1', 'E1', 'F1', 'G1', 'H1'], ['C2', 'D2', 'E2', 'F2', 'G2', 'H2']])
})

test('span tiles horizontally across an error tile', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1', 'C1'],
            ['A2', 'B2', 'C2']
          ],
          { error: { name: 'MyError', message: 'hi' } },
          [
            ['G1', 'H1', 'I1'],
            ['G2', 'H2', 'I2']
          ]
        ]
      ], 10, 3, 0, 2, 2, 8
    )
  ).toEqual([['C1', null, null, null, 'G1', 'H1'], ['C2', null, null, null, 'G2', 'H2']])
})

test('span tiles vertically', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1'],
            ['A2', 'B2'],
            ['A3', 'B3']
          ]
        ],
        [
          [
            ['A4', 'B4'],
            ['A5', 'B5'],
            ['A6', 'B6']
          ]
        ],
        [
          [
            ['A7', 'B7'],
            ['A8', 'B8'],
            ['A9', 'B9']
          ]
        ]
      ], 3, 5, 2, 8, 1, 2
    )
  ).toEqual([['B3'], ['B4'], ['B5'], ['B6'], ['B7'], ['B8']])
})

test('span tiles vertically across a gap', () => {
  expect(
    getCellRange(
      [
        [
          [
            ['A1', 'B1'],
            ['A2', 'B2'],
            ['A3', 'B3']
          ]
        ],
        2,
        [
          [
            ['A10', 'B10'],
            ['A11', 'B11'],
            ['A12', 'B12']
          ]
        ]
      ], 3, 5, 2, 10, 1, 2
    )
  ).toEqual([['B3'], [null], [null], [null], [null], [null], [null], ['B10']])
})
