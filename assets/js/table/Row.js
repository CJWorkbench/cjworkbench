import React from 'react'
import { Row } from 'react-data-grid'
import Cell from './Cell'

export default class RowWithoutCellGarbageOrCellKeyConflicts extends Row {
  static defaultProps = {
    ...Row.defaultProps
  }

  actionCellRef = React.createRef()

  getCell = (column, i, selectedColumn) => {
    // work around https://github.com/adazzle/react-data-grid/issues/1269
    const { idx, cellMetaData, row, isSelected, isScrolling } = this.props
    const { key, formatter } = column
    // another fix for 1269 is the new value={this.getCellValue(key, i)}
    return (
      <Cell
        key={`${key}-${i}`}
        idx={i}
        rowIdx={idx}
        height={35}
        column={column}
        cellMetaData={cellMetaData}
        ref={i === 0 ? this.actionCellRef : null}
        value={this.getCellValue(key, i)}
        rowData={row}
        isRowSelected={isSelected}
        selectedColumn={selectedColumn}
        formatter={formatter}
        isScrolling={isScrolling}
      />
    )
  }

  getCellValue = (key, columnIndex) => {
    // Another fix for https://github.com/adazzle/react-data-grid/issues/1269
    if (columnIndex === 0 && key === 'select-row') {
      // ... assumes row-select is always enabled
      return this.props.isSelected
    } else {
      return this.props.row[key]
    }
  }

  setScrollLeft = (scrollLeft) => {
    // work around https://github.com/adazzle/react-data-grid/issues/1270
    this.actionCellRef.current.setScrollLeft(scrollLeft)
  }

  render () {
    const { idx, isSelected } = this.props

    const className = `react-grid-Row react-grid-Row--${idx % 2 === 0 ? 'even' : 'odd'} ${isSelected ? 'row-selected' : ''}`
    const cells = this.getCells()
    return (
      <div className={className}>
        {cells}
      </div>
    )
  }
}
