import React from 'react'
import { Row, Cell } from 'react-data-grid'

class CellWithoutGarbage extends Cell {
  renderCellContent = (props) => {
    const Formatter = this.getFormatter()
    let content

    if (React.isValidElement(Formatter)) {
      props.dependentValues = this.getFormatterDependencies();
      content = React.cloneElement(Formatter, props);
    } else {
      content = <Formatter value={this.props.value} dependentValues={this.getFormatterDependencies()} />
    }


    return (
      <div className='react-grid-Cell__value'>{content}</div>
    )
  }

  render () {
    // Mostly a copy/paste job to nix drag-handle. See 
    // https://github.com/adazzle/react-data-grid/issues/822

    const style = this.getStyle()
    const className = this.getCellClass()
    const cellContent = this.props.children || this.renderCellContent({
      value: this.props.value,
      column: this.props.column,
      rowIdx: this.props.rowIdx,
      isExpanded: this.props.isExpanded
    })
    const events = this.getEvents()
    return (
      <div {...this.getKnownDivProps()} className={className} style={style} {...events} ref={(node) => { this.node = node }}>
        {cellContent}
      </div>
    )
  }
}

export default class RowWithoutCellGarbageOrCellKeyConflicts extends Row {
  static defaultProps = {
    ...Row.defaultProps,
    cellRenderer: CellWithoutGarbage
  }

  cellRefs = {}

  getCell = (column, i, selectedColumn) => {
    // work around https://github.com/adazzle/react-data-grid/issues/1269
    // ... when the bug is fixed, delete this function.
    let CellRenderer = this.props.cellRenderer;
    const { colVisibleStart, colVisibleEnd, idx, cellMetaData } = this.props;
    const { key, formatter, locked } = column;
    const baseCellProps = { key: `${key}-${i}`, idx: i, rowIdx: idx, height: this.getRowHeight(), column, cellMetaData };

    //if ((i < colVisibleStart || i > colVisibleEnd) && !locked) {
    //  return <OverflowCell ref={(node) => this.cellRefs[key] = node} {...baseCellProps} />;
    //}

    const { row, isSelected } = this.props;
    const cellProps = {
      ref: (node) => this.cellRefs[key] = node,
      value: this.getCellValue(key, i), // another fix for 1269
      rowData: row,
      isRowSelected: isSelected,
      expandableOptions: this.getExpandableOptions(key),
      selectedColumn,
      formatter,
      isScrolling: this.props.isScrolling
    };
    return <CellRenderer {...baseCellProps} {...cellProps} />;
  }

  getCellValue = (key, columnIndex) => {
    // Another fix for https://github.com/adazzle/react-data-grid/issues/1269
    if (columnIndex === 0 && key === 'select-row') {
			// ... assumes row-select is always enabled
      return this.props.isSelected;
    } else if (typeof this.props.row.get === 'function') {
      return this.props.row.get(key);
    } else {
      return this.props.row[key];
    }
  }

  setScrollLeft = (scrollLeft) => {
    // work around https://github.com/adazzle/react-data-grid/issues/1270
    // ... when the bug is fixed, delete this function.
    this.props.columns.forEach((column) => {
      if (column.locked) {
        if (!this.cellRefs[column.key]) return;
        this.cellRefs[column.key].setScrollLeft(scrollLeft);
      }
    })
  }
}
