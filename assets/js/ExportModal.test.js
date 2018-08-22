import React from 'react'
import { mount } from 'enzyme'
import ExportModal from "./ExportModal";


describe('ExportModal', () => {

  let wrapper;
  let onClose;

  beforeEach(() => {

    onClose = jest.fn();

    // mount not shallow as we are looking for components down in the tree, e.g. the input fields inside FormGroup
    wrapper = mount(
      <ExportModal
        wfModuleId={415}
        open={true}
        onClose={onClose}
        className="menu-test-class"
      />
    )
  });

  afterEach(() => wrapper.unmount());

  it('should match snapshot', () => {
    expect(wrapper).toMatchSnapshot()
  });

  it('closes', () => {
    const closeButton = wrapper.find('button.test-done-button');
    expect(closeButton).toHaveLength(1);
    closeButton.simulate('click');
    expect(onClose).toHaveBeenCalled();
  });

  it('should render download links', () => {
    const csvField = wrapper.find('input.test-csv-field');
    expect(csvField.length).toBe(1);
    expect(csvField.props().value).toBe("http://localhost/public/moduledata/live/415.csv");

    const jsonField =wrapper.find('input.test-json-field');
    expect(jsonField.length).toBe(1);
    expect(jsonField.props().value).toBe("http://localhost/public/moduledata/live/415.json");
  });

  it('renders copy to clipboard buttons', () => {
    const csvCopy = wrapper.find('div.test-csv-copy');
    expect(csvCopy).toHaveLength(1);

    const jsonCopy = wrapper.find('div.test-json-copy');
    expect(jsonCopy).toHaveLength(1);

  });

  it('Renders modal links which can be downloaded', () => {
    const csvDownload = wrapper.find('a.test-csv-download');
    expect(csvDownload.prop('href')).toBe("http://localhost/public/moduledata/live/415.csv");

    const jsonDownload = wrapper.find('a.test-json-download');
    expect(jsonDownload.prop('href')).toBe("http://localhost/public/moduledata/live/415.json");
  });
});
