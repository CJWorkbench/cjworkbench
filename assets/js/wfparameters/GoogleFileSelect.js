import React from 'react'
import PropTypes from 'prop-types'


class PickerFactory {
  constructor() {
    this.picker = null
  }

  /**
   * Opens a singleton Picker, calling onPick and onCancel.
   *
   * Calls onPick({ id, name }) or onCancel() and then destroys the picker.
   *
   * If the singleton Picker is already open, this is a no-op.
   */
  open(accessToken, onPick, onCancel) {
    if (this.picker !== null) return

    const onEvent = (data) => {
      switch (data.action) {
        case 'loaded':
          break

        case 'picked':
          const { id, name } = data.docs[0]
          onPick({ id, name })
          this.close()
          break

        case 'cancel':
          onCancel()
          this.close()
          break

        default:
          console.log('Unhandled picker event', data)
      }
    }

    const view = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
      .setIncludeFolders(true)

    this.picker = new google.picker.PickerBuilder()
      .addView(view)
      .setOAuthToken(accessToken)
      .setCallback(onEvent)
      .build()

    this.picker.setVisible(true)
  }

  /**
   * Close the singleton picker, if it is open.
   */
  close() {
    if (this.picker !== null) {
      this.picker.dispose()
      this.picker = null
    }
  }
}


let googleApiLoadedPromise = null
/**
 * Load Google APIs globally (if they haven't been loaded already); return
 * a Promise[PickerFactory] that will resolve once the Google APIs are loaded.
 *
 * This returns a new PickerFactory each call, but it only loads the global
 * `google` and `gapi` variables once.
 */
async function getPickerFactory() {
  if (googleApiLoadedPromise === null) {
    googleApiLoadedPromise = new Promise((resolve, reject) => {
      const callbackName = `GoogleFileSelect_onload_${String(Math.random()).slice(2, 10)}`
      window[callbackName] = function() {
        delete window[callbackName]
        gapi.load('picker', function() {
          resolve()
        })
      }

      const script = document.createElement('script')
      script.async = true
      script.defer = true
      script.src = `https://apis.google.com/js/api.js?onload=${callbackName}`

      document.querySelector('head').appendChild(script)
      this.script = script
    })
  }

  await googleApiLoadedPromise
  return new PickerFactory()
}


export default class GoogleFileSelect extends React.PureComponent {
  static propTypes = {
    api: PropTypes.shape({
      currentGoogleClientAccessToken: PropTypes.func.isRequired,
    }).isRequired,
    userCreds: PropTypes.number, // TODO document what it is
    fileMetadataJson: PropTypes.string, // may be empty/null
    onChangeJson: PropTypes.func.isRequired, // func("{ id, name }") => undefined
    loadPickerFactory: PropTypes.func, // func() => Promise[PickerFactory], default uses Google APIs
  }

  constructor(props) {
    super(props)

    this.state = {
      pickerFactory: null,
      accessToken: null,
      loadingAccessToken: false,
      userCredsThatLedToAccessToken: null,
    }
  }

  refreshAccessToken() {
    const userCreds = this.props.userCreds

    if (userCreds === null) {
      this.setState({
        accessToken: null,
        userCredsThatLedToAccessToken: null,
        loadingAccessToken: false,
      })
      return
    }

    this.setState({
      accessToken: null,
      userCredsThatLedToAccessToken: userCreds,
      loadingAccessToken: true,
    })

    this.props.api.currentGoogleClientAccessToken()
      .then(json => json && json.access_token || null)
      .catch(err => {
        console.warn(err)
        return null
      })
      .then(access_token_or_null => {
        if (userCreds === this.state.userCredsThatLedToAccessToken) { // avoid race
          this.setState({
            accessToken: access_token_or_null,
            loadingAccessToken: false,
          })
        }
      })
  }

  componentDidMount() {
    this.props.loadPickerFactory().then(pf => {
      if (this._isMounted) {
        this.setState({ pickerFactory: pf })
      }
      // otherwise, no prb -- next time we mount, the promise will return
      // quickly
    })

    this.refreshAccessToken()

    this._isMounted = true
  }

  componentWillUnmount() {
    if (this.state.pickerFactory) {
      this.state.pickerFactory.close()
      // we leak window.gapi, but that's probably fine
    }

    if (this.state.loadingAccessToken) {
      // We can't set state when unmounted, and there's an API request
      // floating about. Ignore the response when it arrives.
      this.setState({
        loadingAccessToken: false,
        accessToken: null,
        userCredsThatLedToAccessToken: null,
      })
    }

    this._isMounted = false
  }

  componentDidUpdate() {
    if (this.props.userCreds !== this.state.userCredsThatLedToAccessToken) {
      this.refreshAccessToken()
    }
  }

  openPicker = () => {
    const { pickerFactory, accessToken } = this.state
    pickerFactory.open(accessToken, this.onPick, this.onCancel)
  }

  onPick = (data) => {
    this.props.onChangeJson(JSON.stringify(data))
  }

  onCancel = () => {
    // do nothing
  }

  render() {
    const { pickerFactory, accessToken, loadingAccessToken } = this.state
    const { fileMetadataJson } = this.props

    const fileMetadata = fileMetadataJson ? JSON.parse(fileMetadataJson) : null
    const fileId = fileMetadata ? (fileMetadata.id || null) : null
    const fileName = fileMetadata ? (fileMetadata.name || null) : null

    let button
    if (loadingAccessToken || !pickerFactory) {
      button = (
        <p className="loading">Loading...</p>
      )
    } else if (!accessToken) {
      button = (
        <p className="not-signed-in">
          To {fileId ? 'choose another file' : 'choose a file'}, you must connect
        </p>
      )
    } else {
      button = (
        <button
          className="button-orange action-button"
          onClick={this.openPicker}
          >{ fileId ? 'Change' : 'Choose' }</button>
      )
    }

    return (
      <div className="google-file-select">
        <div className="file-info">
          {fileId ? fileName : '(no file chosen)'}
        </div>
        {button}
      </div>
    )
  }
}
