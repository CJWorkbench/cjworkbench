import React from 'react'
import { Cell } from 'react-data-grid'

// Constants help tone down garbage collection
const NormalClassName = 'react-grid-Cell'
const LockedClassName = 'react-grid-Cell react-grid-Cell--locked'

export default class CellWithoutGarbage extends Cell {
  renderCellContent = (props) => {
    const Formatter = this.getFormatter()
    let content

    if (React.isValidElement(Formatter)) {
      content = React.cloneElement(Formatter, props)
    } else {
      content = <Formatter value={this.props.value} />
    }

    return (
      <div className='react-grid-Cell__value'>{content}</div>
    )
  }

  storeRef = (node) => { this.node = node }

  render () {
    const { value, column, rowIdx } = this.props

    // Mostly a copy/paste job to nix drag-handle. See
    // https://github.com/adazzle/react-data-grid/issues/822
    const style = {
      width: column.width,
      left: column.left
    }

    const className = column.locked ? LockedClassName : NormalClassName

    const cellContent = this.props.children || this.renderCellContent({
      value: value,
      column: column,
      rowIdx: rowIdx
    })

    return (
      <div
        className={className}
        tabIndex='0'
        style={style}
        onClick={this.onCellClick}
        onFocus={this.onCellFocus}
        onDoubleClick={this.onCellDoubleClick}
        onContextMenu={this.onCellContextMenu}
        ref={this.storeRef}
      >
        {cellContent}
      </div>
    )
  }
}
