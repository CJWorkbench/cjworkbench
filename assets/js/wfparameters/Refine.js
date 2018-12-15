import React from 'react'
import PropTypes from 'prop-types'
import RefineModal from '../refine/RefineModal'
import { withFetchedData } from './FetchedData'

const NumberFormatter = new Intl.NumberFormat()

export class RefineSpec {
  constructor (renames, blacklist) {
    this.renames = renames
    this.blacklist = blacklist
  }

  toJsonString () {
    return JSON.stringify({
      renames: this.renames,
      blacklist: this.blacklist
    })
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `name`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   * * `isBlacklisted`: true if we are omitting this group from output
   */
  buildGroupsForValueCounts (valueCounts) {
    const { renames, blacklist } = this

    const groupNames = []
    const groupsByName = {}
    const allValues = Object.keys(valueCounts || {})
    for (const value of allValues) {
      const count = valueCounts[value]
      const groupName = value in renames ? renames[value] : value

      if (groupName in groupsByName) {
        const group = groupsByName[groupName]
        group.values.push(value)
        group.count += count
      } else {
        groupNames.push(groupName)
        groupsByName[groupName] = {
          name: groupName,
          values: [ value ],
          count: count,
          isBlacklisted: false // for now
        }
      }
    }

    // Blacklist groups
    for (const groupName of blacklist) {
      if (groupName in groupsByName) {
        groupsByName[groupName].isBlacklisted = true
      }
    }

    // Sort groups, highest count to lowest
    groupNames.sort((a, b) => (groupsByName[b].count - groupsByName[a].count) || a.localeCompare(b))

    const groups = groupNames.map(g => groupsByName[g])

    return groups
  }

  rename (fromGroup, toGroup) {
    return this.massRename({ [fromGroup]: toGroup })
  }

  massRename (groupMap) {
    const { renames, blacklist } = this
    const newRenames = Object.assign({}, renames)

    // Start with blacklist as a "Set": { groupA: null, groupB: null, ... }
    const oldBlacklistSet = {}
    for (const group of blacklist) {
      oldBlacklistSet[group] = null
    }
    const newBlacklistSet = Object.assign({}, oldBlacklistSet)

    // Rewrite every value=>fromGroup to be value=>toGroup
    for (const oldValue in renames) {
      const oldGroup = renames[oldValue]
      if (oldGroup in groupMap) {
        const toGroup = groupMap[oldGroup]
        newRenames[oldValue] = toGroup

        // Rename a blacklist entry if we need to
        if (oldGroup in oldBlacklistSet) {
          delete newBlacklistSet[oldGroup]
          newBlacklistSet[toGroup] = null
        }
      }
    }

    // Now do the simple rewrite of fromGroup=>toGroup
    for (const fromGroup in groupMap) {
      if (!(fromGroup in newRenames)) {
        const toGroup = groupMap[fromGroup]
        newRenames[fromGroup] = toGroup

        if (fromGroup in oldBlacklistSet) {
          delete newBlacklistSet[fromGroup]
          newBlacklistSet[toGroup] = null
        }
      }
    }

    const newBlacklist = Object.keys(newBlacklistSet)

    return new RefineSpec(newRenames, newBlacklist)
  }

  resetGroup (group) {
    const { renames, blacklist } = this

    const newRenames = Object.assign({}, renames)
    const newBlacklist = blacklist.filter(g => g !== group)

    for (const key in renames) {
      if (renames[key] === group) {
        delete newRenames[key]
      }
    }

    return new RefineSpec(newRenames, newBlacklist)
  }

  resetValue (value) {
    const { renames, blacklist } = this

    const newRenames = Object.assign({}, renames)
    delete newRenames[value]

    // This _might_ remove a group. If it does, we need to remove that from
    // blacklist. So let's track all the groups.
    const newGroups = {}
    for (const key in newRenames) {
      newGroups[newRenames[key]] = null
    }

    const newBlacklist = blacklist.filter(g => g in newGroups)

    return new RefineSpec(newRenames, newBlacklist)
  }

  setIsBlacklisted (group, isBlacklisted) {
    const newBlacklist = this.blacklist.slice()

    const index = newBlacklist.indexOf(group)
    if (index === -1) {
      // Add to blacklist
      newBlacklist.push(group)
    } else {
      // Remove from blacklist
      newBlacklist.splice(index, 1)
    }

    return new RefineSpec(this.renames, newBlacklist)
  }

  withBlacklist (newBlacklist) {
    return new RefineSpec(this.renames, newBlacklist)
  }

  static parse_v0 (arr) {
    // See comments in modules/refine.py
    let spec = new RefineSpec({}, [])

    for (const action of arr) {
      if (action.type === 'select') {
        // Toggle isBlacklisted for the given group
        const group = action.content.value
        const isBlacklisted = spec.blacklist.includes(group)
        spec = spec.setIsBlacklisted(group, !isBlacklisted)
      } else {
        // Rename from oldValue to newValue
        const fromGroup = action.content.fromVal
        const toGroup = action.content.toVal
        spec = spec.rename(fromGroup, toGroup)
      }
    }

    return spec
  }

  static parse_v1 (obj) {
    const { renames, blacklist } = obj

    return new RefineSpec(renames, blacklist)
  }

  static parse (json) {
    if (json == '') {
      return new RefineSpec({}, [])
    }

    const data = JSON.parse(json)
    if (Array.isArray(data)) {
      return RefineSpec.parse_v0(data)
    } else {
      return RefineSpec.parse_v1(data)
    }
  }
}

/**
 * Displays a <button> prompt that opens a Modal.
 */
class RefineModalPrompt extends React.PureComponent {
  static propTypes = {
    groups: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired,
      count: PropTypes.number.isRequired
    }).isRequired).isRequired,
    massRename: PropTypes.func.isRequired, // func({ oldGroup: newGroup, ... }) => undefined
  }

  get bucket () {
    const groups = this.props.groups
    const ret = {}
    for (const group of groups) {
      ret[group.name] = group.count
    }
    return ret
  }

  state = {
    isModalOpen: false
  }

  openModal = () => {
    this.setState({ isModalOpen: true })
  }

  closeModal = () => {
    this.setState({ isModalOpen: false })
  }

  onSubmit = (renames) => {
    this.closeModal()
    this.props.massRename(renames)
  }

  render () {
    const { isModalOpen } = this.state
    const { groups } = this.props

    // Hide modal when there aren't enough groups
    if (groups.length < 2 && !isModalOpen) return null

    return (
      <div className='refine-modal-prompt'>
        <button name='cluster' onClick={this.openModal}>Auto cluster</button>
        <span className='instructions'></span>
        { !isModalOpen ? null : (
          <RefineModal
            bucket={this.bucket}
            onClose={this.closeModal}
            onSubmit={this.onSubmit}
          />
        )}
      </div>
    )
  }
}

