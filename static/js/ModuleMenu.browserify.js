// A menu to select a module addition

import React from 'react';

export default class ModuleMenu extends React.Component {

  constructor(props) {
    super(props);
    this.state = { open: false, items: []};

    // annoying bind to make 'this' accessible in handlers
    this.buttonClick = this.buttonClick.bind(this);
    this.itemMouseDown = this.itemMouseDown.bind(this);
    this.itemClick = this.itemClick.bind(this);
    this.blur = this.blur.bind(this);
  }

  componentDidMount() {
    var _this = this;
    fetch('/api/modules/')
      .then(response => response.json())
      .then(json => {
        _this.setState({open: false, items: json}) })
  }

  buttonClick() {
    // Toggle menu state
    var newOpen = !this.state.open;
    this.setState( { open: newOpen});
  }

  itemMouseDown(evt) {
    evt.preventDefault();    // so the menu button doesn't lose focus and trigger blur, preventing item clicked
  }

  itemClick(evt) {
    var itemID = evt.target.getAttribute('data-id');
    this.props.addModule(itemID);
    this.setState( { open: false});
  }

  // close the menu when user clicks anywhere but on a menu item
  blur() {
    this.setState({ open: false});
  }

  render() {
    return (
        <div className="toolMenuOuter" onBlur={this.blur}>
            <button className="toolMenuButton" onClick={this.buttonClick}>+</button>
            <ul className="toolMenuItemHolder" style={{display: this.state.open ? 'block' : 'none'}}>
              {this.state.items.map(
                  item => {return <li className="toolMenuItem" key={item.id} data-id={item.id} onMouseDown={this.itemMouseDown} onClick={this.itemClick}> {item.name} </li>;})
              }
            </ul>
        </div>
    );
  }
}

