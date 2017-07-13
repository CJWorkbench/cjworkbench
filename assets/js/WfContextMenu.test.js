import React from 'react'
import WfContextMenu  from './WfContextMenu'
import renderer from 'react-test-renderer'

it('WfContextMenu renders correctly', () => {
  const tree = renderer.create(
    <WfContextMenu removeModule={ () => {} } />
  ).toJSON();
  expect(tree).toMatchSnapshot();
});





