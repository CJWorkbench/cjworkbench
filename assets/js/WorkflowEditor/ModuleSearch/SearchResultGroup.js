import React from 'react'
import PropTypes from 'prop-types'
import SearchResult from './SearchResult'
import { CategoryName } from '../../util/ModuleCategory'

export default class ModuleSearchResultGroup extends React.PureComponent {
  static propTypes = {
    name: PropTypes.string.isRequired,
    activeModule: PropTypes.string, // idName, null if none active
    modules: PropTypes.arrayOf(PropTypes.shape({
      isLessonHighlight: PropTypes.bool.isRequired,
      idName: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      description: PropTypes.string.isRequired,
      icon: PropTypes.string.isRequired
    })).isRequired,
    onClickModule: PropTypes.func.isRequired, // func(moduleIdName) => undefined
    onMouseEnterModule: PropTypes.func.isRequired // func(moduleIdName) => undefined
  }

  render () {
    const { name, modules, activeModule } = this.props

    const children = modules.map(module => (
      <SearchResult
        key={module.name}
        isActive={module.idName === activeModule}
        {...module}
        onClick={this.props.onClickModule}
        onMouseEnter={this.props.onMouseEnterModule}
      />
    ))

    return (
      <li className='module-search-result-group' data-name={name}>
        <h4><CategoryName category={name} /></h4>
        <ul className='module-search-results'>{children}</ul>
      </li>
    )
  }
}
