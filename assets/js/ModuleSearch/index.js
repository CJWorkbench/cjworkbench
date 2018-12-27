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
      idName: PropTypes.string.isRequired,
      isLessonHighlight: PropTypes.bool.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      category: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired,
    })).isRequired,
    index: PropTypes.number.isRequired, // helps mapStateToProps() calculate isLessonHighlight
    isLessonHighlight: PropTypes.bool.isRequired,
    onCancel: PropTypes.func.isRequired, // func() => undefined
    onClickModule: PropTypes.func.isRequired, // func(moduleIdName) => undefined
  }

  state = {
    input: '',
    resultGroups: groupModules(this.props.modules),
    activeModule: null // idName
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

  onClickModule = (moduleIdName) => {
    this.setInput('')
    this.props.onClickModule(moduleIdName)
  }

  onMouseEnterModule = (moduleIdName) => {
    this.setState({ activeModule: moduleIdName })
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
    const { input, resultGroups, activeModule } = this.state

    const resultGroupComponents = resultGroups.map(rg => (
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
