import React from 'react'
import DataVersionSelect  from './DataVersionSelect'
import { mount, shallow, ReactWrapper } from 'enzyme'
import { okResponseMock, jsonResponseMock } from './utils'

jest.useFakeTimers();

describe('DataVersionSelect', () => {

  // Force time zone to make sure tests always give same result
  //process.env.TZ = 'UTC';
  // how many hours off from UTC are we? print tests all in UTC
  var localToUTC = (new Date()).getTimezoneOffset();  
  var mockVersions = {
    versions: [
      '2017-07-10 17:57:58.324', 
      '2017-06-10 17:57:58.324', 
      '2017-05-10 17:57:58.324', 
      '2017-04-10 17:57:58.324', 
      '2017-03-10 17:57:58.324'
    ],
    selected: '2017-04-10 17:57:58.324'
  };
  var api = {
    getWfModuleVersions: jsonResponseMock(mockVersions),
    setWfModuleVersion: okResponseMock(),
  };
  var wrapper;  
  var modalLink;

  // Mount is necessary to invoke componentDidMount()
  beforeEach(() => wrapper = mount(
    <DataVersionSelect
      isReadOnly={false}
      wfModuleId={808}
      revision={202}
      api={api}
      timezoneOffset={localToUTC}          
    />
  ));
  beforeEach(() => modalLink = wrapper.find('div.open-modal'));    

  it('Renders correctly when in Private mode, and selection is confirmed when user hits OK', (done) => { 

    // should call API for its data on componentDidMount
    expect(api.getWfModuleVersions.mock.calls.length).toBe(1);

    // Snapshots on the wrapper will fail in Travis b/c it compares the `localToUTC` value
    // expect(wrapper).toMatchSnapshot();

    // Start with dialog closed
    expect(wrapper.state().modalOpen).toBe(false)

    expect(modalLink).toHaveLength(1);
    modalLink.simulate('click');
    expect(wrapper.state().modalOpen).toBe(true);

    // Need setImmediate to give modal a chance to fill with data, API returns a promise that must resolve  
    setImmediate( () => {
      expect(wrapper.state().modalOpen).toBe(true)

      // The insides of the Modal are a "portal", that is, attached to root of DOM, not a child of Wrapper
      // So find them, and make a new Wrapper
      // Reference: "https://github.com/airbnb/enzyme/issues/252"
      let modal_element = document.getElementsByClassName('dialog-window');
      expect(modal_element.length).toBe(1);
      let modal = new ReactWrapper(modal_element[0], true)
      // expect(modal).toMatchSnapshot(); horrifying timezone bug
      expect(modal.find('.dialog-body')).toHaveLength(1);

      // check that the versions have loaded and are displayed in list
      expect(wrapper.state().versions).toEqual(mockVersions);  
      let versionsList = modal.find('.list-test-class');
      expect(versionsList).toHaveLength(5);
      
      // filter list to grab first item
      let firstVersion = versionsList.filterWhere(n => n.key() == '2017-07-10 17:57:58.324');
      expect(firstVersion).toHaveLength(1);
      firstVersion.simulate('click');

      expect(wrapper.state().versions.selected).toEqual('2017-07-10 17:57:58.324');  
      expect(wrapper.state().originalSelected).toEqual('2017-04-10 17:57:58.324'); 

      let okButton = modal.find('.test-ok-button');
      expect(okButton).toHaveLength(1);
      okButton.first().simulate('click');

      // state needs to update and modal needs to close
      setImmediate( () => {
        // expect(wrapper).toMatchSnapshot();
        expect(wrapper.state().modalOpen).toBe(false);
        expect(wrapper.state().originalSelected).toEqual('2017-07-10 17:57:58.324');  
        expect(api.getWfModuleVersions.mock.calls.length).toBe(1);
        expect(api.setWfModuleVersion.mock.calls.length).toBe(1);
        done();
      });
    });
  });

     // Pared-down version of first test
  it('Does not save selection when user hits Cancel', (done) => {

    expect(api.getWfModuleVersions.mock.calls.length).toBe(2);
    
    // expect(wrapper).toMatchSnapshot();
    
    modalLink.simulate('click');
    expect(wrapper.state().modalOpen).toBe(true);    

    setImmediate( () => {
      let modal_element = document.getElementsByClassName('dialog-window');
      // when document.get is invoked a second time, it has 2 elements
      expect(modal_element.length).toBe(2);
      // need to target the newly-created modal, [0] is the modal from previous test
      let modal = new ReactWrapper(modal_element[1], true);

      // check that the versions have loaded and are displayed in list
      expect(wrapper.state().versions).toEqual(mockVersions);  
      let versionsList = modal.find('.list-test-class');
      expect(versionsList).toHaveLength(5);
      let lastVersion = versionsList.filterWhere(n => n.key() == '2017-03-10 17:57:58.324');
      lastVersion.simulate('click');

      expect(wrapper.state().versions.selected).toEqual('2017-03-10 17:57:58.324');  
      expect(wrapper.state().originalSelected).toEqual('2017-04-10 17:57:58.324'); 

      let cancelButton = modal.find('.test-cancel-button');
      cancelButton.first().simulate('click');

      setImmediate( () => {
        // expect(wrapper).toMatchSnapshot();        
        expect(wrapper.state().modalOpen).toBe(false);        
        expect(wrapper.state().originalSelected).toEqual('2017-04-10 17:57:58.324');  
        // includes calls from previous test
        expect(api.getWfModuleVersions.mock.calls.length).toBe(2);
        expect(api.setWfModuleVersion.mock.calls.length).toBe(1);
        done();
      });
    });
  });

  it('Does not open modal when in read-only mode', (done) => {
    let readOnlywrapper = mount(<DataVersionSelect
      isReadOnly={true}
      wfModuleId={808}
      revision={202}
      api={api}
      timezoneOffset={localToUTC}          
    />);

    // This is "4" b/c of an extra API call from beforeEach()
    expect(api.getWfModuleVersions.mock.calls.length).toBe(4);

    let readOnlyModalLink = readOnlywrapper.find('div.open-modal')
    
    readOnlyModalLink.simulate('click');
    expect(readOnlywrapper.state().modalOpen).toBe(false);    

    done();
  });
    
});

