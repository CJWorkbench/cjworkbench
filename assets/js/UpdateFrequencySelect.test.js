import React from 'react'
import UpdateFrequencySelect  from './UpdateFrequencySelect'
import { shallow } from 'enzyme'

const Utils = require('./utils');

var today = new Date();
var day_before = today.setDate(today.getDate() - 2);

it('UpdateFrequencySelect renders correctly', () => {

  var updateSettings = {
    autoUpdateData: false, // start in Manual mode
    updateInterval: 5,
    updateUnits: 'minutes',
    lastUpdateCheck: day_before
  };

  var apiCall = jest.fn().mockImplementation(()=>
    Promise.resolve(Utils.mockResponse(200, null, null))
  );
  var api = {
    setWfModuleUpdateSettings: apiCall
  };

  const wrapper = shallow(
    <UpdateFrequencySelect
      updateSettings={updateSettings}
      wfModuleId={212}
      api={api} 
  />);
  expect(wrapper).toMatchSnapshot();

  // check Interval input when first opened:
  var freqPeriod = wrapper.find('#updateFreqPeriod');
  // basic test
  expect(freqPeriod).toHaveLength(1);
  // TODO: access the value from freqPeriod, compare against updateSettings 
  
  // simulate click to open modal
  var modalLink = wrapper.find('.test-button');
  expect(modalLink).toHaveLength(1);
  modalLink.first().simulate('click');

  setImmediate( () => {
    // Dialog should be open
    expect(wrapper).toMatchSnapshot();

    // Click the Auto setting
    var autoButton = wrapper.find('.test-button-gray');
    expect(autoButton).toHaveLength(1);
    autoButton.first().simulate('click');

    // TODO: simulate selections of Interval and Units before hitting "OK" button (tricky)
    
    // Click on OK button to confirm
    var okButton = wrapper.find('.test-ok-button');
    expect(okButton).toHaveLength(1);
    okButton.first().simulate('click');

    // Do we need more layers of SetImmediate after every click? (Going with "No" for now)
    setImmediate( () => {
      // Dialog should be closed, link should now say "auto"
      expect(wrapper).toMatchSnapshot();

      // check on state values after changes
      expect(wrapper.state().liveSettings.manual).toBe(false);  

      // check that API was called
      expect(apiCall.mock.calls.length).toBe(1);

      done();
    });
  });
});


