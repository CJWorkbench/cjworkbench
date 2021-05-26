import React from 'react'
import BigTable from '../BigTable'
import TextCell from '../BigTable/Cell/TextCell'

const EmptyTileGrid = [[[
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', ''],
  ['', '', '', '']
]]]

function EmptyColumnHeader (props) {
  const { columnLetter } = props

  return (
    <>
      <div className='column-letter'>{columnLetter}</div>
      <div className='column-key'>
        <div className='value' />
        <div className='column-type' />
      </div>
    </>
  )
}

const EmptyColumn = {
  type: 'text',
  width: 180,
  valueComponent: TextCell
}

const EmptyColumns = [
  { ...EmptyColumn, headerComponent: () => <EmptyColumnHeader columnLetter='A' /> },
  { ...EmptyColumn, headerComponent: () => <EmptyColumnHeader columnLetter='B' /> },
  { ...EmptyColumn, headerComponent: () => <EmptyColumnHeader columnLetter='C' /> },
  { ...EmptyColumn, headerComponent: () => <EmptyColumnHeader columnLetter='D' /> }
]

function doNothing () {}

export default function PlaceholderTable () {
  return (
    <div className='outputpane-table'>
      <div className='outputpane-header'>
        <div className='table-info-container' />
      </div>
      <div className='outputpane-data'>
        <BigTable
          sparseTileGrid={EmptyTileGrid}
          nRows={10}
          columns={EmptyColumns}
          nRowsPerTile={EmptyTileGrid[0][0].length}
          nColumnsPerTile={EmptyTileGrid[0][0][0].length}
          setWantedTileRange={doNothing}
        />
      </div>
    </div>
  )
}
