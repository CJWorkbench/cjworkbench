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
          const { id, name, url } = data.docs[0]
          onPick({ id, name, url })
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
async function loadDefaultPickerFactory() {
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
      paramOauthGenerateAccessToken: PropTypes.func.isRequired,
    }).isRequired,
    googleCredentialsParamId: PropTypes.number.isRequired,
    googleCredentialsSecretName: PropTypes.string, // when this changes, call api.paramOauthGenerateAccessToken
    fileMetadataJson: PropTypes.string, // may be empty/null
    onChangeJson: PropTypes.func.isRequired, // func("{ id, name, url }") => undefined
    loadPickerFactory: PropTypes.func, // func() => Promise[PickerFactory], default uses Google APIs
  }

  constructor(props) {
    super(props)

    this.state = {
      pickerFactory: null,
      accessToken: null,
      loadingAccessToken: false,
      secretNameThatLedToAccessToken: null,
    }
  }

  refreshAccessToken() {
    const googleCredentialsSecretName = this.props.googleCredentialsSecretName

    if (googleCredentialsSecretName === null) {
      this.setState({
        accessToken: null,
        secretNameThatLedToAccessToken: null,
        loadingAccessToken: false,
      })
      return
    }

    this.setState({
      accessToken: null,
      secretNameThatLedToAccessToken: googleCredentialsSecretName,
      loadingAccessToken: true,
    })

    this.props.api.paramOauthGenerateAccessToken(this.props.googleCredentialsParamId)
      .then(access_token_or_null => {
        if (googleCredentialsSecretName === this.state.secretNameThatLedToAccessToken) { // avoid race
          this.setState({
            accessToken: access_token_or_null,
            loadingAccessToken: false,
          })
        }
      })
  }

  loadPickerFactory() {
    const loadPickerFactory = this.props.loadPickerFactory || loadDefaultPickerFactory
    loadPickerFactory().then(pf => {
      if (this._isMounted) {
        this.setState({ pickerFactory: pf })
      }
      // otherwise, no prob: next mount, the promise will return quickly
    })
  }

  componentDidMount() {
    this.loadPickerFactory()
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
        secretNameThatLedToAccessToken: null,
      })
    }

    this._isMounted = false
  }

  componentDidUpdate() {
    if (this.props.googleCredentialsSecretName !== this.state.secretNameThatLedToAccessToken) {
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

    const defaultFileName = '(no file chosen)'
    const fileMetadata = fileMetadataJson ? JSON.parse(fileMetadataJson) : null
    const fileId = fileMetadata ? (fileMetadata.id || null) : null
    const fileName = fileMetadata ? (fileMetadata.name || defaultFileName) : defaultFileName
    const fileUrl = fileMetadata ? (fileMetadata.url || null) : null

    let button
    if (loadingAccessToken || !pickerFactory) {
      button = (
        <p className="loading">Loading...</p>
      )
    } else if (!accessToken) {
      if (this.props.googleCredentialsSecretName) {
        button = (
          <p className="sign-in-error">failure: please reconnect</p>
        )
      } else {
        button = (
          <p className="not-signed-in">(not signed in)</p>
        )
      }
    } else {
      button = (
        <button
          className="change-file action-link"
          onClick={this.openPicker}
          >{ fileId ? 'Change' : 'Choose' }</button>
      )
    }

    return (
      <div className="google-file-select">
        <a className="file-info" title={`Edit in Google Sheets: ${fileName}`} target="_blank" href={fileUrl}>{fileName}</a>
        {button}
      </div>
    )
  }
}
