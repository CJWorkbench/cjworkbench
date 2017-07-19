import React from 'react'
import { WorkflowListNavBar, WorkflowNavBar } from './navbar'
import renderer from 'react-test-renderer'

it('WorkflowListNavBar renders correctly', () => {
  const tree = renderer.create(
    <WorkflowListNavBar />
  ).toJSON();
  expect(tree).toMatchSnapshot();
});

it('WorkflowNavBar renders correctly', () => {
  const tree = renderer.create(
    <WorkflowNavBar addButton={<div />} workflowId={1} api={{}}/>
  ).toJSON();
  expect(tree).toMatchSnapshot();
});



