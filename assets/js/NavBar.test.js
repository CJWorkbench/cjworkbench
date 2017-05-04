import React from 'react';
import { NavBar, WorkflowNavBar } from './navbar';
import renderer from 'react-test-renderer';

it('NavBar renders correctly', () => {
  const tree = renderer.create(
    <NavBar />
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

it('WorkflowNavBar renders correctly', () => {
  const tree = renderer.create(
    <WorkflowNavBar addButton={<div />} workflowTitle='Workflow Title'/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});



