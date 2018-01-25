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
  }

  // When our props change, update our collapsed state (this is the other end of setOpenCategory)
  componentWillReceiveProps(newProps) {
    this.setState({collapsed: newProps.collapsed})
  }

  toggleCollapse() {
    var newCollapsed = !this.state.collapsed;
    this.setState({collapsed: newCollapsed});
    this.props.setOpenCategory(newCollapsed ? null : this.props.name); // tell parent, so it can close other cats
  }

  render() {
    var isOpen = !this.state.collapsed;

    // Provides margins around opened library category
    var cardClass = isOpen
      ? 'card b-l-gray library-card-category-open'
      : 'card b-l-gray library-card-category-closed';

    var sort = isOpen
      ? 'icon-sort-up-vl-gray ml-sort mb-1'
      : 'icon-sort-down-vl-gray ml-sort mb-1';

    // Grabs icon from first module in category for category icon
    var icon = 'icon-' + this.props.modules[0].props.icon + ' ml-icon';

    var categoryHead = (this.props.libraryOpen)
      ? <div className='first-level' onClick={this.toggleCollapse} >
          <div className='cat-container' >
            <div className={sort} />
            <span className='open-ML-cat'>{this.props.name}</span>
          </div>
        </div>
      : <div className='first-level' onMouseEnter={this.toggleCollapse} >
          <div className='cat-container closed-ML-cat' >
            <span className={icon}></span>
          </div>
        </div>

    var moduleList = (this.props.libraryOpen)
      ? <Collapse isOpen={isOpen}>
          <div className="ml-list">{this.props.modules}</div>
        </Collapse>
      : <div className="ml-list-mini" style={{ display : (isOpen) ? 'block' : 'none'}}>
          {this.props.modules}
        </div>

    return (
      <div className={cardClass} >
        <div className="ml-cat" >
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
