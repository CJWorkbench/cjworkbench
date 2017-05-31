// Display of output from currently selected module

import React from 'react';
import TableView from './TableView'


export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);
  }

  render() {
    // Don't show anything if we don't have a selected WfModule to show
    var tableView = null;
    if (this.props.id)
      tableView = <TableView id={this.props.id} revision={this.props.revision} />;

    return (
      <div className="bg-faded">
        {tableView}
      </div>
    );
  }
}

OutputPane.propTypes = {
  id: React.PropTypes.number,
  revision: React.PropTypes.number
};


