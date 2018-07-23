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
    fetchInputColumns: PropTypes.func.isRequired, // func() => Promise[Array[String]]
    onChange: PropTypes.func.isRequired // func([{column, color}, ...]) => undefined
  }

  state = {
    allColumns: null,
    allColumnsWorkflowRevision: null,
    allColumnsFetchError: null,
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
    series[index] = { column, color }
    this.props.onChange(series)
  }

  render() {
    const { allColumns, allColumnsFetchError } = this.state
    const { series } = this.props

    if (allColumns === null && allColumnsFetchError === null) {
      return <p className="loading">Loading…</p>
    }

    if (allColumnsFetchError !== null) {
      return <p className="error">Failed to fetch column names</p>
    }

    const pickedColors = series.map(x => x.column)
    const pickers = series.map(({ column, color }, index) => {
      // Don't allow picking a column that's already picked
      const availableColumns = allColumns
        .filter(x => pickedColors.indexOf(x.column) === -1 || x.column === column)

      return (
        <ChartSeriesSelect
          key={index}
          index={index}
          column={column}
          color={color}
          availableColumns={availableColumns}
          onChange={this.onChange}
        />
      )
    })

    if (allColumns.length > series.length) {
      // Don't allow picking a column that's already picked
      const availableColumns = allColumns
        .filter(x => pickedColors.indexOf(x.column) === -1)

      pickers.push(
        <ChartSeriesSelect
          key={series.length}
          index={series.length}
          column={null}
          color={null}
          availableColumns={availableColumns}
          onChange={this.onChange}
        />
      )

      return (
        <React.Fragment>
          {pickers}
        </React.Fragment>
      )
    }
  }
}
