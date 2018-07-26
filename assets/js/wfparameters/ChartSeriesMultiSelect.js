import React from 'react'
import PropTypes from 'prop-types'
import ChartSeriesSelect from './ChartSeriesSelect'

export default class ChartSeriesMultiSelect extends React.PureComponent {
  static propTypes = {
    workflowRevision: PropTypes.number.isRequired,
    series: PropTypes.arrayOf(PropTypes.shape({
      column: PropTypes.string.isRequired,
      color: PropTypes.string.isRequired
    })).isRequired,
    prompt: PropTypes.string.isRequired,
    fetchInputColumns: PropTypes.func.isRequired, // func() => Promise[Array[String]]
    onChange: PropTypes.func.isRequired, // func([{column, color}, ...]) => undefined
    isReadOnly: PropTypes.bool.isRequired,
  }

  state = {
    allColumns: null,
    allColumnsWorkflowRevision: null,
    allColumnsFetchError: null,
    isAddingPlaceholder: this.props.series.length == 0,
  }

  componentDidMount () {
    this.mounted = true

    this.refreshAllColumns()
  }

  componentDidUpdate (prevProps) {
    if (prevProps.workflowRevision !== this.props.workflowRevision) {
      this.refreshAllColumns()
    }
  }

  refreshAllColumns () {
    const setState = (state) => {
      if (this.mounted) this.setState(state)
    }

    if (this.state.allColumnsWorkflowRevision !== this.props.workflowRevision || (this.state.allColumns === null && this.state.allColumnsFetchError === null)) {
      this.setState({
        allColumnsWorkflowRevision: this.props.workflowRevision,
        allColumns: null,
        allColumnsFetchError: null
      })
      this.props.fetchInputColumns()
        .then(allColumns => setState({ allColumns }))
        .catch(err => setState({ allColumnsFetchError: err }))
    }
  }

  componentWillUnmount () {
    this.mounted = false
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
    const { isAddingPlaceholder, allColumns } = this.state
    const { series, isReadOnly } = this.props

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
    const { allColumns, allColumnsFetchError } = this.state
    const { series, prompt, isReadOnly } = this.props

    if (allColumns === null && allColumnsFetchError === null) {
      return <p className="loading">Loading…</p>
    }

    if (allColumnsFetchError !== null) {
      return <p className="error">Failed to fetch column names</p>
    }

    const pickedColumns = series.map(x => x.column)
    const pickers = series.map(({ column, color }, index) => {
      // Don't allow picking a column that's already picked
      const availableColumns = allColumns
        .filter(x => pickedColumns.indexOf(x.column) === -1 || x.column === column)

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
      const availableColumns = allColumns
        .filter(x => pickedColumns.indexOf(x.column) === -1)

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
