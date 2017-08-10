import React from 'react'
import UpdateFrequencySelect  from './UpdateFrequencySelect'
import { shallow } from 'enzyme'
import { okResponseMock } from './utils'

var today = new Date();
var day_before = today.setDate(today.getDate() - 2);

describe('UpdateFrequencySelect', () => {

  const updateSettings = {
    autoUpdateData: false, // start in Manual mode
    updateInterval: 5,
    updateUnits: 'minutes',
    lastUpdateCheck: day_before
  };
  const api = {
    setWfModuleUpdateSettings: okResponseMock()
  };
  var wrapper;  
  var freqNum;
  var freqUnit;
  var modalLink;
  var autoButton;

  beforeEach(() => wrapper = shallow(
    <UpdateFrequencySelect
      isReadOnly={false}
      updateSettings={updateSettings}
      wfModuleId={212}
      api={api} 
    />));
  beforeEach(() => freqUnit = wrapper.find('#updateFreqUnit'));
  beforeEach(() => freqNum = wrapper.find('#updateFreqNum'));  
  beforeEach(() => modalLink = wrapper.find('.test-button'));    
  beforeEach(() => autoButton = wrapper.find('.auto-button')); 


  it('Renders correctly when in Private mode and changes are confirmed with OK', (done) => {

    expect(wrapper).toMatchSnapshot();

    // check that Manual setting now in state
    expect(wrapper.state().liveSettings.manual).toBe(true);  
    // check value of Period input when first opened, as well as matching state value
    expect(freqNum.get(0).props.value).toBe(5);
    expect(wrapper.state().dialogSettings.period).toBe(5); 
    // check value of Unit input when first opened, as well as matching state value
    expect(freqUnit.get(0).props.value).toBe('minutes');
    expect(wrapper.state().dialogSettings.unit).toBe('minutes');   

    // simulate click to open modal
    expect(modalLink).toHaveLength(1);
    modalLink.first().simulate('click');

    setImmediate( () => {
      // Dialog should be open
      expect(wrapper).toMatchSnapshot();

      // Click the Auto setting
      expect(autoButton).toHaveLength(1);
      autoButton.first().simulate('click');
    
      // Change the Number setting    
      freqNum.simulate('change', {target: {value: 888}});
      // confirm state change
      expect(wrapper.state().dialogSettings.period).toBe(888);   
      
      // Change the Period setting
      freqUnit.simulate('change', {target: {value: 'days'}});   
      // confirm state change
      expect(wrapper.state().dialogSettings.unit).toBe('days');   
      
      // Click on OK button to confirm
      var okButton = wrapper.find('.test-ok-button');
      expect(okButton).toHaveLength(1);
      okButton.first().simulate('click');

      // Dialog should be closed, link should now say "auto"
      expect(wrapper).toMatchSnapshot();
      // check that API was called
      expect(api.setWfModuleUpdateSettings.mock.calls.length).toBe(1);
      // check that Auto setting now engaged
      expect(wrapper.state().liveSettings.manual).toBe(false);  
      // check that Period has changed
      expect(wrapper.state().liveSettings.period).toBe(888);  
      // check that Number has changed
      expect(wrapper.state().liveSettings.unit).toBe('days');              
      
      done();
    });
  });

  it('Does not save changed settings when user hits Cancel', (done) => {
    
    // simulate click to open modal
    modalLink.first().simulate('click');

    setImmediate( () => {
      // Click the Auto setting
      autoButton.first().simulate('click');
      // Change the Number setting    
      freqNum.simulate('change', {target: {value: 888}});
      // Change the Period setting
      freqUnit.simulate('change', {target: {value: 'days'}});   
      
      // Click the Cancel button to nullify changes
      var cancelButton = wrapper.find('.test-cancel-button');
      expect(cancelButton).toHaveLength(1);
      cancelButton.first().simulate('click');

      // Dialog should be closed, link should now say "auto"
      expect(wrapper).toMatchSnapshot();
      // check that API was not called (was called once already)
      expect(api.setWfModuleUpdateSettings.mock.calls.length).toBe(1);

      // check that still in Manual
      expect(wrapper.state().liveSettings.manual).toBe(true);  
      // check that Period has not changed
      expect(wrapper.state().liveSettings.period).toBe(5);  
      // check that Number has not changed
      expect(wrapper.state().liveSettings.unit).toBe('minutes');   
    
      done();
    });
  });

  it('Does not open modal when in read-only mode', (done) => {
    
    var readOnlyWrapper = shallow(
      <UpdateFrequencySelect
        isReadOnly={true}
        updateSettings={updateSettings}
        wfModuleId={212}
        api={api} 
    />);

    // confirm that modal is not open
    expect(readOnlyWrapper.state().modalOpen).toBe(false);   

    // click on modal
    modalLink.first().simulate('click');

    setImmediate( () => {
      // confirm that modal is not open
      expect(readOnlyWrapper.state().modalOpen).toBe(false);         
      done();
    });
  });
    
});