class RefineGroup extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    isVisible: PropTypes.bool.isRequired,
    name: PropTypes.string, // new value -- may be empty string
    values: PropTypes.arrayOf(PropTypes.string).isRequired, // sorted by count, descending -- may be empty
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isBlacklisted: PropTypes.bool.isRequired,
    onChangeName: PropTypes.func.isRequired, // func(oldName, newName) => undefined
    onChangeIsBlacklisted: PropTypes.func.isRequired, // func(name, isBlacklisted) => undefined
    onResetGroup: PropTypes.func.isRequired, // func(name) => undefined
    onResetValue: PropTypes.func.isRequired // func(value) => undefined
  }

  state = {
    name: this.props.name,
    isExpanded: false
  }

  onChangeName = (ev) => {
    this.setState({ name: ev.target.value })
  }

  onBlurName = () => {
    if (this.props.name !== this.state.name) {
      this.props.onChangeName(this.props.name, this.state.name)
    }
  }

  onChangeIsBlacklisted = (ev) => {
    this.props.onChangeIsBlacklisted(this.props.name, !ev.target.checked)
  }

  onChangeIsExpanded = (ev) => {
    this.setState({ isExpanded: ev.target.checked })
  }

  onKeyDown = (ev) => {
    switch (ev.keyCode) {
      case 27: // Escape
        return this.setState({ value: this.props.name })
      case 13: // Enter
        return this.props.onChangeName(this.props.name, this.state.name)
      // else do nothing special
    }
  }

  onClickRemove = (ev) => {
    this.props.onResetValue(ev.target.getAttribute('data-value'))
  }

  onClickReset = (ev) => {
    this.props.onResetGroup(this.props.name)
  }

  render () {
    const { name, isExpanded } = this.state
    const { count, values, valueCounts, isVisible } = this.props

    // isOriginal uses this._props_.name, not this._state_. The group the
    // buttons would modify is this.props.name.
    const isOriginal = values.length === 1 && values[0] === this.props.name
    const className=`${isVisible ? 'visible' : 'not-visible'} ${isOriginal ? 'original' : 'edited'}`

    const maybeExpandCheckbox = isOriginal ? null : (
      <label className='expand'>
        <input
          type='checkbox'
          name='expand'
          title={isExpanded ? 'Hide original values' : 'Show original values'}
          checked={isExpanded}
          onChange={this.onChangeIsExpanded}
        />
        <i className={isExpanded ? 'icon-caret-down' : 'icon-caret-right'} />
      </label>
    )

    const maybeResetButton = isOriginal ? null : (
      <button
        name='reset'
        title='Cancel edits of these values'
        onClick={this.onClickReset}
      >
        <i className='icon-undo' />
      </button>
    )

    const maybeValues = (isOriginal || !isExpanded) ? null : (
      <ul className='values'>
        {values.sort((a, b) => a.localeCompare(b)).map(value => (
          <li key={value}>
            <span className='value'>{value}</span>
            <span className='count-and-remove'>
              { this.props.name === value ? null : (
                <button
                  name={`remove[${this.props.name}]`}
                  data-value={value}
                  onClick={this.onClickRemove}
                  className="icon-close"
                >
                </button>
              )}
              <span className='count'>{valueCounts[value]}</span>
            </span>
          </li>
        ))}
      </ul>
    )

    return (
      <li className={className}>
        <div className='summary'>
          <input
            name={`include[${this.props.name}]`}
            type='checkbox'
            title='Include these rows'
            checked={!this.props.isBlacklisted}
            onChange={this.onChangeIsBlacklisted}
          />
          {maybeExpandCheckbox}
          <span className='count-and-reset'>
            {maybeResetButton}
            <span className='count'>{NumberFormatter.format(count)}</span>
          </span>
          <div className='growing'>
            <input
              type='text'
              name={`rename[${this.props.name}]`}
              value={this.state.name}
              onChange={this.onChangeName}
              onBlur={this.onBlurName}
              onKeyDown={this.onKeyDown}
            />
          </div>
        </div>
        {maybeValues}
      </li>
    )
  }
}

