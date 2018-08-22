import React from 'react'
import ConnectedWorkflowNavBar, { WorkflowNavBar } from './WorkflowNavBar'
import { shallow, mount, ReactWrapper } from 'enzyme'
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

  it('In Private mode, Share button invites user to set to Public', () => {
    user = {
      id: 99
    };
    workflow = {
      id: 808,
      name: 'Original Version',
      owner_name: 'Fred Frederson',
      public: false,
    };

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
    expect(wrapper.state().modalsOpen).toBe(false);

    let button = wrapper.find('button[name="share"]')
    expect(button).toHaveLength(1);
    button.simulate('click');

    expect(wrapper.state().modalsOpen).toBe(true);

    const setPublicButton = wrapper.find('button[title="Make Public"]')
    setPublicButton.simulate('click');

    expect(wrapper.prop('onChangeIsPublic')).toHaveBeenCalledWith(808, true)
  })


  it('In Public mode, Share button opens modal with links', () => {
    user = {
      id: 47
    };
    workflow = {
      id: 808,
      name: 'Original Version',
      owner_name: 'Fred Frederson',
      public: true,
    };
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
    expect(wrapper.state().modalsOpen).toBe(false);

    let button = wrapper.find('button[name="share"]')
    expect(button).toHaveLength(1);
    button.simulate('click');

    expect(wrapper.state().modalsOpen).toBe(true);

    // check that link has rendered correctly
    const linkField = wrapper.find('input[name="url"]')
    expect(linkField.length).toBe(1);
    expect(linkField.props().value).toEqual("http://localhost/workflows/808");

    expect(wrapper.prop('onChangeIsPublic')).not.toHaveBeenCalled()
  });
});
