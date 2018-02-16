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
      collapsed: props.collapsed
    };
    this.toggleCollapse = this.toggleCollapse.bind(this);
    this.collapseAll = this.collapseAll.bind(this);
  }

  // When our props change, update our collapsed state (this is the other end of setOpenCategory)
  componentWillReceiveProps(newProps) {
    this.setState({collapsed: newProps.collapsed})
  }

  toggleCollapse() {
    var newCollapsed = !this.state.collapsed;
    this.props.setOpenCategory(newCollapsed ? null : this.props.name); // tell parent, so it can close other cats
  }

  collapseAll() {
    this.props.setOpenCategory(null); // tell parent to close all
  }

  render() {
    var isOpen = !this.state.collapsed;

    // Provides margins around opened library category
    var cardClass = isOpen ? 'library-card-category-open' : 'library-card-category-closed';

    var sortIcon = isOpen ? 'icon-sort-up-vl-gray' : 'icon-sort-down-vl-gray';

    // ??? are these the correct icons per category ???
    const icons = {
      'Add data': 'database',
      'Analyze': 'notepad',
      'Prepare':'wrangle',
      'Visualize': 'chart',
      'Code': 'code',

    }
    var categoryIcon = 'icon-' + icons[this.props.name] + ' ml-icon';

    var categoryHead;
    if (this.props.libraryOpen) {
      categoryHead =  <div className='first-level' onClick={this.toggleCollapse} >
                        <div className='cat-container' >
                          <span className='open-ML-cat'>{this.props.name}</span>
                          <div className={'ml-sort ' + sortIcon} />
                        </div>
                      </div>
    } else {
      categoryHead =  <div className='first-level' onMouseEnter={this.toggleCollapse} >
                        <div className='closed-ML-cat' >
                          <span className={categoryIcon}></span>
                        </div>
                      </div>
    }

    // do not render list of modules if both library and category are closed
    var moduleList;
    if (this.props.libraryOpen) {
      moduleList =  <Collapse isOpen={isOpen}>
                      <div className="ml-list">{this.props.modules}</div>
                    </Collapse>
    } else if (isOpen) {
      moduleList =  <div className="ml-list-mini" onMouseLeave={this.collapseAll}>
                      {this.props.modules}
                    </div>
    } else {
      moduleList = null;
    }

    return (
      <div className={"card b-l-gray " + cardClass}>
        <div className="ml-cat">
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
