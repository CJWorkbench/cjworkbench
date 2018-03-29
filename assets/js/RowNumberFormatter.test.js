import React from 'react'
import { shallow } from 'enzyme'
import { RowNumberFormatter } from "./DataGrid"

it('Renders a 2-digit row number in base font size', () => {

  var wrapper = shallow( <RowNumberFormatter
    value={10}
  />);
  expect(wrapper.find('.row-number')).toHaveLength(1);
});


it('Renders a 3-digit row number in smaller font size', () => {

  var wrapper = shallow( <RowNumberFormatter
    value={100}
  />);
  expect(wrapper.find('.row-number-3')).toHaveLength(1);
});


it('Renders a 4-digit row number in even smaller font size', () => {

  var wrapper = shallow( <RowNumberFormatter
    value={1000}
  />);
  expect(wrapper.find('.row-number-4')).toHaveLength(1);
});




