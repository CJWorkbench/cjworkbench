import React from 'react'
import PropTypes from 'prop-types'
import memoize from 'memoize-one'
import { ModulePropType } from './PropTypes'
import SearchResultGroup from './SearchResultGroup'

const GroupOrder = {
  // dont use 0 -- we use the "||" operator to detect misses
  Combine: 1,
  Scrape: 2,
  Clean: 3,
  Analyze: 4,
  Visualize: 5,
  Code: 6,
  'Add data': 1 // TODO nix this category for non-`loads_data` modules
}

function compareGroups (a, b) {
  const ai = GroupOrder[a.name] || 99
  const bi = GroupOrder[b.name] || 99
  return ai - bi
}

// Function to sort modules in alphabetical order
function compareModules (a, b) {
  if (a.name.toLowerCase() < b.name.toLowerCase()) return -1
  else if (a.name.toLowerCase() > b.name.toLowerCase()) return 1
  else return 0
}

/**
 * Return [ { name: 'Clean', modules: [ ... ] }, ... ]
 */
function groupModules (items) {
  const ret = []
  const temp = {}
  items.sort(compareModules)

  items.forEach(item => {
    if (temp[item.category]) {
      temp[item.category].push(item)
    } else {
      const obj = { name: item.category, modules: [item] }
      temp[item.category] = obj.modules
      ret.push(obj)
    }
  })

  ret.sort(compareGroups)

  return ret
}

const escapeRegexCharacters = (str) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export default class SearchResults extends React.PureComponent {
  static propTypes = {
    search: PropTypes.string.isRequired, // search string, to filter modules
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    onClickModule: PropTypes.func.isRequired // func(moduleIdName) => undefined
  }

  state = {
    activeModule: null // idName
  }

  get resultGroups () {
    return this._buildResultGroups(this.allGroups, this.props.search)
  }

  get allGroups () {
    return this._buildAllGroups(this.props.modules)
  }

  _buildAllGroups = memoize(groupModules)

  _buildResultGroups = memoize((groups, search) => {
    const escapedValue = escapeRegexCharacters(search.trim())
    const regex = new RegExp(escapedValue, 'i')
    const predicate = (module) => (regex.test(module.name) || regex.test(module.description))
    return groups
      .map(({ name, modules }) => ({ name, modules: modules.filter(predicate) }))
      .filter(({ modules }) => modules.length > 0)
  })

  onMouseEnterModule = (moduleIdName) => {
    this.setState({ activeModule: moduleIdName })
  }

  render () {
    const { onClickModule } = this.props
    const { activeModule } = this.state

    return (
      <ul className='module-search-result-groups'>
        {this.resultGroups.map(rg => (
          <SearchResultGroup
            key={rg.name}
            name={rg.name}
            modules={rg.modules}
            activeModule={activeModule}
            onClickModule={onClickModule}
            onMouseEnterModule={this.onMouseEnterModule}
          />
        ))}
      </ul>
    )
  }
}
