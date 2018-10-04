import React from 'react'
import WorkflowNavBar from './WorkflowNavBar'
import { mount } from 'enzyme'
const Utils = require('./utils');
import { jsonResponseMock } from './test-utils'


describe('WorkflowNavBar', () => {
  let wrapper;
  let user;
  let workflow;
  const mockWorkflowCopy = {
    id: 77,
    name: 'Copy of Original Version',
    owner_name: 'Paula Plagarizer',
    public: false
  };
  let api;

  let globalGoToUrl;
  beforeEach(() => {
    wrapper = null
    globalGoToUrl = Utils.goToUrl;
    Utils.goToUrl = jest.fn();
    api = {
      duplicateWorkflow: jsonResponseMock(mockWorkflowCopy),
    };
  })
  afterEach(() => {
    Utils.goToUrl = globalGoToUrl
    if (wrapper) wrapper.unmount();
  })

  it('With user logged in, Duplicate button sends user to new copy', (done) => {
    user = {
      id: 8
    };
    workflow = {
      id: 12,
      name: 'Original Version',
      owner_name: 'John Johnson',
      public: true
    };

    Utils.goToUrl = jest.fn();

    wrapper = mount(
      <WorkflowNavBar
        workflow={workflow}
        api={api}
        isReadOnly={false}
        loggedInUser={user}
        onChangeIsPublic={jest.fn()}
      />
    );

    expect(wrapper).toMatchSnapshot();
    expect(wrapper.state().spinnerVisible).toBe(false);

    let button = wrapper.find('button[name="duplicate"]')
    expect(button).toHaveLength(1);
    button.first().simulate('click');

    // spinner starts immediately
    expect(wrapper.state().spinnerVisible).toBe(true);

    // then we wait for promise to resolve
    setImmediate( () => {
      expect(Utils.goToUrl).toHaveBeenCalledWith('/workflows/77');
      expect(api.duplicateWorkflow).toHaveBeenCalled();
      done();
    });
  });

  it('With user NOT logged in, Duplicate button sends user to sign-in page', (done) => {
    workflow = {
      id: 303,
      name: 'Original Version',
      owner_name: 'Not LogggedIn',
      public: true
    };

    wrapper = mount(
      <WorkflowNavBar
        workflow={workflow}
        api={api}
        isReadOnly={false}      // no loggedInUser prop
        onChangeIsPublic={jest.fn()}
      />
    );

    expect(wrapper).toMatchSnapshot();

    let button = wrapper.find('button[name="duplicate"]')
    expect(button).toHaveLength(1);
    button.simulate('click');

    // wait for promise to resolve
    setImmediate( () => {
      expect(Utils.goToUrl).toHaveBeenCalledWith('/account/login');
      expect(api.duplicateWorkflow.mock.calls.length).toBe(0);
      done();
    });

  });
});
