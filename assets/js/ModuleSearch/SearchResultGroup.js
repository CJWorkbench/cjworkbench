import React from 'react'
import PropTypes from 'prop-types'
import SearchResult from './SearchResult'

export default class ModuleSearchResultGroup extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    activeModuleId: PropTypes.number, // null if none active
    modules: PropTypes.arrayOf(PropTypes.shape({
      isLessonHighlight: PropTypes.bool.isRequired,
      id: PropTypes.number.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired
    })).isRequired,
    onClickModuleId: PropTypes.func.isRequired, // func(moduleId) => undefined
    onMouseEnterModuleId: PropTypes.func.isRequired // func(moduleId) => undefined
  }

  render() {
    const { name, modules, hasMatch, activeModuleId } = this.props

    const children = modules.map(module => (
      <SearchResult
        key={module.name}
        isActive={module.id === activeModuleId}
        {...module}
        onClick={this.props.onClickModuleId}
        onMouseEnter={this.props.onMouseEnterModuleId}
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
