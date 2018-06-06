import React from 'react'
import PropTypes from 'prop-types'

export default class GoogleFileSelect extends React.PureComponent {
  static propTypes = {
    api: PropTypes.shape({
      currentGoogleClientAccessToken: PropTypes.func.isRequired,
    }).isRequired,
    userCreds: PropTypes.number, // TODO document what it is
    fileMetadataJson: PropTypes.string, // may be empty/null
    onChangeJson: PropTypes.func.isRequired, // func("{ id, name }") => undefined
  }

  constructor(props) {
    super(props)

    this.picker = null

    this.state = {
      gapiLoaded: false,
      accessToken: null,
      loadingAccessToken: false,
      userCredsThatLedToAccessToken: null,
    }
  }

  refreshAccessToken() {
    const userCreds = this.props.userCreds

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
    this.callbackName = `GoogleFileSelect_onload_${String(Math.random()).slice(2, 10)}`
    window[this.callbackName] = this.onGapiLoad

    const script = document.createElement('script')
    script.async = true
    script.defer = true
    script.src = `https://apis.google.com/js/api.js?onload=${this.callbackName}`

    document.querySelector('head').appendChild(script)
    this.script = script

    this.refreshAccessToken()
  }

  componentWillUnmount() {
    delete window[this.callbackName]
    document.querySelector('head').removeChild(this.script)
    // we leak window.gapi, but that's probably fine

    if (this.picker) {
      this.picker.dispose()
      this.picker = null
    }
  }

  componentDidUpdate() {
    if (this.props.userCreds !== this.state.userCredsThatLedToAccessToken) {
      this.refreshAccessToken()
    }
  }

  onGapiLoad = () => {
    gapi.load('picker', this.onPickerApiLoad)
  }

  onPickerApiLoad = () => {
    this.setState({
      gapiLoaded: true,
    })
  }

  openPicker = () => {
    if (this.picker) return

    const accessToken = this.state.accessToken
    const view = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
      .setIncludeFolders(true)

    this.picker = new google.picker.PickerBuilder()
      .addView(view)
      .setOrigin(window.location.origin)
      .setOAuthToken(accessToken)
      .setCallback(this.onPick)
      .build()

    this.picker.setVisible(true)
  }

  onPick = (data) => {
    switch (data.action) {
      case 'loaded':
        break

      case 'picked':
        const doc = data.docs[0]
        this.props.onChangeJson(JSON.stringify({
          id: doc.id,
          name: doc.name,
        }))

        this.picker.dispose()
        this.picker = null
        return

      case 'cancel':
        this.picker.dispose()
        this.picker = null
        return

      default:
        console.log(data)
    }
  }

  render() {
    const { gapiLoaded, accessToken, accessTokenLoading } = this.state
    const { fileMetadataJson } = this.props

    const fileMetadata = fileMetadataJson ? JSON.parse(fileMetadataJson) : null
    const fileId = fileMetadata ? (fileMetadata.id || null) : null
    const fileName = fileMetadata ? (fileMetadata.name || null) : null

    let button
    if (accessTokenLoading || !gapiLoaded) {
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
          {fileName || '(no file chosen)'}
        </div>
        {button}
      </div>
    )
  }
}
