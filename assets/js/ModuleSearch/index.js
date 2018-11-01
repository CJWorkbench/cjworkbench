/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
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
    modules: PropTypes.arrayOf(PropTypes.shape({
      id: PropTypes.number.isRequired,
      isLessonHighlight: PropTypes.bool.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      category: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired,
    })).isRequired,
    index: PropTypes.number.isRequired, // helps mapStateToProps() calculate isLessonHighlight
    isLessonHighlight: PropTypes.bool.isRequired,
    onCancel: PropTypes.func.isRequired, // func() => undefined
    onClickModuleId: PropTypes.func.isRequired, // func(moduleId) => undefined
  }

  state = {
    input: '',
    resultGroups: groupModules(this.props.modules),
    activeModuleId: null
  }

  inputRef = React.createRef()

  findResultGroups(input) {
    const escapedValue = escapeRegexCharacters(input.trim())
    const regex = new RegExp(escapedValue, 'i')
    const foundModules = this.props.modules.filter(m => (regex.test(m.name) | regex.test(m.description)))
    const groups = groupModules(foundModules)
    return groups
  }

  componentDidMount() {
    // auto-focus
    const ref = this.inputRef.current
    if (ref) ref.focus()
  }

  setInput(input) {
    const resultGroups = this.findResultGroups(input)

    this.setState({
      input,
      resultGroups,
    })
  }

  onInputChange = (ev) => {
    const input = ev.target.value
    this.setInput(input)
  }

  onClickModuleId = (moduleId) => {
    this.setInput('')
    this.props.onClickModuleId(moduleId)
  }

  onMouseEnterModuleId = (moduleId) => {
    this.setState({ activeModuleId: moduleId })
  }

  onSubmit = (ev) => {
    ev.preventDefault()
  }

  onReset = () => {
    this.setInput('')
    this.props.onCancel()
  }

  onKeyDown = (ev) => {
    if (ev.keyCode === 27) this.onReset() // Esc => reset
  }

  render () {
    const { input, resultGroups, activeModuleId } = this.state

    const resultGroupComponents = resultGroups.map(rg => (
      <SearchResultGroup
        key={rg.name}
        name={rg.name}
        modules={rg.modules}
        activeModuleId={activeModuleId}
        onClickModuleId={this.onClickModuleId}
        onMouseEnterModuleId={this.onMouseEnterModuleId}
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
        <form className="module-search-field" onSubmit={this.onSubmit} onReset={this.onReset}>
          <input
            type='search'
            name='moduleQ'
            placeholder='Search…'
            autoComplete='off'
            ref={this.inputRef}
            value={input}
            onChange={this.onInputChange}
            onKeyDown={this.onKeyDown}
            />
          <button type="reset" className="close" title="Close Search"><i className="icon-close"></i></button>
        </form>
        {resultGroupsComponent}
      </div>
    )
  }
}

const mapStateToProps = (state, ownProps) => {
  const { testHighlight } = lessonSelector(state)
  return {
    isLessonHighlight: testHighlight({ type: 'Module', index: ownProps.index }),
    modules: Object.keys(state.modules).map(moduleId => {
      const module = state.modules[moduleId]
      return {
        ...module,
        isLessonHighlight: testHighlight({ type: 'Module', name: module.name, index: ownProps.index })
      }
    })
  }
}

export default connect(
  mapStateToProps
)(ModuleSearch)
