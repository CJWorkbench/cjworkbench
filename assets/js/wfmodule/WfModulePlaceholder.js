import React from "react";
import { sortableWfModule } from './WfModuleDragDropConfig';

export default class WfModulePlaceholder extends React.Component {
  constructor(props) {
    super(props);
  }

  render() {
    return <div className="wf-card placeholder mx-auto" />;
  }
}