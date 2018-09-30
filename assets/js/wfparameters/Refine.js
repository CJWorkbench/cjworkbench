import React from 'react'
import PropTypes from 'prop-types'
import RefineModal from '../refine/RefineModal'

const NumberFormatter = new Intl.NumberFormat()
const blacklistEmpty = 0
const blacklistFill = 1

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

  clearBlackList ()  {
    return new RefineSpec(this.renames, [])
  }

  fillBlackList (allGroups) {
    return new RefineSpec(this.renames, allGroups)
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

class RefineGroup extends React.PureComponent {
  static propTypes = {
    valueCounts: PropTypes.object, // null or { value1: n, value2: n, ... }
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
    if (this.props.name !== this.state.value) {
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
    const { count, values, valueCounts } = this.props

    // isOriginal uses this._props_.name, not this._state_. The group the
    // buttons would modify is this.props.name.
    const isOriginal = values.length === 1 && values[0] === this.props.name
    const className = isOriginal ? '' : 'edited'

    const maybeExpandCheckbox = isOriginal ? null : (
      <label className='expand'>
        <input
          type='checkbox'
          name='expand'
          title={isExpanded ? 'Hide original values' : 'Show original values'}
          checked={isExpanded}
          onChange={this.onChangeIsExpanded}
        />
        <i className={isExpanded ? 'icon-caret-up' : 'icon-caret-down'} />
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
      <React.Fragment>
        <dt className={className}>
          <label className='checkbox'>
            <input
              name={`include[${this.props.name}]`}
              type='checkbox'
              title='Include these rows'
              checked={!this.props.isBlacklisted}
              onChange={this.onChangeIsBlacklisted}
            />
          </label>
          <span className='growing'>
            <span className='autosized-input'>
              <span className='text-to-size'>{this.state.name}</span>
              <input
                type='text'
                name={`rename[${this.props.name}]`}
                value={this.state.name}
                onChange={this.onChangeName}
                onBlur={this.onBlurName}
                onKeyDown={this.onKeyDown}
              />
            </span>
            {maybeExpandCheckbox}
          </span>
          <span className='count-and-reset'>
            {maybeResetButton}
            <span className='count'>{NumberFormatter.format(count)}</span>
          </span>
        </dt>
        <dd>
          {maybeValues}
        </dd>
      </React.Fragment>
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
    clearBlackList: PropTypes.func.isRequired,
    fillBlackList: PropTypes.func.isRequired,
    allGroups: PropTypes.array.isRequired
  }

  setAll = () => this.props.clearBlackList()
  setNone = () => this.props.fillBlackList(this.props.allGroups)

  render() {
    return (
      <div className="d-flex mb-2 mt-2 ">
          <button
            disabled={this.props.isReadOnly}
            name={`refine-select-all`}
            title='Select All'
            onClick={this.setAll}
            className='mc-select-all content-4 t-d-gray'
            >
            All
          </button>
          <button
            disabled={this.props.isReadOnly}
            name={`refine-select-none`}
            title='Select None'
            onClick={this.setNone}
            className='mc-select-none content-4 t-d-gray'
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
    isRefineModalOpen: false,
    searchInput: '',
    searchMode: false
  }

  get parsedSpec () {
    return RefineSpec.parse(this.props.value)
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
    const { valueCounts } = this.props
    if (valueCounts === null) return []
    return this.parsedSpec.buildGroupsForValueCounts(this.props.valueCounts)
  }

  openRefineModal = () => {
    this.setState({ isRefineModalOpen: true })
  }

  closeRefineModal = () => {
    this.setState({ isRefineModalOpen: false })
  }

  onRefineModalSubmit = (renames) => {
    this.massRename(renames)
    this.closeRefineModal()
  }

  onReset = () => {
    this.setInput('')
  }

  setInput(input) {
    const searchMode = input == '' ? false : true

    this.setState({
      searchInput: input,
      searchMode: searchMode
    })
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onReset() // Esc => reset
  }

  onInputChange = (ev) => {
    const input = ev.target.value
    this.setInput(input)
  }

  filterResults = (groups) => {
    // Search for the search string in both the group name or group members
    return groups.filter(group =>
      ( group.name.toLowerCase().includes(this.state.searchInput.toLowerCase()) || this.searchInGroup(group.values))
    )
  }

  searchInGroup = (members) => {
    for (let i in members) {
      if (members[i].toLowerCase().includes(this.state.searchInput.toLowerCase())) return true
    }
    return false
  }

  rename = buildSpecModifier(this, 'rename')
  massRename = buildSpecModifier(this, 'massRename')
  setIsBlacklisted = buildSpecModifier(this, 'setIsBlacklisted')
  resetGroup = buildSpecModifier(this, 'resetGroup')
  resetValue = buildSpecModifier(this, 'resetValue')
  clearBlackList = buildSpecModifier(this, 'clearBlackList')
  fillBlackList = buildSpecModifier(this, 'fillBlackList')

  render () {
    const { valueCounts } = this.props
    const { isRefineModalOpen, searchInput, searchMode } = this.state
    const groups = this.groups
    const displayedGroups = searchMode ? this.filterResults(groups) : groups
    const groupNames = groups.map(group => group.name)

    const groupComponents = displayedGroups.map(group => (
      <RefineGroup
        key={group.name}
        valueCounts={valueCounts}
        onChangeName={this.rename}
        onChangeIsBlacklisted={this.setIsBlacklisted}
        onResetGroup={this.resetGroup}
        onResetValue={this.resetValue}
        {...group}
      />
    ))

    const canCluster = isRefineModalOpen || groups.length > 1
    const canSearch = groups.length > 1
    let refineModalBucket = null
    if (isRefineModalOpen) {
      refineModalBucket = {}
      for (const group of groups) {
        refineModalBucket[group.name] = group.count
      }
    }

    return (
      <React.Fragment>
        { !canCluster ? null : (
          <div className='refine-modal-prompt'>
            <button className="cluster" name='cluster' onClick={this.openRefineModal}>Cluster</button>
            <span className='instructions'>Group values using algorithms</span>
            { !isRefineModalOpen ? null : (
              <RefineModal
                bucket={refineModalBucket}
                onClose={this.closeRefineModal}
                onSubmit={this.onRefineModalSubmit}
              />
            )}
          </div>
        )}
        { !canSearch ? null : (
          <div>
            <div className="refine-search">
              <form className="refine-search-field" onSubmit={this.onSubmit} onReset={this.onReset}>
                <input
                  type='search'
                  placeholder='Search Facets...'
                  autoComplete='off'
                  value={searchInput}
                  onChange={this.onInputChange}
                  onKeyDown={this.onKeyDown}
                />
                <button type="reset" className="close" title="Close Search"><i className="icon-close"></i></button>
              </form>
            </div>
            <AllNoneButtons
              isReadOnly={searchMode}
              clearBlackList={this.clearBlackList}
              fillBlackList={this.fillBlackList}
              allGroups={groupNames}
            />
          </div>
        )}
        <div className="refine-groups">
          <dl>
            {groupComponents}
          </dl>
        </div>
        { ( canSearch && displayedGroups.length == 0 ) ? (
          <div>
            <span className='no-search-results'>No Results</span>
          </div>) : null
        }
      </React.Fragment>
    )
  }
}

// https://reactjs.org/docs/higher-order-components.html
//
// Let's keep this generic and maybe make it into a reusable util later.
function withFetchedData(WrappedComponent, dataName) {
  return class extends React.PureComponent {
    static propTypes = {
      fetchData: PropTypes.func.isRequired, // fn() => Promise[data]
      fetchDataCacheId: PropTypes.string.isRequired, // unique string: when it changes, call fetchData()
    }

    state = {
      data: null,
      loading: false
    }

    _reload () {
      const fetchDataCacheId = this.props.fetchDataCacheId

      // Keep state.data unchanged, until we solve
      // https://www.pivotaltracker.com/story/show/158034731. After that, we
      // should probably change this to setState({data: null})
      this.setState({ loading: true })

      this.props.fetchData()
        .then(data => {
          if (this.unmounted) return
          if (this.props.fetchDataCacheId !== fetchDataCacheId) return // ignore wrong response in race

          this.setState({
            loading: false,
            data
          })
        })
    }

    componentDidMount () {
      this._reload()
    }

    componentWillUnmount () {
      this.unmounted = true
    }

    componentDidUpdate (prevProps) {
      if (prevProps.fetchDataCacheId !== this.props.fetchDataCacheId) {
        this._reload()
      }
    }

    render () {
      const props = Object.assign({
        [dataName]: this.state.data,
        loading: this.state.loading
      }, this.props)
      delete props.fetchData
      delete props.fetchDataCacheId

      return <WrappedComponent {...props} />
    }
  }
}

export default withFetchedData(Refine, 'valueCounts')
