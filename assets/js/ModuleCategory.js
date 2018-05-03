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

  render() {
    var isOpen = !this.state.collapsed;

    // Provides margins around opened library category

    const icons = {
      'Add data': 'database',
      'Clean': 'wrangle',
      'Analyze': 'notepad',
      'Visualize': 'chart',
      'Code': 'code',
      'Other': 'more'
    };
    var categoryIcon = 'icon-' + icons[this.props.name] + ' ml-icon';

    var categoryHead;
    if (this.props.libraryOpen) {
      categoryHead =  <div className='first-level'>
                        <div className='category-container' >
                          <span className='category-name'>{this.props.name}</span>
                        </div>
                      </div>
    } else {
      categoryHead =  <div
                        className='first-level'
                        onMouseEnter={this.openCategory}
                        onMouseLeave={this.collapseAll}
                      >
                        <div className='closed-ML--category' >
                          <span className={categoryIcon}></span>
                        </div>
                      </div>
    }

    // do not render list of modules if both library and category are closed
    var moduleList;
    if (this.props.libraryOpen) {
      moduleList =  <div className="ml-list">{this.props.modules}</div>

    } else if (isOpen) {
      moduleList =  <div
                      className="ml-list-mini"
                      onMouseEnter={this.openCategory}
                      onMouseLeave={this.collapseAll}
                    >
                      {this.props.modules}
                    </div>
    } else {
      moduleList = null;
    }

    return (
      <div className="card module-category--open">
        <div className="module-category--wrapper">
          {categoryHead}
          {moduleList}
        </div>
      </div>
    );
  }
}


ModuleCategory.propTypes = {
  name:             PropTypes.string.isRequired,
  modules:          PropTypes.arrayOf(PropTypes.object).isRequired,
  collapsed:        PropTypes.bool.isRequired,
  setOpenCategory:  PropTypes.func.isRequired,
  isReadOnly:       PropTypes.bool.isRequired,
  libraryOpen:      PropTypes.bool.isRequired
};
