/* eslint no-new-func: 0 */
import React from 'react'
import PropTypes from 'prop-types'
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from '../components/Dropdown'
import { connect } from 'react-redux'
import { createSelector } from 'reselect'
import { addModuleAction, setWfModuleParamsAction, setSelectedWfModuleAction } from '../workflow-reducer'
import { Plural, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const numberFormat = new Intl.NumberFormat()

class Action extends React.PureComponent {
  static propTypes = {
    idName: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    onClick: PropTypes.func.isRequired // onClick(idName) => undefined
  }

  handleClick = () => {
    const { idName, onClick } = this.props
    onClick(idName)
  }

  render () {
    return (
      <DropdownItem onClick={this.handleClick}>{this.props.title}</DropdownItem>
    )
  }
}

export class SelectedRowsActions extends React.PureComponent {
  static propTypes = {
    selectedRowIndexes: PropTypes.arrayOf(PropTypes.number.isRequired).isRequired,
    wfModuleId: PropTypes.number, // or null/undefined if none selected
    rowActionModules: PropTypes.arrayOf(PropTypes.shape({
      idName: PropTypes.string.isRequired,
      title: PropTypes.string.isRequired
    }).isRequired).isRequired,
    onClickRowsAction: PropTypes.func.isRequired // func(wfModuleId, moduleIdName, rowString) => undefined
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
        parts.push([curStart, i - 1])
        curStart = null
      }
    }
    if (curStart !== null) {
      parts.push([curStart, maxIndex])
    }

    const partStrings = parts.map(([start, end]) => {
      if (start === end) {
        return String(start + 1)
      } else {
        return `${start + 1}-${end + 1}`
      }
    })

    return partStrings.join(', ')
  }

  handleClickAction = (idName) => {
    const { wfModuleId } = this.props

    this.props.onClickRowsAction(wfModuleId, idName, this.rowString)
  }

  render () {
    const { selectedRowIndexes, wfModuleId, rowActionModules, i18n } = this.props

    const actions = rowActionModules.map(({ idName, title }) => (
      <Action key={idName} idName={idName} title={title} onClick={this.handleClickAction} />
    ))

    const disabled = !wfModuleId || selectedRowIndexes.length === 0

    const rowSelect = disabled ? 'table-action disabled' : 'table-action'

    return (
      <UncontrolledDropdown disabled={disabled}>
        <DropdownToggle title={i18n._(t('js.table.SelectedRowsActions.menu')`menu`)} className={rowSelect}>
          <Plural
            id='js.table.SelectedRowsActions.numberOfSelectedRows'
            value={disabled ? 0 : numberFormat.format(selectedRowIndexes.length)}
            _0='No rows selected'
            one='# row selected'
            other='# rows selected'
          />
        </DropdownToggle>
        <DropdownMenu>
          {actions}
        </DropdownMenu>
      </UncontrolledDropdown>
    )
  }
}

const getModules = ({ modules }) => modules
const getRowActionModules = createSelector([getModules], (modules) => {
  const rowActionModules = []
  for (const moduleIdName in modules) {
    const module = modules[moduleIdName]
    if (module.row_action_menu_entry_title) {
      rowActionModules.push({
        idName: moduleIdName,
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

  const oldParams = { ...wfModule.params } // copy in case module modifies it

  try {
    return addSelectedRows(oldParams, rowsString, fromInput)
  } catch (e) {
    console.warn('Error in module.js_module addSelectedRows()', e)
    return null
  }
}

function ensureWfModuleForRowsAction (currentWfModuleId, moduleIdName, rowsString) {
  return (dispatch, getState) => {
    const { wfModules, tabs, modules } = getState()

    // Fallback behavior: add new module with the given rows.
    function simplyAdd () {
      return dispatch(addModuleAction(
        moduleIdName,
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
    if (currentWfModule.module === moduleIdName) {
      const currentModule = modules[currentWfModule.module]
      const newParams = maybeAddSelectedRowsToParams(currentModule, currentWfModule, rowsString, false)
      if (newParams !== null) {
        return dispatch(setWfModuleParamsAction(currentWfModuleId, newParams))
      }
    }

    const tab = tabs[currentWfModule.tab_slug]

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

    if (nextWfModule.module === moduleIdName) {
      const nextModule = modules[nextWfModule.module]
      const newParams = maybeAddSelectedRowsToParams(nextModule, nextWfModule, rowsString, true)
      if (newParams !== null) {
        dispatch(setSelectedWfModuleAction(nextWfModuleId))
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

export default connect(mapStateToProps, mapDispatchToProps)(withI18n()(SelectedRowsActions))