const buildSpecModifier = (_this, helperName) => {
  const func = RefineSpec.prototype[helperName]

  return (...args) => {
    const oldSpec = _this.parsedSpec
    const newSpec = func.apply(oldSpec, args)
    _this.props.onChange(newSpec.toJsonString())
  }
}

export class AllNoneButtons extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    clearBlacklist: PropTypes.func.isRequired, // func() => undefined
    fillBlacklist: PropTypes.func.isRequired // func() => undefined
  }

  render() {
    const { isReadOnly, clearBlacklist, fillBlacklist } = this.props

    return (
      <div className="all-none-buttons">
        <button
          disabled={isReadOnly}
          name='refine-select-all'
          title='Select All'
          onClick={clearBlacklist}
          className='mc-select-all'
        >
          All
        </button>
        <button
          disabled={isReadOnly}
          name='refine-select-none'
          title='Select None'
          onClick={fillBlacklist}
          className='mc-select-none'
        >
          None
        </button>
      </div>
    )
  }
}

/**
 * Edit a column's values to become "groups", then blacklist unwanted groups.
 *
 * The "value" here is a JSON-encoded String. Its format:
 *
 *     {
 *         "renames": {
 *             "foo": "bar", // "edit every 'foo' value to become 'bar'"
 *             //      ^^^ from the user's point of view, "bar" is the "group"
 *             ...
 *         },
 *         "blacklist": [
 *             "bar", // "Filter out every row where the post-rename value is "bar"
 *         ]
 *     }
 *
 * `valueCounts` describes the input: `{ "foo": 1, "bar": 3, ... }`
 */
