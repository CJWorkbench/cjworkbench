/**
 * A tile full of data.
 *
 * @property {number} tileRow Row of the tile (2 means, "third N rows of data")
 * @property {number} tileColumn Column of the tile (1 means, "second M columns of data")
 * @property {array} rows Array of Arrays of values
 */
export class LoadedTile {
  constructor (tileRow, tileColumn, rows) {
    this.type = 'loaded'
    this.tileRow = tileRow
    this.tileColumn = tileColumn
    this.rows = rows
  }
}

/**
 * A tile that is pending.
 *
 * @property {number} tileRow Row of the tile (2 means, "third N rows of data")
 * @property {number} tileColumn Column of the tile (1 means, "second M columns of data")
 */
export class LoadingTile {
  constructor (tileRow, tileColumn) {
    this.type = 'loading'
    this.tileRow = tileRow
    this.tileColumn = tileColumn
  }
}

/**
 * A tile that resulted in error.
 *
 * @property {number} tileRow Row of the tile (2 means, "third N rows of data")
 * @property {number} tileColumn Column of the tile (1 means, "second M columns of data")
 * @property {Error} error Error object that explains why this was not loaded
 */
export class ErrorTile {
  constructor (tileRow, tileColumn, error) {
    this.type = 'error'
    this.tileRow = tileRow
    this.tileColumn = tileColumn
    this.error = error
  }
}

/**
 * A grid of tiles.
 *
 * @property {tileRows} Array of [Array[Tile], Array[Tile], Number, Array[Tile], ...].
 *                      Numbers are gaps. (Think of it as an explicitly-sparse Array.)
 */
export class SparseTileGrid {
  constructor (tileRows) {
    this.tileRows = tileRows
  }
}
