/**
 * A component that holds a collection of modules for a given category. For example,
 * Category: Source
 * Modules: Load URL, Paste CSV, Twitter
 *
 * Category: Wrangle
 * Modules: Melt, Select Columns
 *
 * Categories should be expandable and collapsible, just like each individual module.
 */

import React from 'react'
import PropTypes from 'prop-types'
import Module from './Module'
import { Collapse, Button, CardBlock, Card } from 'reactstrap';

export default class ModuleCategory extends React.Component {
  constructor(props) {
    super(props);
    this.state = {
      collapsed: props.collapsed,
    };

    this.toggleCollapse = this.toggleCollapse.bind(this)
  }

  toggleCollapse() {
    var newCollapsed = !this.state.collapsed;
    this.setState({collapsed: newCollapsed});
    if (!newCollapsed) {
      this.props.setOpenCategory(this.props.name); // tell parent, so it can close other cats
    }
  }

  // When our props change, update our collapsed state (this is the other end of setOpenCategory)
  componentWillReceiveProps(newProps) {
    this.setState({collapsed: newProps.collapsed})
  }

  render() {
    var isOpen = !this.state.collapsed;

    // Provides margins around opened library category
    var cardClass = isOpen
      ? 'card b-l-gray library-card-category-open'
      : 'card b-l-gray library-card-category-closed';

    var symbol = isOpen
      ? 'icon-sort-down-vl-gray ml-sort button-icon-library ml-3 mb-1'
      : 'icon-sort-right-vl-gray button-icon-library ml-3';

    // --- Need a mapping of category-to-icon before implementing
    // var icon = 'icon-' + ??? + ' button-icon mr-2';

    return (
      <div className={cardClass}>
        <div className="cat-open">
          <div className='first-level d-flex align-items-center'onClick={this.toggleCollapse}>
            <div className='cat-container'>
              <div className={symbol} />
              {/* <span className={icon}></span> */}
              <span className='content-3 t-vl-gray ml-3 ml-cat'>{this.props.name}</span>
            </div>
          </div>
          <div>
            <Collapse className='' isOpen={isOpen}>
              <div className="ml-list">{this.props.modules}</div>
            </Collapse>
          </div>
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
  isReadOnly:       PropTypes.bool.isRequired
};
