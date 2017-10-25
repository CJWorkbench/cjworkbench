import React from 'react'
import WorkflowMetadata  from './WorkflowMetadata'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock } from './utils'


describe('WorkflowMetadata - private mode', () => {

  var today = new Date('Fri Sep 22 2017 17:03:52 GMT-0400 (EDT)');
  var day_before = today.setDate(today.getDate() - 2);

  var workflow = {
    id: 100,
    public: false,
    owner_name: "Harry Harrison",
    last_update: day_before,
    read_only: false
  };

  var wrapper, api;

  beforeEach(() => {
    api = {
      setWorkflowPublic: okResponseMock()
    };

    wrapper = mount(
      <WorkflowMetadata
        workflow={workflow}
        api={api}
        test_now={today}
        isPublic={false}
      />);
  });


  it('renders correctly', () => {
    expect(wrapper).toMatchSnapshot(); // 1
  })

  it('modal operates', (done) => {
    var publicLink = wrapper.find('.test-button');
    expect(publicLink).toHaveLength(1);
    publicLink.first().simulate('click');

    setImmediate(() => {
      // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
      // So find them, and make a new Wrapper
      // Reference: "https://github.com/airbnb/enzyme/issues/252"
      let modal_element = document.getElementsByClassName('modal-content');
      expect(modal_element.length).toBe(1); // dialog should be open
      let modal = new ReactWrapper(modal_element[0], true);

      // Dialog should be open, and have correct contents
      expect(wrapper).toMatchSnapshot(); // 2
      expect(modal).toMatchSnapshot(); // 3

      // Click the Private setting
      var privateButton = modal.find('.test-button-gray');
      expect(privateButton).toHaveLength(1);
      privateButton.first().simulate('click');

      setImmediate(() => {
        // Dialog should be closed, link should now say private
        //let modal_element = document.getElementsByClassName('dialog-window');

        expect(publicLink.childAt(0).text()).toBe('public');
        expect(wrapper).toMatchSnapshot(); // 4

        // Check that the API was called
        expect(api.setWorkflowPublic.mock.calls.length).toBe(1);
        expect(api.setWorkflowPublic.mock.calls[0][0]).toBe(100);
        expect(api.setWorkflowPublic.mock.calls[0][1]).toBe(true);     // checking if False was passed in for isPublic argument

        expect(wrapper.state('isPublic')).toBe(true);
        done();
      });
    });
  });



});

describe('WorkflowMetadata - private mode', () => {

  var workflow;
  var wrapper;

  var today = new Date('Fri Sep 22 2017 17:03:52 GMT-0400 (EDT)');
  var day_before = today.setDate(today.getDate() - 2);  

  var api = {
    setWorkflowPublic: okResponseMock()
  };

  beforeEach(() => {
      
    workflow = {
      id: 100,
      public: true,
      owner_name: "Harry Harrison",
      last_update: day_before,
      read_only: true
    };

    wrapper = mount(
      <WorkflowMetadata
        workflow={workflow}
        api={api}
        test_now={today}
        isPublic={true}
      />);
    });
      
    it('renders correctly in read-only mode', () => {
      expect(wrapper).toMatchSnapshot(); // 5
  
      // check that privacy modal link does not render
      var publicLink = wrapper.find('.test-button');
      expect(publicLink).toHaveLength(0);
    })

});




