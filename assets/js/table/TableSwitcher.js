import React from 'react'
import PropTypes from 'prop-types'
import TableView from './TableView'

function areSameTable(props1, props2) {
  if (props1 === null && props2 === null) return true // both null => true
  if ((props1 === null) !== (props2 === null)) return false // one null => false

  return props1.wfModuleId === props2.wfModuleId
    && props1.deltaId === props2.deltaId
    && props1.nRows === props2.nRows
}

function noop () {}

/**
 * Shows a <TableView> for the given wfModule+deltaId -- and transitions
 * when those props change.
 *
 * The transition is: this.state maintains a "last-loaded" wfModule+deltaId.
 * When we switch to a new wfModule+deltaId that has not yet loaded (or has
 * nRows===null), we keep that stale table visible atop the new, unloaded one
 * and we show a spinner.
 *
 *   <div className="table-switcher">
 *     <div className="loaded-table">
 *       <TableView ... /> <!-- last table we've seen with data -->
 *     </div>
 *     <div className="loading-table">
 *       <TableView ... /> <!-- next table -- when it loads, we'll move it -->
 *     </div>
 *     <Spinner ... />
 *   </div>
 */
export default class TableSwitcher extends React.PureComponent {
  static propTypes = {
    api: PropTypes.object.isRequired,
    isReadOnly: PropTypes.bool.isRequired,
    wfModuleId: PropTypes.number, // or null, if no selection
    deltaId: PropTypes.number, // or null, if status!=ok
    columns: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      type: PropTypes.oneOf([ 'text', 'datetime', 'number' ]).isRequired
    }).isRequired), // or null, if status!=ok
    nRows: PropTypes.number, // or null, if status!=ok
    showColumnLetter: PropTypes.bool.isRequired,
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number
  }

  state = {
    loaded: null // { wfModuleId, deltaId, nRows, columns } of a table that has rendered something, sometime
  }

  /**
   * Render a <TableView>, with a `key` tied to wfModuleId+deltaId so tables
   * are guaranteed to never share data.
   */
  _renderTable (props, className) {
    const { wfModuleId, deltaId } = props
    const { api, isReadOnly } = this.props

    return (
      <div key={`${wfModuleId}-${deltaId}`} className={className}>
        <TableView api={api} isReadOnly={isReadOnly} onLoadPage={noop} {...props} />
      </div>
    )
  }

  // Empty grid, big enough to fill screen.
  // 10 rows by four blank columns (each with a different number of spaces, for
  // unique names)
  _renderPlaceholderTable () {
    return this._renderTable({
      wfModuleId: null,
      deltaId: null,
      columns: [
        { name: ' ', type: '' },
        { name: '  ', type: '' },
        { name: '   ', type: '' },
        { name: '    ', type: '' }
      ],
      nRows: 10,
      showColumnLetter: false
    }, 'placeholder-table')
  }

  onLoadPage = (wfModuleId, deltaId) => {
    if (wfModuleId === this.props.wfModuleId && deltaId === this.props.deltaId && !areSameTable(this.props, this.state.loaded)) {
      // We have data for our currently-loading table. Mark it "loaded."
      const loaded = {}
      for (const key of [ 'wfModuleId', 'deltaId', 'columns', 'nRows', 'showColumnLetter', 'sortColumn', 'sortDirection' ]) {
        loaded[key] = this.props[key]
      }
      this.setState({ loaded })
    }
  }

  render () {
    const { loaded } = this.state

    let className = 'table-switcher'
    const tables = []

    if (loaded) {
      className += ' has-loaded'
      tables.push(this._renderTable(loaded, 'loaded-table'))
    }

    let loading = false
    if (this.props.nRows !== null && !areSameTable(this.props, loaded)) {
      loading = true
      className += ' has-loading'
      tables.push(this._renderTable({
        ...this.props,
        onLoadPage: this.onLoadPage
      }, 'loading-table'))
    }

    if (tables.length === 0) {
      className += ' has-placeholder'
      tables.push(this._renderPlaceholderTable())
    }

    return (
      <div className={className}>
        {tables}
        {!loading ? null : (
          <div key='spinner' className="spinner-container-transparent">
            <div className="spinner-l1">
              <div className="spinner-l2">
                <div className="spinner-l3"></div>
              </div>
            </div>
          </div>
        )}
      </div>
    )
  }
}
