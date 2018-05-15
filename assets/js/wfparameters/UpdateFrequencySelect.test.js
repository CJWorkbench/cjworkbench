import React from 'react'
import UpdateFrequencySelect  from './UpdateFrequencySelect'
import { shallow } from 'enzyme'
import { okResponseMock } from '../test-utils'


describe('UpdateFrequencySelect', () => {

  var today = new Date();
  var day_before = today.setDate(today.getDate() - 2);
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
  beforeEach(() => modalLink = wrapper.find('.test-modal-button'));
  beforeEach(() => autoButton = wrapper.find('.auto-button'));


  it('Renders correctly when in Private mode and changes are confirmed with OK', (done) => {

    expect(wrapper).toMatchSnapshot();
    expect(wrapper.state().liveSettings.manual).toBe(true);
    expect(freqNum.get(0).props.value).toBe(5);
    expect(wrapper.state().dialogSettings.period).toBe(5);
    expect(freqUnit.get(0).props.value).toBe('minutes');
    expect(wrapper.state().dialogSettings.unit).toBe('minutes');

    expect(modalLink).toHaveLength(1);
    modalLink.first().simulate('click');

    // Dialog should be open
    expect(wrapper).toMatchSnapshot();

    expect(autoButton).toHaveLength(1);
    autoButton.first().simulate('click');

    freqNum.simulate('change', {target: {value: 888}});
    expect(wrapper.state().dialogSettings.period).toBe(888);

    freqUnit.simulate('change', {target: {value: 'days'}});
    expect(wrapper.state().dialogSettings.unit).toBe('days');

    var okButton = wrapper.find('.test-ok-button');
    expect(okButton).toHaveLength(1);
    okButton.first().simulate('click');

    // Dialog should be closed, link should now say "auto"
    expect(wrapper).toMatchSnapshot();
    expect(api.setWfModuleUpdateSettings.mock.calls.length).toBe(1);

    // '.toBe()' requires strict equality, and will fail
    expect(wrapper.state().liveSettings).toEqual({
      manual: false,
      period: 888,
      unit: 'days'
    });

    done();
  });

  it('Does not save changed settings when user hits Cancel', (done) => {

    modalLink.first().simulate('click');

    autoButton.first().simulate('click');
    freqNum.simulate('change', {target: {value: 888}});
    freqUnit.simulate('change', {target: {value: 'days'}});

    var cancelButton = wrapper.find('.test-cancel-button');
    expect(cancelButton).toHaveLength(1);
    cancelButton.first().simulate('click');

    // Dialog should be closed, link should now say "manual"
    expect(wrapper).toMatchSnapshot();
    // check that API was not called (was called once already in previous test)
    expect(api.setWfModuleUpdateSettings.mock.calls.length).toBe(1);

    // check that Live settings have NOT changed
    // '.toBe()' requires strict equality, and will fail
    expect(wrapper.state().liveSettings).toEqual({
      manual: true,
      period: 5,
      unit: 'minutes'
    });
    done();
  });

  it('Does not open modal when in read-only mode', (done) => {
    var readOnlyWrapper = shallow(
      <UpdateFrequencySelect
        isReadOnly={true}
        updateSettings={updateSettings}
        wfModuleId={212}
        api={api}
    />);
    expect(readOnlyWrapper.state().modalOpen).toBe(false);
    modalLink.first().simulate('click');
    expect(readOnlyWrapper.state().modalOpen).toBe(false);
    done();
  });

});
