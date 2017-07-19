import React from 'react'
import WfHamburgerMenu  from './WfHamburgerMenu'
import renderer from 'react-test-renderer'

it('renders correctly', () => {
  const tree = renderer.create(
    <WfHamburgerMenu workflowId={1}/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

it('renders correctly for workflows list page', () => {
  const tree = renderer.create(
    <WfHamburgerMenu />
  ).toJSON();
  expect(tree).toMatchSnapshot();
});



