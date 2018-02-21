import React from 'react'
import CellEditor from './CellEditor'
import { mount } from 'enzyme'

describe('CellEditor', () => {

  const testParam = '[\n' +
    '    { "row": 3, "col": "foo", "value":"bar" },\n' +
    '    { "row": 6, "col": "food", "value":"sandwich" },\n' +
    '    { "row": 5, "col": "foo", "value":"gak" },\n' +
    '    { "row": 17,  "col": "food", "value":"pizza" }\n' +
    ' ]';

  it('Renders correctly', () => {
    var wrapper = mount(
      <CellEditor
        edits={testParam}
        onSave={() => {}}
      />);

    expect(wrapper.find('.cell-edits--column')).toHaveLength(2);
    expect(wrapper.find('.cell-edits--row')).toHaveLength(4);

    expect(wrapper).toMatchSnapshot();
  });

  it('Renders empty data', () => {
     var wrapper = mount(
      <CellEditor
        edits={''}
        onSave={() => {}}
      />);

    expect(wrapper.find('.cell-edits--column')).toHaveLength(0);
    expect(wrapper.find('.cell-edits--row')).toHaveLength(0);

    expect(wrapper).toMatchSnapshot();
  });

});
