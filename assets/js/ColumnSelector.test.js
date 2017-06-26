import React from 'react'
import ColumnSelector from './ColumnSelector'
import renderer from 'react-test-renderer'

it('renders correctly', () => {
  const tree = renderer.create(
    <ColumnSelector
      selectedCols='foo,bar,baz'
      getColNames={ () => { return Promise.resolve(['foo,bar,baz,wow,word wrap,ok then']) } }
      saveState={ () => {} }
      revision={101} />
  ).toJSON();
  expect(tree).toMatchSnapshot();
});




