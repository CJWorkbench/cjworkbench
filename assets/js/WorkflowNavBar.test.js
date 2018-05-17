import React from 'react'
import WorkflowNavBar from './WorkflowNavBar'
import { shallow, mount, ReactWrapper } from 'enzyme'
const Utils = require('./utils');
import { jsonResponseMock, okResponseMock } from './test-utils'


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
    globalGoToUrl = Utils.goToUrl;
    Utils.goToUrl = jest.fn();
    api = {
      duplicateWorkflow: jsonResponseMock(mockWorkflowCopy),
      setWorkflowPublic: okResponseMock()
    };
  })
  afterEach(() => {
    Utils.goToUrl = globalGoToUrl
    wrapper.unmount();
  })

  it('With user logged in, Duplicate button sends user to new copy', (done) => {
    user = {
      id: 8
    };
    workflow = {
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
      />
    );

    expect(wrapper).toMatchSnapshot(); 
    expect(wrapper.state().spinnerVisible).toBe(false);

    let button = wrapper.find('.test-duplicate-button');
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
      />
    );

    expect(wrapper).toMatchSnapshot(); 

    let button = wrapper.find('.test-duplicate-button');
    expect(button).toHaveLength(1);
    button.simulate('click');

    // wait for promise to resolve
    setImmediate( () => {
      expect(Utils.goToUrl).toHaveBeenCalledWith('/account/login');
      expect(api.duplicateWorkflow.mock.calls.length).toBe(0);
      done();
    });

  });

  it('In Private mode, Share button invites user to set to Public', (done) => {
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
      />
    );

    expect(wrapper).toMatchSnapshot();
    expect(wrapper.state().modalsOpen).toBe(false);
    
    let button = wrapper.find('.test-share-button');
    expect(button).toHaveLength(1);
    button.simulate('click');

    expect(wrapper.state().modalsOpen).toBe(true);      

    const setpubModal = wrapper.find('div.test-setpublic-modal');
    expect(setpubModal).toMatchSnapshot(); 

    const setPublicButton = setpubModal.find('.test-public-button');
    setPublicButton.simulate('click');

    // wait for promise to resolve
    setImmediate( () => {
      wrapper.update()
      // find the Share modal & wrap it
      const shareModal = wrapper.find('div.test-share-modal');
      expect(shareModal).toMatchSnapshot(); 
    
      // check that link has rendered correctly
      const linkField = shareModal.find('input.test-link-field');
      expect(linkField.length).toBe(1);
      // Need to fix this once correct link string in place
      // expect(linkField.props().placeholder).toEqual("");
    
      expect(api.setWorkflowPublic).toHaveBeenCalled();
      done();
    });
  });


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
      />
    );

    expect(wrapper).toMatchSnapshot();
    expect(wrapper.state().modalsOpen).toBe(false);
    
    let button = wrapper.find('.test-share-button');
    expect(button).toHaveLength(1);
    button.simulate('click');

    expect(wrapper.state().modalsOpen).toBe(true);      

    const shareModal = wrapper.find('div.test-share-modal');
    expect(shareModal).toMatchSnapshot(); 

    // check that link has rendered correctly
    const linkField = shareModal.find('input.test-link-field');
    expect(linkField.length).toBe(1);
    expect(linkField.props().placeholder).toEqual("/workflows/808");
  
    expect(api.setWorkflowPublic).not.toHaveBeenCalled();
  });
});
