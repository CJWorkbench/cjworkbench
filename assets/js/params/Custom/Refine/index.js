import React from 'react'
import PropTypes from 'prop-types'
import RefineModal from './RefineModal'
import { withFetchedData } from '../FetchedData'

const NumberFormatter = new Intl.NumberFormat()

export class RefineSpec {
  constructor (renames, blacklist) {
    this.renames = renames
    this.blacklist = blacklist
  }

  toJsonObject () {
    return {
      renames: this.renames,
      blacklist: this.blacklist
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
        <button type='button' name='cluster' onClick={this.openModal}>Find clusters...</button>
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
    isFocused: PropTypes.bool,  // focus text area immediately after group merged
    isVisible: PropTypes.bool.isRequired,
    name: PropTypes.string, // new value -- may be empty string
    values: PropTypes.arrayOf(PropTypes.string).isRequired, // sorted by count, descending -- may be empty
    count: PropTypes.number.isRequired, // number, strictly greater than 0
    isSelected: PropTypes.bool.isRequired,
    onChangeName: PropTypes.func.isRequired, // func(oldName, newName) => undefined
    setIsSelected: PropTypes.func.isRequired, // func(name, isBlacklisted) => undefined
    onResetGroup: PropTypes.func.isRequired, // func(name) => undefined
    onResetValue: PropTypes.func.isRequired // func(value) => undefined
  }

  textInput = React.createRef()

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

  // Set focus when group finishes merging
  componentDidUpdate(oldProps, newProps) {
    if (this.props.isFocused) {
      this.textInput.current.focus()
      if (this.textInput.current.value === this.props.name) {
        this.textInput.current.select()
      }
    }
  }

  onChangeIsBlacklisted = (ev) => {
    this.props.onChangeIsBlacklisted(this.props.name, !ev.target.checked)
  }

  onChangeIsSelected = (ev) => {
    this.props.setIsSelected(this.props.name, ev.target.checked)
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
        type='button'
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
                  type='button'
                  name={`remove[${this.props.name}]`}
                  data-value={value}
                  onClick={this.onClickRemove}
                  className='icon-close'
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
            checked={this.props.isSelected}
            onChange={this.onChangeIsSelected}
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
              ref={this.textInput}
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

const buildSpecModifier = (_this, helperName, shouldSubmit=false) => {
  const func = RefineSpec.prototype[helperName]

  return (...args) => {
    const oldSpec = _this.parsedSpec
    const newSpec = func.apply(oldSpec, args)
    _this.props.onChange(newSpec.toJsonObject())
    if (shouldSubmit) _this.props.onSubmit()
  }
}

export class AllNoneButtons extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    clearSelectedSearchValues: PropTypes.func.isRequired, // func() => undefined
    fillSelectedSearchValues: PropTypes.func.isRequired // func() => undefined
  }

  render() {
    const { isReadOnly, clearSelectedSearchValues, fillSelectedSearchValues } = this.props

    return (
      <div className="all-none-buttons">
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-all'
          title='Select All'
          onClick={fillSelectedSearchValues}
        >
          All
        </button>
        <button
          disabled={isReadOnly}
          type='button'
          name='refine-select-none'
          title='Select None'
          onClick={clearSelectedSearchValues}
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
    value: PropTypes.shape({
      renames: PropTypes.object.isRequired,
      blacklist: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired
    }).isRequired,
    onChange: PropTypes.func.isRequired, // fn(newValue) => undefined
  }

  state = {
    searchInput: '',
    selectedValues: {}, // object for quick lookup
    focusedValue: ''
  }

  get parsedSpec () {
    const { value } = this.props

    if (this._parsedSpec && this._parsedSpec.value === value) {
      // Memoized
      return this._parsedSpec.retval
    } else {
      const { renames, blacklist } = value
      const retval = new RefineSpec(renames, blacklist)
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
    switch (ev.key) {
      case 'Escape':
        return this.onReset()
      case 'Enter':
        ev.preventDefault() // prevent form submit
    }
  }

  onInputChange = (ev) => {
    const searchInput = ev.target.value
    this.setState({ searchInput })
  }

  setIsSelected = (value, isChecked) => {
    isChecked ? this.addSelectedValues([value]) : this.removeSelectedValues([value])
  }

  // ADD values to selectedValues. "All" button will not overwrite previously selected values.
  addSelectedValues = (values) => {
    let selectedValues = Object.assign({}, this.state.selectedValues)
    for (var idx in values){
      selectedValues[values[idx]] = null
    }
    this.setState({ selectedValues: selectedValues })
  }

  removeSelectedValues = (values) => {
    let selectedValues = Object.assign({}, this.state.selectedValues)
    for (var idx in values){
      if (values[idx] in selectedValues) {
        delete selectedValues[values[idx]]
      }
    }
    this.setState({ selectedValues: selectedValues })
  }

  clearSelectedSearchValues = () => {
    const matchingGroupsList = Object.keys(this.groupNamesMatching(this.state.searchInput))
    this.removeSelectedValues(matchingGroupsList)
  }

  fillSelectedSearchValues = () => {
    const matchingGroupsList = Object.keys(this.groupNamesMatching(this.state.searchInput))
    this.addSelectedValues(matchingGroupsList)
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

  clearFocus() {
    this.setState({ focusedValue: '' })
  }

  /*
    Determines the name value to default to for new group.
    Order:
      1. Group 'values' count
      2. Group 'count'
      3. Alphabetical
  */
  mergeSelectedValues = () => {
    const selectedValuesList = Object.keys(this.state.selectedValues)
    const selectedGroups = this.groups.filter(obj => selectedValuesList.indexOf(obj.name) > -1)

    selectedGroups.sort(function (a, b) {
        // Compare length of values
        if (a.values.length > b.values.length) return -1
        if (b.values.length > a.values.length) return 1
        // Compare count
        if (a.count > b.count) return -1
        if (b.count < a.count) return 1
        // Alphabetical
        if (a.name < b.name) return -1
        return 1
    })

    const toGroup = selectedGroups[0].name
    let groupMap = {}
    selectedValuesList.forEach(function (fromGroup) {
      groupMap[fromGroup] = toGroup
    })
    this.massRename(groupMap)
    this.setState( {selectedValues: [], focusedValue: toGroup} )
  }

  rename = buildSpecModifier(this, 'rename')
  massRename = buildSpecModifier(this, 'massRename')
  setIsBlacklisted = buildSpecModifier(this, 'setIsBlacklisted')
  resetGroup = buildSpecModifier(this, 'resetGroup')
  resetValue = buildSpecModifier(this, 'resetValue')
  setBlacklist = buildSpecModifier(this, 'withBlacklist')

  render () {
    const { valueCounts } = this.props
    const { searchInput, selectedValues, focusedValue } = this.state
    const groups = this.groups
    const isSearching = (searchInput !== '')
    const matchingGroups = isSearching ? this.groupNamesMatching(searchInput) : null

    const groupComponents = groups.map(group => (
      <RefineGroup
        key={group.name}
        isFocused={group.name === this.state.focusedValue}
        isSelected={group.name in selectedValues}
        isVisible={(matchingGroups === null) || (group.name in matchingGroups)}
        valueCounts={valueCounts}
        onChangeName={this.rename}
        setIsSelected={this.setIsSelected}
        onResetGroup={this.resetGroup}
        onResetValue={this.resetValue}
        {...group}
      />
    ))

    const canSearch = this.groups.length > 1
    if (focusedValue !== '') this.clearFocus()

    const maybeMergeButton = groups.length > 0 ? (
      <button type='button' name='merge' onClick={this.mergeSelectedValues} disabled={Object.keys(selectedValues).length < 2}>Merge facets</button>)
      : null

    return (
      <div className='refine-parameter'>
        { !canSearch ? null : (
          <React.Fragment>
            <fieldset className="in-module--search" onSubmit={this.onSubmit} onReset={this.onReset}>
              <input
                type='search'
                placeholder='Search facets...'
                autoComplete='off'
                value={searchInput}
                onChange={this.onInputChange}
                onKeyDown={this.onKeyDown}
              />
              <button type="button" onClick={this.onReset} className="close" title="Clear Search"><i className="icon-close"></i></button>
            </fieldset>
            <AllNoneButtons
              isReadOnly={false}
              clearSelectedSearchValues={this.clearSelectedSearchValues}
              fillSelectedSearchValues={this.fillSelectedSearchValues}
            />
          </React.Fragment>
        )}
        <ul className='refine-groups'>
          {groupComponents}
        </ul>
        <div className="refine-actions">
          {maybeMergeButton}
          <RefineModalPrompt groups={this.groups} massRename={this.massRename} />
          { (isSearching && matchingGroups !== null && matchingGroups.length === 0) ? (
            <div className='wf-module-error-msg'>No values</div>
          ) : null}
        </div>
      </div>
    )
  }
}

export default withFetchedData(
  Refine,
  'valueCounts',
  ({ api, inputWfModuleId, selectedColumn }) => api.valueCounts(inputWfModuleId, selectedColumn),
  ({ inputDeltaId, selectedColumn }) => `${inputDeltaId}-${selectedColumn}`
)
