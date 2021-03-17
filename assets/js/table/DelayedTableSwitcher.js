/* global requestAnimationFrame */
import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import TableSwitcher from './TableSwitcher'

function areSameTable (props1, props2) {
  if (props1 === null && props2 === null) return true // both null => true
  if ((props1 === null) !== (props2 === null)) return false // one null => false

  return props1.stepSlug === props2.stepSlug && props1.deltaId === props2.deltaId
}

/**
 * Given props, return the React "key".
 *
 * This forces React to re-render new tables and saves React from re-rendering
 * when switching from "loading" to "loaded".
 */
function tableKey ({ stepSlug, deltaId }) {
  return `table-${stepSlug}-${deltaId}`
}

/**
 * Given props, return the props we'll pass to <TableSwitcher>.
 */
function tableProps ({ workflowId, stepSlug, stepId, deltaId, columns, nRows, status }) {
  return { workflowId, stepSlug, stepId, deltaId, columns, nRows, status }
}

/**
 * Shows a <TableSwitcher> for the given step+deltaId -- and transitions
 * when those props change.
 *
 * The transition is: this.state maintains a "last-loaded" step+deltaId.
 * When we switch to a new step+deltaId that has not yet loaded (or has
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
 *   </div>
 *
 * this.state holds the _loaded_ table. this.props holds the _loading_ table.
 *
 * Behind the state, a table in `this.props` goes through three stages:
 *
 * 1. Rendered straight from props to `"loading-table"`. This table should be
 *    invisible: <DataGrid> waits a tick before rendering, so the <Spinner>
 *    will appear to the user before <ReactDataGrid> starts drawing columns
 *    (which can be painfully slow -- >1s).
 * 2. One tick later: <DataGrid> actually sets <ReactDataGrid> size correctly.
 *    At this point, if `nRows>0` we're "loading"; otherwise we're...:
 * 3. In `state.loaded`.
 *
 * This file calls the phase between stages 1 and 2 `state.oneTickFromLoaded`.
 */
export default class DelayedTableSwitcher extends PureComponent {
  isUnmounted = false

  static propTypes = {
    loadRows: PropTypes.func.isRequired, // func(workflowId, stepSlug, deltaId, startRowInclusive, endRowExclusive) => Promise[Array[Object] or error]
    isReadOnly: PropTypes.bool.isRequired,
    workflowId: PropTypes.number.isRequired,
    stepSlug: PropTypes.string, // or null, if no selection
    stepId: PropTypes.number, // or null, if no selection; deprecated
    deltaId: PropTypes.number, // or null, if status!=ok
    status: PropTypes.oneOf(['ok', 'busy', 'unreachable']), // null if no selection
    columns: PropTypes.arrayOf(
      PropTypes.shape({
        name: PropTypes.string.isRequired,
        type: PropTypes.oneOf(['text', 'timestamp', 'number']).isRequired
      }).isRequired
    ), // or null, if status!=ok
    nRows: PropTypes.number // or null, if status!=ok
  }

  state = {
    loaded: null, // { stepId, deltaId, status, nRows, columns } of a table that has rendered something, sometime
    oneTickFromLoaded: null // { stepId, deltaId, status, nRows, columns } of a table for which data is already loaded, but we need to render it for a tick otherwise <DataGrid> will flicker
  }

  _afterOneTickFromLoaded = () => {
    const { oneTickFromLoaded } = this.state
    // TODO nix react-data-grid, so we don't have to do this deferred-render
    // hack and we can nix the this.isUnmounted check.
    if (oneTickFromLoaded && !this.isUnmounted) {
      this.setState({
        loaded: oneTickFromLoaded,
        oneTickFromLoaded: null
      })
    }
  }

  componentDidUpdate (_, prevState) {
    if (this.state.oneTickFromLoaded && !prevState.oneTickFromLoaded) {
      requestAnimationFrame(this._afterOneTickFromLoaded)
    }
  }

  componentDidMount () {
    this._afterOneTickFromLoaded()
  }

  componentWillUnmount () {
    this.isUnmounted = true
  }

  static getDerivedStateFromProps (props, state) {
    // If new props aren't changing the table, don't change the state
    if (areSameTable(props, state.loaded)) return { oneTickFromLoaded: null }

    if (props.status === 'ok' && props.nRows > 0) {
      return { oneTickFromLoaded: null } // table needs loading; loadRows() will set state.loaded
    } else if (props.status === 'busy') {
      return { oneTickFromLoaded: null } // table needs rendering (and maybe _after_ that, loading); we'll set new status later
    } else {
      return { oneTickFromLoaded: tableProps(props) } // table just needs a single tick; then we'll move it to .loaded
    }
  }

  /**
   * Call this.prop.loadRows() and ensure state.loaded is set after it returns.
   */
  loadRows = (workflowId, stepSlug, deltaId, startRow, endRow) => {
    return this.props
      .loadRows(workflowId, stepSlug, deltaId, startRow, endRow)
      .finally(() => {
        if (
          workflowId === this.props.workflowId &&
          stepSlug === this.props.stepSlug &&
          deltaId === this.props.deltaId &&
          !areSameTable(this.props, this.state.loaded) &&
          // TODO nix react-data-grid, so we don't have to do this deferred-render
          // hack and we can nix the this.isUnmounted check.
          !this.isUnmounted
        ) {
          // We have data for our currently-loading table. Mark it "loaded".
          this.setState({ loaded: tableProps(this.props) })
        }
      })
  }

  render () {
    const { isReadOnly } = this.props
    const { loaded } = this.state

    let className = 'table-switcher'

    // Show the last table that has data visible (from state)
    //
    // If input props have stepId=null, that's a "loaded" table -- an
    // empty-looking one.
    if (loaded) className += ' has-loaded'

    // Show requested table afterwards -- styled differently (and on top)
    //
    // It's always the case that `!!loading || !!loaded`
    const loading = !areSameTable(this.props, loaded)
    if (loading) className += ' has-loading'

    // Notice the nifty optimization: we make sure React will not redraw a
    // table when switching from "loading" to "loaded": its `key` will remain
    // the same.
    //
    // TODO when we switch off react-data-grid, the "loading" table should be
    // read-only no matter what. Currently we can't do that, because
    // react-data-grid won't notice the change if we start with isReadOnly=true
    // and later set isReadOnly=false
    return (
      <div className={className}>
        {loaded
          ? (
            <TableSwitcher
              isReadOnly={isReadOnly}
              isLoaded
              key={tableKey(loaded)}
              loadRows={this.loadRows}
              {...loaded}
            />
            )
          : null}
        {loading
          ? (
            <TableSwitcher
              isReadOnly={isReadOnly}
              isLoaded={false}
              key={tableKey(this.props)}
              loadRows={this.loadRows}
              {...tableProps(this.props)}
            />
            )
          : null}
      </div>
    )
  }
}
