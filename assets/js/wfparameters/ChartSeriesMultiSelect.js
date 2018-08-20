import React from 'react'
import PropTypes from 'prop-types'
import ChartSeriesSelect from './ChartSeriesSelect'

export default class ChartSeriesMultiSelect extends React.PureComponent {
  static propTypes = {
    series: PropTypes.arrayOf(PropTypes.shape({
      column: PropTypes.string.isRequired,
      color: PropTypes.string.isRequired
    })).isRequired,
    prompt: PropTypes.string.isRequired,
    allColumns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired
    })), // or null if not loaded
    onChange: PropTypes.func.isRequired, // func([{column, color}, ...]) => undefined
    isReadOnly: PropTypes.bool.isRequired,
  }

  state = {
    isAddingPlaceholder: this.props.series.length == 0,
  }

  onChange = ({ index, column, color }) => {
    const series = this.props.series.slice() // shallow copy

    if (index === series.length) {
      // We just overwrote the placeholder
      this.setState({ isAddingPlaceholder: false })
    }

    series[index] = { column, color }
    this.props.onChange(series)
  }

  onClickAddPlaceholder = () => {
    this.setState({ isAddingPlaceholder: true })
  }

  onClickRemoveLast = () => {
    if (this.state.isAddingPlaceholder) {
      this.setState({ isAddingPlaceholder: false })
    } else {
      const series = this.props.series.slice() // shallow copy
      series.pop()
      this.props.onChange(series)
    }
  }

  renderButtons () {
    const { isAddingPlaceholder } = this.state
    const { allColumns, series, isReadOnly } = this.props

    const showAddButton = !isReadOnly && !isAddingPlaceholder && series.length < (allColumns || []).length
    const showRemoveButton = !isReadOnly && (series.length > 1 || series.length === 1 && isAddingPlaceholder)

    if (!showAddButton && !showRemoveButton) {
      return null
    } else {
      const addButton = !showAddButton ? null : (
        <button title="add another column" onClick={this.onClickAddPlaceholder}>
          <i className="icon-addc" />
        </button>
      )

      const removeButton = !showRemoveButton ? null : (
        <button title="remove last column" onClick={this.onClickRemoveLast}>
          <i className="icon-removec" />
        </button>
      )

      return (
        <div className="buttons">
          {removeButton}
          {addButton}
        </div>
      )
    }
  }

  render () {
    const { allColumns, series, prompt, isReadOnly } = this.props

    if (allColumns === null) {
      return <p className="loading">Loading…</p>
    }

    const pickedColumns = series.map(x => x.column)
    const pickers = series.map(({ column, color }, index) => {
      // Don't allow picking a column that's already picked
      const availableColumns = (allColumns || [])
        .filter(({ name }) => pickedColumns.indexOf(name) === -1 || name === column)

      return (
        <ChartSeriesSelect
          key={index}
          index={index}
          prompt={prompt}
          isReadOnly={isReadOnly}
          column={column}
          color={color}
          availableColumns={availableColumns}
          onChange={this.onChange}
        />
      )
    })

    if (this.state.isAddingPlaceholder) {
      const availableColumns = (allColumns || [])
        .filter(({ name }) => pickedColumns.indexOf(name) === -1)

      pickers.push(
        <ChartSeriesSelect
          key={series.length}
          index={series.length}
          prompt={prompt}
          isReadOnly={isReadOnly}
          column={null}
          color={null}
          availableColumns={availableColumns}
          onChange={this.onChange}
        />
      )
    }

    const buttons = this.renderButtons()

    return (
      <div className="wf-parameter chart-series-multi-select">
        {pickers}
        {buttons}
      </div>
    )
  }
}