export class Refine extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
    loading: PropTypes.bool.isRequired, // true iff loading from server
    value: PropTypes.string.isRequired, // JSON-encoded {renames: {value1: 'newvalue1', ...}, blacklist: ['newvalue1']}
    onChange: PropTypes.func.isRequired, // fn(newValue) => undefined
  }

  state = {
    searchInput: ''
  }

  get parsedSpec () {
    const value = this.props.value

    if (this._parsedSpec && this._parsedSpec.value === value) {
      // Memoized
      return this._parsedSpec.retval
    } else {
      const retval = RefineSpec.parse(value)
      this._parsedSpec = { value, retval }
      return retval
    }
  }

  /**
   * Return "groups": outputs, and their input
   *
   * Each "group" has the following properties:
   *
   * * `name`: a string describing the desired output
   * * `values`: strings describing the desired input; empty if no edits
   * * `isBlacklisted`: true if we are omitting this group from output
   */
  get groups () {
    const valueCounts = this.props.valueCounts
    const parsedSpec = this.parsedSpec

    if (this._groups && this._groups.valueCounts === valueCounts && this._groups.parsedSpec === parsedSpec) {
      // memoize retval
      return this._groups.retval
    } else {
      if (valueCounts === null) return []
      const retval = parsedSpec.buildGroupsForValueCounts(valueCounts)
      this._groups = { valueCounts, parsedSpec, retval }
      return retval
    }
  }

  onReset = () => {
    this.setState({ searchInput: '' })
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onReset() // Esc => reset
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput })
  }

  /**
   * Find { name: null } Object enumerating matching group names
   */
  groupNamesMatching (searchInput) {
    const groupNames = {} // { name: null } of matches

    const valueCounts = this.props.valueCounts || {}
    const renames = this.parsedSpec.renames

    const searchKey = searchInput.toLowerCase()
    for (const value in valueCounts) {
      if (value.toLowerCase().includes(searchKey)) {
        if (value in renames) {
          groupNames[renames[value]] = null
        } else {
          groupNames[value] = null
        }
      }
    }

    return groupNames
  }

  rename = buildSpecModifier(this, 'rename')
  massRename = buildSpecModifier(this, 'massRename')
  setIsBlacklisted = buildSpecModifier(this, 'setIsBlacklisted')
  resetGroup = buildSpecModifier(this, 'resetGroup')
  resetValue = buildSpecModifier(this, 'resetValue')
  setBlacklist = buildSpecModifier(this, 'withBlacklist')

  clearBlacklist = () => {
    this.setBlacklist([])
  }

  fillBlacklist = () => {
    this.setBlacklist(this.groups.map(g => g.name))
  }

  render () {
    const { valueCounts } = this.props
    const { searchInput } = this.state
    const groups = this.groups
    const isSearching = (searchInput !== '')
    const matchingGroups = isSearching ? this.groupNamesMatching(searchInput) : null

    const groupComponents = groups.map(group => (
      <RefineGroup
        key={group.name}
        isVisible={(matchingGroups === null) || (group.name in matchingGroups)}
        valueCounts={valueCounts}
        onChangeName={this.rename}
        onChangeIsBlacklisted={this.setIsBlacklisted}
        onResetGroup={this.resetGroup}
        onResetValue={this.resetValue}
        {...group}
      />
    ))

    const canSearch = this.groups.length > 1

    return (
      <div className='refine-parameter'>
        <RefineModalPrompt groups={this.groups} massRename={this.massRename} />
        { !canSearch ? null : (
          <React.Fragment>
            <form className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search facets...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button type="reset" className="close" title="Clear Search"><i className="icon-close"></i></button>
            </form>
            <AllNoneButtons
              isReadOnly={isSearching}
              clearBlacklist={this.clearBlacklist}
              fillBlacklist={this.fillBlacklist}
            />
          </React.Fragment>
        )}
        <ul className='refine-groups'>
          {groupComponents}
        </ul>
        { (isSearching && matchingGroups !== null && matchingGroups.length === 0) ? (
          <div className='wf-module-error-msg'>No values</div>
        ) : null}
      </div>
    )
  }
}

export default withFetchedData(Refine, 'valueCounts')
