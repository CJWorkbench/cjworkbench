import React from 'react'
import { WorkflowListNavBar, WorkflowNavBar } from './navbar'
import { mount } from 'enzyme'


it('WorkflowListNavBar renders correctly', () => {
  const wrapper = mount(
    <WorkflowListNavBar />
  );
  expect(wrapper).toMatchSnapshot();
});

it('WorkflowNavBar renders correctly', () => {
  const wrapper = mount(
    <WorkflowNavBar addButton={<div />} workflowId={1} api={{}}/>
  );
  expect(wrapper).toMatchSnapshot();
});

