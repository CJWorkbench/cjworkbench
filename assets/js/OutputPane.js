// Display of output from currently selected module

import React from 'react';
import TableView from './TableView'


export default class OutputPane extends React.Component {

  constructor(props) {
    super(props);
  }

  render() {

    return (
      <div className="bg-faded">
        <TableView id={this.props.id} revision={this.props.revision} />
      </div>
    );
  }
}

OutputPane.propTypes = {
  id: React.PropTypes.number,
  revision: React.PropTypes.number
};


