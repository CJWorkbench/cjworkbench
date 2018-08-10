/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import PropTypes from 'prop-types'
import { connect } from 'react-redux'

import lessonSelector from './lessons/lessonSelector'

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

function groupModules(items) {
  const ret = []
  const temp = {}

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

class ModuleSearchResult extends React.PureComponent {
  onClick = () => {
    this.props.onClick(this.props.id)
  }

  render() {
    const { isLessonHighlight, isMatch, name, icon } = this.props

    const className = [ 'module-search-result' ]
    if (isLessonHighlight) className.push('lesson-highlight')

    return (
      <li className={className.join(' ')} data-module-name={this.props.name} onClick={this.onClick}>
        <i className={'icon-' + this.props.icon}></i>
        <span className='name'>{this.props.name}</span>
      </li>
    )
  }
}
ModuleSearchResult.propTypes = {
  isLessonHighlight: PropTypes.bool.isRequired,
  id: PropTypes.number.isRequired,
  name: PropTypes.string.isRequired,
  icon: PropTypes.string.isRequired,
  onClick: PropTypes.func.isRequired,
}

class ModuleSearchResultGroup extends React.PureComponent {
  render() {
    const { name, modules, hasMatch } = this.props

    const children = modules.map(module => (
      <ModuleSearchResult
        key={module.name}
        {...module}
        onClick={this.props.onClickModuleId}
        />
    ))

    return (
      <li className="module-search-result-group" data-name={name}>
        <h4>{name}</h4>
        <ul className="module-search-results">{children}</ul>
      </li>
    )
  }
}
ModuleSearchResultGroup.propTypes = {
  name: PropTypes.string.isRequired,
  modules: PropTypes.arrayOf(PropTypes.shape({
    isLessonHighlight: PropTypes.bool.isRequired,
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
  })).isRequired,
  onClickModuleId: PropTypes.func.isRequired, // func(moduleId) => undefined
}

const escapeRegexCharacters = (str) => {
  return str.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export class ModuleSearch extends React.Component {
  constructor(props) {
    super(props)
    this.state = {
      input: '',
      resultGroups: groupModules(this.props.modules),
    }

    this.inputRef = React.createRef()
  }

  findResultGroups(input) {
    const escapedValue = escapeRegexCharacters(input.trim())
    const regex = new RegExp(escapedValue, 'i')
    const foundModules = this.props.modules.filter(m => regex.test(m.name))
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
    const { input, resultGroups } = this.state

    const resultGroupComponents = resultGroups.map(rg => (
      <ModuleSearchResultGroup
        key={rg.name}
        name={rg.name}
        modules={rg.modules}
        onClickModuleId={this.onClickModuleId}
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

ModuleSearch.propTypes = {
  modules: PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    isLessonHighlight: PropTypes.bool.isRequired,
    name: PropTypes.string.isRequired,
    category: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
  })).isRequired,
  index: PropTypes.number.isRequired, // helps mapStateToProps() calculate isLessonHighlight
  isLessonHighlight: PropTypes.bool.isRequired,
  onCancel: PropTypes.func.isRequired, // func() => undefined
  onClickModuleId: PropTypes.func.isRequired, // func(moduleId) => undefined
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
