import React from 'react'
import PropTypes from 'prop-types'
import UncontrolledDropdown from 'reactstrap/lib/UncontrolledDropdown'
import DropdownToggle from 'reactstrap/lib/DropdownToggle'
import DropdownMenu from 'reactstrap/lib/DropdownMenu'
import DropdownItem from 'reactstrap/lib/DropdownItem'
import { connect } from 'react-redux'
import { createSelector } from 'reselect'
import { addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'

const numberFormat = new Intl.NumberFormat()

class Action extends React.PureComponent {
  static propTypes = {
    id: PropTypes.number.isRequired,
    title: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired, // onClick(id) => undefined
  }

  onClick = () => {
    this.props.onClick(this.props.id)
  }

  render () {
    return (
      <DropdownItem onClick={this.onClick}>
        {this.props.title}
      </DropdownItem>
    )
  }
}

export class SelectedRowsActions extends React.PureComponent {
  static propTypes = {
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired).isRequired,
    wfModuleId: PropTypes.number, // or null/undefined if none selected
    rowActionModules: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      title: PropTypes.string.isRequired
    }).isRequired).isRequired,
    onClickRowsAction: PropTypes.func.isRequired, // func(wfModuleId, moduleId, rowString) => undefined
  }

  get rowString () {
    const indexes = this.props.selectedRowIndexes
    const maxIndex = indexes.reduce((s, i) => Math.max(s, i))

    // Create `bools`, array of booleans, starts empty
    // Think of this like a bitmap
    const bools = []
    for (let i = 0; i <= maxIndex; i++) {
      bools[i] = false
    }

    // Fill in the selected indexes
    for (const selectedIndex of indexes) {
      bools[selectedIndex] = true
    }

    // Fill `parts`, an Array of [start,end] (inclusive) pairs
    const parts = []
    let curStart = null
    for (let i = 0; i <= maxIndex; i++) {
      const bool = bools[i]
      if (curStart === null && bool) {
        curStart = i
      } else if (curStart !== null && !bool) {
        parts.push([ curStart, i - 1])
        curStart = null
      }
    }
    if (curStart !== null) {
      parts.push([ curStart, maxIndex ])
    }

    const partStrings = parts.map(([ start, end ]) => {
      if (start === end) {
        return String(start + 1)
      } else {
        return `${start + 1}-${end + 1}`
      }
    })

    return partStrings.join(', ')
  }

  onClickAction = (idName) => {
    const { wfModuleId } = this.props

    this.props.onClickRowsAction(wfModuleId, idName, this.rowString)
  }

  render () {
    const { selectedRowIndexes, wfModuleId, rowActionModules } = this.props

    const actions = rowActionModules.map(({ id, title }) => (
      <Action key={id} id={id} title={title} onClick={this.onClickAction} />
    ))

    const disabled = !wfModuleId || selectedRowIndexes.length === 0

    const prompt = disabled ? 'No rows selected' : `${numberFormat.format(selectedRowIndexes.length)} rows selected`

    const rowSelect = disabled ? 'table-action disabled' : 'table-action'

    return (
      <UncontrolledDropdown disabled={disabled}>
        <DropdownToggle title='menu' className={rowSelect}>
          {prompt}
        </DropdownToggle>
        <DropdownMenu right>
          {actions}
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}

const getModules = ({ modules }) => modules
const getRowActionModules = createSelector([ getModules ], (modules) => {
  const rowActionModules = []
  for (const key in modules) {
    const module = modules[key]
    if (module.row_action_menu_entry_title) {
      rowActionModules.push({
        id: Number(key),
        title: module.row_action_menu_entry_title
      })
    }
  }
  rowActionModules.sort((a, b) => a.title.localeCompare(b.title))

  return rowActionModules
})

function mapStateToProps (state) {
  const rowActionModules = getRowActionModules(state)

  return { rowActionModules }
}

/**
 * Parse `module.js_module` and return its export named `exportName`.
 *
 * On error, warn. If the export can't be loaded, return `null`.
 *
 * This is a _trivial_ module loader: it calls the JavaScript as a function
 * with a `module` parameter, expecting the module to set
 * `module.exports = {...}`. It's like CommonJS, without `define` or `require`.
 * It should be compatible with bundlers. But there's no dynamic loading: we
 * send all modules' JavaScript to the client every page load.
 */
function loadModuleExport (module, exportName) {
  if (!module.js_module) return null
  const jsModule = {}
  try {
    // Load the module
    const jsWrapper = new Function('module', module.js_module)
    // Execute it (so it sets module.exports)
    jsWrapper(jsModule)

    if (!jsModule.exports) {
      throw new Error('Module did not write `module.exports`')
    }
  } catch (e) {
    console.warn('Error loading module.js_module', e)
    return null
  }

  return jsModule.exports[exportName] || null
}

/**
 * Execute `module`'s `addSelectedRows()` and return its result.
 *
 * If `addSelectedRows()` is not defined for the module, return `null`.
 *
 * If `addSelectedRows()` throws an error, warn and return `null`.
 */
function maybeAddSelectedRowsToParams (module, wfModule, rowsString, fromInput) {
  const addSelectedRows = loadModuleExport(module, 'addSelectedRows')
  if (!addSelectedRows) return null

  const oldParams = {}
  for (const pv of wfModule.parameter_vals) {
    oldParams[pv.parameter_spec.id_name] = pv.value
  }

  try {
    return addSelectedRows(oldParams, rowsString, fromInput)
  } catch (e) {
    console.warn('Error in module.js_module addSelectedRows()', e)
    return null
  }
}

function ensureWfModuleForRowsAction(currentWfModuleId, moduleId, rowsString) {
  return (dispatch, getState) => {
    const { workflow, wfModules, tabs, modules } = getState()

    // Fallback behavior: add new module with the given rows.
    function simplyAdd () {
      return dispatch(addModuleAction(
        moduleId,
        { afterWfModuleId: currentWfModuleId },
        { rows: rowsString }
      ))
    }

    // Does currentWfModuleId point to the very module we're asking to add?
    // e.g., are we clicking "Delete rows" from the "Delete rows" output?
    //
    // If so -- and if the module has support.js defining addSelectedRows() --
    // modify the current WfModule.
    const currentWfModule = wfModules[String(currentWfModuleId)]
    const currentModule = modules[String(currentWfModule.module_version.module)]
    if (currentModule && currentModule.id === moduleId) {
      const newParams = maybeAddSelectedRowsToParams(currentModule, currentWfModule, rowsString, false)
      if (newParams !== null) {
        return dispatch(setWfModuleParamsAction(currentWfModuleId, newParams))
      }
    }

    const tab = tabs[String(workflow.tab_ids[workflow.selected_tab_position])]

    // Does nextWfModuleId point to the very module we're asking to add?
    // e.g., did we delete rows, select the input, and delete more rows?
    //
    // If so -- and if the module has support.js defining addSelectedRows() --
    // modify the current module.
    const index = tab.wf_module_ids.indexOf(currentWfModuleId)
    if (index === -1) return simplyAdd()
    const nextWfModuleId = tab.wf_module_ids[index + 1]
    if (!nextWfModuleId) return simplyAdd()
    const nextWfModule = wfModules[String(nextWfModuleId)]
    if (!nextWfModule) return simplyAdd()
    const nextModule = modules[String(nextWfModule.module_version.module)]
    if (nextModule && nextModule.id === moduleId) {
      const newParams = maybeAddSelectedRowsToParams(nextModule, nextWfModule, rowsString, true)
      if (newParams !== null) {
        dispatch(setSelectedWfModuleAction(index + 1))
        return dispatch(setWfModuleParamsAction(nextWfModuleId, newParams))
      }
    }

    return simplyAdd()
  }
}

const mapDispatchToProps = (dispatch) => {
  return {
    onClickRowsAction: (...args) => dispatch(ensureWfModuleForRowsAction(...args))
  }
}

export default connect(mapStateToProps, mapDispatchToProps)(SelectedRowsActions)
