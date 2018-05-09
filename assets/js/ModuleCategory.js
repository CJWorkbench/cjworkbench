/**
 * A component that holds a collection of <Module>s for a given category. For example,
 * Category: Source
 * Modules: Load URL, Paste CSV, Twitter
 *
 * Category: Wrangle
 * Modules: Melt, Select Columns
 *
 * Categories should be expandable and collapsible, just like each individual module.
 *
 * Rendered by <ModuleCategories> component
 */

import React from 'react'
import PropTypes from 'prop-types'
import { Collapse, Button, CardBlock, Card } from 'reactstrap';
import Module from './Module'

export default class ModuleCategory extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      collapsed: props.collapsed   // relevant only when !this.props.libraryOpen
    };
    this.openCategory = this.openCategory.bind(this);
    this.collapseAll = this.collapseAll.bind(this);
  }

  // When our props change, update our collapsed state (this is the other end of setOpenCategory)
  componentWillReceiveProps(newProps) {
    this.setState({collapsed: newProps.collapsed})
  }

  openCategory() {
    this.props.setOpenCategory(this.props.name); // tell parent to close all
  }

  collapseAll() {
    this.props.setOpenCategory(null); // tell parent to close all
  }

  _renderModule(module) {
    const { name, icon, id } = module
    const { addModule, dropModule, isReadOnly, setOpenCategory, libraryOpen } = this.props

    return (
      <Module
        key={name}
        name={name}
        icon={icon}
        id={id}
        addModule={addModule}
        dropModule={dropModule}
        isReadOnly={isReadOnly}
        setOpenCategory={setOpenCategory}
        libraryOpen={libraryOpen}
      />
    )
  }

  _renderModules() {
    return this.props.modules.map(m => this._renderModule(m))
  }

  render() {
    // Provides margins around opened library category

    const icons = {
      'Add data': 'database',
      'Clean': 'wrangle',
      'Analyze': 'notepad',
      'Visualize': 'chart',
      'Code': 'code',
      'Other': 'more',
    }
    const categoryIcon = 'icon-' + icons[this.props.name] + ' ml-icon';

    let categoryHead
    if (this.props.libraryOpen) {
      categoryHead =  <div className='ML-cat'>
                        <div className='category-container' >
                          <span className='category-name'>{this.props.name}</span>
                        </div>
                      </div>
    } else {
      categoryHead =  <div
                        className='ML-cat'
                        onMouseEnter={this.openCategory}
                        onMouseLeave={this.collapseAll}
                      >
                        <div className='closed-ML--category' >
                          <span className={categoryIcon}></span>
                        </div>
                      </div>
    }

    // do not render list of modules if both library and category are closed
    let moduleList
    if (this.props.libraryOpen) {
      moduleList = <div className="ml-list">{this._renderModules()}</div>
    } else if (!this.state.collapsed) {
      moduleList = (
        <div className="ml-list-mini"
          onMouseEnter={this.openCategory}
          onMouseLeave={this.collapseAll}
          >
          {this._renderModules()}
        </div>
      )
    } else {
      moduleList = null
    }

    return (
      <div className="card closed-ML--category">
        <div className="module-category--wrapper">
          {categoryHead}
          {moduleList}
        </div>
      </div>
    )
  }
}


ModuleCategory.propTypes = {
  name:             PropTypes.string.isRequired,
  modules:          PropTypes.arrayOf(PropTypes.shape({
    id: PropTypes.number.isRequired,
    name: PropTypes.string.isRequired,
    icon: PropTypes.string.isRequired,
  })).isRequired,
  collapsed:        PropTypes.bool.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  libraryOpen:      PropTypes.bool.isRequired,
}
