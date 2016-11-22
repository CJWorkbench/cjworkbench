import React from 'react';
import ReactDOM from 'react-dom';
import { sortable } from 'react-sortable';

// return ID in URL of form "/workflows/id/" or "/workflows/id"
var getPageID = function () {
  var url = window.location.pathname;

  // trim trailing slash if needed
  if (url.lastIndexOf('/' == url.length-1)
    url = url.substring(0, url.length-1);

  // take everything after last slash as the id
  var id = url.substring(url.lastIndexOf('/')+1);
  return id
};

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

    // If we'd ended a drag, we need to post the new order
    if (newState.draggingIndex === null) {
      console.log("You moved my cheese")
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


ReactDOM.render(
    <SortableList/>,
    document.getElementById('root')
);