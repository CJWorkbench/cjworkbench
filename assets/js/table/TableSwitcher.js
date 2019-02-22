import React from 'react'
import PropTypes from 'prop-types'
import TableView, {NMaxColumns} from './TableView'

function areSameTable(props1, props2) {
  if (props1 === null && props2 === null) return true // both null => true
  if ((props1 === null) !== (props2 === null)) return false // one null => false

  return props1.wfModuleId === props2.wfModuleId
    && props1.deltaId === props2.deltaId
    && props1.nRows === props2.nRows
}

/**
 * Given props, return the props we'll pass to <TableView>.
 */
function tableProps (props) {
  const ret = {}
  for (const key of [ 'wfModuleId', 'deltaId', 'columns', 'nRows', 'sortColumn', 'sortDirection' ]) {
    ret[key] = props[key]
  }
  return ret
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
    sortColumn: PropTypes.string,
    sortDirection: PropTypes.number
  }

  state = {
    loaded: null // { wfModuleId, deltaId, nRows, columns } of a table that has rendered something, sometime
  }

  static getDerivedStateFromProps (props) {
    if (props.wfModuleId === null) {
      return { loaded: null }
    } else if (props.nRows !== null && (props.nRows === 0 || props.columns.length > NMaxColumns)) {
      return { loaded: tableProps(props) }
    } else {
      return null
    }
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
        { name: ' ', type: 'text' },
        { name: '  ', type: 'text' },
        { name: '   ', type: 'text' },
        { name: '    ', type: 'text' }
      ],
      nRows: 10,
    }, 'placeholder-table')
  }

  onLoadPage = (wfModuleId, deltaId) => {
    if (wfModuleId === this.props.wfModuleId && deltaId === this.props.deltaId && !areSameTable(this.props, this.state.loaded)) {
      // We have data for our currently-loading table. Mark it "loaded."
      this.setState({ loaded: tableProps(this.props) })
    }
  }

  render () {
    const { loaded } = this.state

    let className = 'table-switcher'
    const tables = []

    // Always show the placeholder. It's for when there's no data on top.
    tables.push(this._renderPlaceholderTable())

    // Show the last table that has data visible
    if (loaded) {
      className += ' has-loaded'
      tables.push(this._renderTable(loaded, 'loaded-table'))
    }

    let loading = false
    // Do not render zero-row tables: render a placeholder instead
    // Helps #161166382, hinders #160865813
    if (this.props.nRows !== null && this.props.nRows > 0 && !areSameTable(this.props, loaded)) {
      loading = true
      className += ' has-loading'
      tables.push(this._renderTable({
        ...this.props,
        onLoadPage: this.onLoadPage
      }, 'loading-table'))
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
