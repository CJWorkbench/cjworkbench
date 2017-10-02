import React from 'react'
import { WorkflowListNavBar, WorkflowNavBar } from './navbar'
import { shallow, mount } from 'enzyme'
const Utils = require('./utils');
import { mockResponse, jsonResponseMock } from './utils'


describe('NavBar', () => {

  var wrapper;
  var user;
  var workflow;
  var mockWorkflowCopy = {
    id: 77,
    name: "Copy of Original Version"
  }
  var api = {
    duplicate: jsonResponseMock(mockWorkflowCopy)
  };

  // Over-write default behavior (changing page)
  Utils.goToUrl = jest.fn();
  window.fetch = jest.fn().mockImplementation(()=>
    Promise.resolve(mockResponse(200, null, JSON.stringify(mockWorkflowCopy)))
  );

  describe('WorkflowListNavBar', () => {

    it('Renders correctly', () => {
      wrapper = shallow(
        <WorkflowListNavBar />
      );
      expect(wrapper).toMatchSnapshot();
    });

  });

  describe('WorkflowNavBar', () => {
    
    it('Renders without Duplicate button in Private mode', () => {
      user = {
        id: 8
      };
      workflow = {
        name: "Original Version",
        public: false
      }
      wrapper = mount(
        <WorkflowNavBar
          workflow={workflow}
          api={api}
          isReadOnly={false}
          user={user}
        />
      )
      expect(wrapper).toMatchSnapshot();

      // confirm that button is not there
      let button = wrapper.find('.test-duplicate-button');
      expect(button.exists()).toBe(false);

    });

    it('Renders Duplicate button in Public mode with user logged in, sends user to new copy', (done) => {
      user = {
        id: 8
      };
      workflow = {
        name: "Original Version",
        public: true
      }
      wrapper = mount(
        <WorkflowNavBar
          workflow={workflow}
          api={api}
          isReadOnly={false}
          user={user}
        />
      )
      expect(wrapper).toMatchSnapshot();
      expect(wrapper.state().spinnerVisible).toBe(false);

      let button = wrapper.find('.test-duplicate-button');
      expect(button).toHaveLength(1);
      button.first().simulate('click');

      // spinner starts immediately
      expect(wrapper.state().spinnerVisible).toBe(true);
      
      // then we wait for promise to resolve
      setImmediate( () => {
        // no snapshot test here: 
        //  we have not actually rendered the new workflow copy, just mocked the calls to change url
      
        expect(Utils.goToUrl.mock.calls.length).toBe(1);
        expect(Utils.goToUrl.mock.calls[0][0]).toBe('/workflows/77');
        expect(api.duplicate.mock.calls.length).toBe(1);
        done();
      });
    });
    
    it('Renders Duplicate button in Public mode with user NOT logged in, sends user to sign-in page', (done) => {
      user = {
        id: null
      };
      workflow = {
        name: "Original Version",
        public: true
      }
      wrapper = mount(
        <WorkflowNavBar
          workflow={workflow}
          api={api}
          isReadOnly={false}
          user={user}
        />
      )
      expect(wrapper).toMatchSnapshot();

      let button = wrapper.find('.test-duplicate-button');
      expect(button).toHaveLength(1);
      button.simulate('click');

      // wait for promise to resolve
      setImmediate( () => {
        // no snapshot test here: 
        //  we have not actually rendered the sign in page, just mocked the calls to change url
      
        // goToUrl() called once previously
        expect(Utils.goToUrl.mock.calls.length).toBe(2);
        expect(Utils.goToUrl.mock.calls[1][0]).toBe('/account/login');
        // check that API was NOT called (has one call from last test)
        expect(api.duplicate.mock.calls.length).toBe(1);
        done();
      });

    });

  });
  
});

