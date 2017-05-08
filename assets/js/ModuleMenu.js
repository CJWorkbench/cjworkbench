// A menu to select a module addition
import React from 'react';
import { UncontrolledDropdown, DropdownToggle, DropdownMenu, DropdownItem } from 'reactstrap';

export default class ModuleMenu extends React.Component {
  constructor(props) {
    super(props);
    this.itemClick = this.itemClick.bind(this);
    this.state = {
      items: []
    };
  }

  componentDidMount() {
    var _this = this;
    fetch('/api/modules/', { credentials: 'include'})
      .then(response => response.json())
      .then(json => {
        // Sort modules first by category, then name
        json.sort( (a,b) => { return a.category > b.category || (a.category==b.category && a.name > b.name) } );
        _this.setState({dropdownOpen: this.state.dropdownOpen, items: json}) })
  }

  itemClick(evt) {
    var itemID = evt.target.getAttribute('data-id');
    this.props.addModule(itemID);
  }

  render() {

    // Construct list of modules, separated by category
    var menuItems = [];
    var lastCategory = undefined;
    for (var item of this.state.items) {
      if (item.category != lastCategory) {
        if (lastCategory)
          menuItems.push(<DropdownItem divider key={item.id*1000} />);
        menuItems.push(<DropdownItem header key={item.id*1000 + 1}> {item.category} </DropdownItem>);
        lastCategory = item.category;
      }
      menuItems.push(<DropdownItem className='ml-2' key={item.id} data-id={item.id} onClick={this.itemClick}> {item.name} </DropdownItem>);
    }

    return (
      <UncontrolledDropdown>
        <DropdownToggle caret>
          Add Module
        </DropdownToggle>
        <DropdownMenu>
          {menuItems}
        </DropdownMenu>
      </UncontrolledDropdown>
    );
  }
}

ModuleMenu.propTypes = {
  addModule:  React.PropTypes.func,
};
