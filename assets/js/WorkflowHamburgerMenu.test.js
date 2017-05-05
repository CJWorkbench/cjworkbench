import React from 'react';
import WorkflowHamburgerMenu  from './WorkflowHamburgerMenu';
import renderer from 'react-test-renderer';

it('renders correctly', () => {
  const tree = renderer.create(
    <WorkflowHamburgerMenu/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

it('renders correctly for workflows list page', () => {
  const tree = renderer.create(
    <WorkflowHamburgerMenu workflowsPage/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});



