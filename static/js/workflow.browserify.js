import React from 'react';
import ReactDOM from 'react-dom';
import { sortable } from 'react-sortable';

var ListItem = React.createClass({
  displayName: 'SortableListItem',
  render: function() {
    return (
      <div {...this.props} className="list-item">{this.props.children}</div>
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

  updateState: function(obj) {
    this.setState(obj);
  },

  componentDidMount: function() {
    console.log("CDM!")
    var _this = this;
    fetch('/api/workflows/2')
      .then(response => response.json())
      .then(json => {
        _this.setState({data: json}) })
  },

  render: function() {
    console.log(this.state.data)
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