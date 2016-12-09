// This is the main script for the Workflow view

import React from 'react';
import ReactDOM from 'react-dom';
import { sortable } from 'react-sortable';

// return ID in URL of form "/workflows/id/" or "/workflows/id"
var getPageID = function () {
  var url = window.location.pathname;

  // trim trailing slash if needed
  if (url.lastIndexOf('/' == url.length-1))
    url = url.substring(0, url.length-1);

  // take everything after last slash as the id
  var id = url.substring(url.lastIndexOf('/')+1);
  return id
};


// ---- ButtonMenu ----
class ButtonMenu extends React.Component {

  constructor(props) {
    super(props);
    this.state = { open: false, items: []};

    // annoying bind to make 'this' accessible in handlers
    this.click= this.click.bind(this);
    this.blur= this.blur.bind(this);
  }

  componentDidMount() {
    this.setState({open: false, items: ['one', 'two', 'three']});
  }

  click() {
    var newOpen = !this.state.open;
    this.setState( { open: newOpen});
  }

  // close the menu when user clicks anywhere else
  blur() {
    this.setState( { open: false});
  }

  render() {
    return (
        <div className="toolMenuOuter" onBlur={this.blur}>
            <button className="toolMenuButton" onClick={this.click}>+</button>
            <ul className="toolMenuItemHolder" style={{display: this.state.open ? 'block' : 'none'}}>
              {this.state.items.map(
                  item => {return <li className="toolMenuItem" key={item}>{item}</li>;})
              }
            </ul>
        </div>
    );
  }
}


// ---- Toolbar and buttons ----


class ToolBar extends React.Component {
  renderButton(_text) {
    return <ToolButton text={_text}/>;
  }

  render() {
    return (
         <ButtonMenu/>
    ); 
  } 
}

// ---- Sortable Modules ----
var ListItem = React.createClass({
  displayName: 'SortableListItem',

  render: function() {
    return (
      <div {...this.props} className="module-li">{this.props.children}</div>
    )
  }
})

var SortableListItem = sortable(ListItem);

var SortableList = React.createClass({

  getInitialState: function() {
    return {
      draggingIndex: null,
      data: { modules: [] }
    };
  },

  updateState: function(newState) {
    this.setState(newState);

    // If we've ended a drag, we need to post the new order to the server
    if (newState.draggingIndex === null) {

      // Generate a JSON paylod that has only module ID and order, then PATCH
      var newOrder = this.state.data.modules.map( (item, i) => ({id: item.id, order: i}) )

      fetch('/api/workflows/' + getPageID(), {
        method: 'patch',
        headers: {
          'Accept': 'application/json',
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(newOrder) })
      .catch( (error) => { console.log('Request failed', error); });
    }
  },

  componentDidMount: function() {
    var _this = this;
    fetch('/api/workflows/' + getPageID())
      .then(response => response.json())
      .then(json => {
        _this.setState({data: json}) })
  },

  render: function() {
    var childProps = { className: 'myClass1' };
    var listItems = this.state.data.modules.map(function(item, i) {
      return (
        <SortableListItem
          key={i}
          updateState={this.updateState}
          items={this.state.data.modules}
          draggingIndex={this.state.draggingIndex}
          sortId={i}
          outline="list"
          childProps={childProps}
          >{item.module.name}</SortableListItem>
      );
    }, this);

    return (
          <div className="list">{listItems}</div>
    )
  }
});

// ---------- Main ----------

class WorkflowMain extends React.Component {
  render() {
    return (
      <div>
        <div className="toolbar">
          <ToolBar/>
        </div>
        <SortableList/>
      </div>
    );
  }
}
ReactDOM.render(
    <WorkflowMain/>,
    document.getElementById('root')
);