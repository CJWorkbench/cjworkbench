/**
* Search field that returns modules matching text input.
*
*/

import React from 'react';
import PropTypes from 'prop-types'
import { connect } from 'react-redux'
import { ModulePropType } from './PropTypes'
import Prompt from './Prompt'
import SearchResults from './SearchResults'

import lessonSelector from '../lessons/lessonSelector'

export class ModuleSearch extends React.Component {
  static propTypes = {
    modules: PropTypes.arrayOf(ModulePropType.isRequired).isRequired,
    index: PropTypes.number.isRequired, // helps mapStateToProps() calculate isLessonHighlight
    isLessonHighlight: PropTypes.bool.isRequired,
    onCancel: PropTypes.func.isRequired, // func() => undefined
    onClickModule: PropTypes.func.isRequired, // func(moduleIdName) => undefined
  }

  state = {
    search: ''
  }

  onSearchInputChange = (value) => {
    this.setState({ search: value })
  }

  onClickModule = (moduleIdName) => {
    this.setState({ search: '' })
    this.props.onClickModule(moduleIdName)
  }

  cancel = () => {
    this.setState({ search: '' })
    this.props.onCancel()
  }

  render () {
    const { modules } = this.props
    const { search } = this.state

    const className = [ 'module-search' ]
    if (this.props.isLessonHighlight) className.push('lesson-highlight')

    return (
      <div className={className.join(' ')}>
        <Prompt value={search} cancel={this.cancel} onChange={this.onSearchInputChange} />
        <SearchResults search={search} modules={modules} onClickModule={this.onClickModule} />
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
