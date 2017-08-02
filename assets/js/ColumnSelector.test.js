import React from 'react'
import ColumnSelector from './ColumnSelector'
import { mount } from 'enzyme'

it('renders correctly', () => {
  const wrapper = mount(
    <ColumnSelector
      selectedCols='foo,bar,baz'
      getColNames={ () => { return Promise.resolve(['foo,bar,baz,wow,word wrap,ok then']) } }
      saveState={ () => {} }
      revision={101} 
    />
  );
  expect(wrapper).toMatchSnapshot();
});



