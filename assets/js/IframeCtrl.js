import { store } from './workflow-reducer';

class IframeCtrl {

  constructor(ref) {
    this._refIframe = ref;
  }

  getIframe() {
    if (typeof this._refIframe !== 'undefined') {
      return this._refIframe;
    }
    return false;
  }

  _setSrc(src) {
    var iframeRef = this.getIframe();
    if (iframeRef) {
      iframeRef.src = src;
    }
    return this;
  }

  _getSrc() {
    var iframeRef = this.getIframe();
    if (iframeRef) {
      return iframeRef.src;
    }
  }

  src(src) {
    if (src) {
      return this._setSrc(src);
    } else {
      return this._getSrc();
    }
  }

  location() {
    var iframeRef = this.getIframe();
    if (iframeRef) {
      return iframeRef.contentWindow.location;
    }
    return false;
  }

  postMessage(message, loc) {
    var remoteWindow;
    if (this.getIframe()) {
      remoteWindow = this.getIframe().contentWindow;
      remoteWindow.postMessage(message, loc); // The module will know what its output url is supposed to be
    }
    return this;
  }
}

export default IframeCtrl;
