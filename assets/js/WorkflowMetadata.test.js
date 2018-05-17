import React from 'react'
import WorkflowMetadata  from './WorkflowMetadata'
import { mount, ReactWrapper } from 'enzyme'
import { okResponseMock } from './test-utils'


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
  afterEach(() => wrapper.unmount())


  it('renders correctly', () => {
    expect(wrapper).toMatchSnapshot(); // 1
  })

  it('modal operates', (done) => {
    var publicLink = wrapper.find('.test-button');
    expect(publicLink).toHaveLength(1);
    publicLink.first().simulate('click');

    setImmediate(() => {
      const modal = wrapper.find('.modal-content');
      expect(modal.length).toBe(1); // dialog should be open

      wrapper.instance().reloadPageToEnsureConsistencyBecauseNavbarDoesntListenToState = jest.fn()

      // Dialog should be open, and have correct contents
      expect(wrapper).toMatchSnapshot(); // 2

      // Click the Private setting
      var privateButton = modal.find('.test-button-gray');
      expect(privateButton).toHaveLength(1);
      privateButton.first().simulate('click');

      setImmediate(() => {
        // Dialog should be closed, link should now say private
        //let modal_element = document.getElementsByClassName('modal-dialog');

        expect(publicLink.childAt(0).text()).toBe('-');
        expect(wrapper).toMatchSnapshot(); // 4

        // Check that the API was called
        expect(api.setWorkflowPublic).toHaveBeenCalledWith(100, true);

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
  afterEach(() => wrapper.unmount())

    it('renders correctly in read-only mode', () => {
      expect(wrapper).toMatchSnapshot(); // 5

      // check that privacy modal link does not render
      var publicLink = wrapper.find('.test-button');
      expect(publicLink).toHaveLength(0);
    })

});
