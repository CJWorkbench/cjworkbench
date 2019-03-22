/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import memoize from 'memoize-one'
import { ModulePropType } from './PropTypes'
import Prompt from './Prompt'
import SearchResultGroup from './SearchResultGroup'

import lessonSelector from '../lessons/lessonSelector'

const GroupOrder = {
  // dont use 0 -- we use the "||" operator to detect misses
  'Add data': 1,
  'Scrape': 2,
  'Clean': 3,
  'Analyze': 4,
  'Visualize': 5,
  'Code': 6,
}

function compareGroups(a, b) {
  const ai = GroupOrder[a.name] || 99;
  const bi = GroupOrder[b.name] || 99;
  return ai - bi;
}

// Function to sort modules in alphabetical order
function compareModules(a, b) {
  if (a.name.toLowerCase() < b.name.toLowerCase()) return -1
  else if (a.name.toLowerCase() > b.name.toLowerCase()) return 1
  else return 0
}

/**
 * Return [ { name: 'Clean', modules: [ ... ] }, ... ]
 */
function groupModules(items) {
  const ret = []
  const temp = {}
  items.sort(compareModules)

  items.forEach(item => {
    if (temp[item.category]) {
      temp[item.category].push(item)
    } else {
      const obj = { name: item.category, modules: [ item ] }
      temp[item.category] = obj.modules
      ret.push(obj)
    }
  })

  ret.sort(compareGroups)

  return ret
}

const escapeRegexCharacters = (str) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export class ModuleSearch extends React.Component {
  static propTypes = {
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    index: PropTypes.number.isRequired, // helps mapStateToProps() calculate isLessonHighlight
    isLessonHighlight: PropTypes.bool.isRequired,
    onCancel: PropTypes.func.isRequired, // func() => undefined
    onClickModule: PropTypes.func.isRequired, // func(moduleIdName) => undefined
  }

  state = {
    input: '',
    activeModule: null // idName
  }

  get resultGroups () {
    return this._buildResultGroups(this.allGroups, this.state.input)
  }

  get allGroups () {
    return this._buildAllGroups(this.props.modules)
  }

  _buildAllGroups = memoize(groupModules)

  _buildResultGroups = memoize((groups, input) => {
    const escapedValue = escapeRegexCharacters(input.trim())
    const regex = new RegExp(escapedValue, 'i')
    const predicate = (module) => regex.test(module.name) || regex.test(module.description)
    return groups
      .map(({ name, modules }) => ({ name, modules: modules.filter(predicate) }))
      .filter(({ modules }) => modules.length > 0)
  })

  onSearchInputChange = (value) => {
    this.setState({ input: value })
  }

  onClickModule = (moduleIdName) => {
    this.setState({ input: '' })
    this.props.onClickModule(moduleIdName)
  }

  onMouseEnterModule = (moduleIdName) => {
    this.setState({ activeModule: moduleIdName })
  }

  cancel = () => {
    this.setState({ input: '' })
    this.props.onCancel()
  }

  render () {
    const { input, activeModule } = this.state

    const resultGroupComponents = this.resultGroups.map(rg => (
      <SearchResultGroup
        key={rg.name}
        name={rg.name}
        modules={rg.modules}
        activeModule={activeModule}
        onClickModule={this.onClickModule}
        onMouseEnterModule={this.onMouseEnterModule}
      />
    ))
    const resultGroupsComponent = (
      <ul className="module-search-result-groups">
        {resultGroupComponents}
      </ul>
    )

    const className = [ 'module-search' ]
    if (this.props.isLessonHighlight) className.push('lesson-highlight')

    return (
      <div className={className.join(' ')}>
        <Prompt value={input} cancel={this.cancel} onChange={this.onSearchInputChange} />
        {resultGroupsComponent}
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const { testHighlight } = lessonSelector(state)
  return {
    isLessonHighlight: testHighlight({ type: 'Module', index: ownProps.index }),
    modules: Object.keys(state.modules).map(idName => {
      const module = state.modules[idName]
      return {
        idName,
        ...module,
        isLessonHighlight: testHighlight({ type: 'Module', name: module.name, index: ownProps.index })
      }
    })
  }
}

export default connect(
  mapStateToProps
)(ModuleSearch)
