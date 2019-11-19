/* globals gapi, google */
import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const MimeTypesString = [
  'application/vnd.google-apps.spreadsheet',
  'text/csv',
  'text/tab-separated-values',
  'application/vnd.ms-excel',
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
].join(',')

class PickerFactory {
  constructor () {
    this.picker = null
  }

  /**
   * Opens a singleton Picker, calling onPick and onCancel.
   *
   * Calls onPick({ id, name, url, mimeType, type }) or onCancel()
   * and then destroys the picker.
   *
   * Example values:
   *
   * id: `"0BS58NKO6eAjKchvRVkhpVYZFL1lSXRaa3VIbFczR0pZX4dJN"`
   * name: `"My filename"`
   * mimeType: `"application/vnd.google-apps.spreadsheet"`, `"text/csv"`
   * url: `"https://docs.google.com/.../edit?usp=drive_web"`
   *
   * If the singleton Picker is already open, this is a no-op.
   */
  open (accessToken, onPick, onCancel) {
    if (this.picker !== null) return

    const onEvent = (data) => {
      switch (data.action) {
        case 'loaded':
          break

        case 'picked': {
          const { id, name, url, mimeType } = data.docs[0]
          onPick({ id, name, url, mimeType })
          this.close()
          break
        }

        case 'cancel':
          onCancel()
          this.close()
          break

        default:
          console.log('Unhandled picker event', data)
      }
    }

    const soloView = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
      .setIncludeFolders(true)
      .setMimeTypes(MimeTypesString)

    const teamView = new google.picker.DocsView(google.picker.ViewId.SPREADSHEETS)
      .setIncludeFolders(true)
      .setEnableTeamDrives(true)
      .setMimeTypes(MimeTypesString)

    this.picker = new google.picker.PickerBuilder()
      .addView(soloView)
      .addView(teamView)
      .setOAuthToken(accessToken)
      .setCallback(onEvent)
      .enableFeature(google.picker.Feature.SUPPORT_DRIVES)
      .setSelectableMimeTypes(MimeTypesString)
      .build()

    this.picker.setVisible(true)
  }

  /**
   * Close the singleton picker, if it is open.
   */
  close () {
    if (this.picker !== null) {
      this.picker.dispose()
      this.picker = null
    }
  }
}

const FileInfo = withI18n()(function ({ id, name, url, i18n }) {
  if (!id) {
    return (
      <a className='file-info empty'><Trans id='js.params.Gdrivefile.FileInfo.chooseFile'>(please choose a file)</Trans></a>
    )
  } else {
    return (
      <a
        className='file-info'
        title={i18n._(
          /* i18n: {name} is the name of a file */
          t('js.params.Gdrivefile.FileInfo.openInGoogleSheets')`Open in Google Sheets: ${name}`
        )}
        target='_blank'
        rel='noopener noreferrer'
        href={url}
      >{name}
      </a>
    )
  }
})

let googleApiLoadedPromise = null
/**
 * Load Google APIs globally (if they haven't been loaded already); return
 * a Promise[PickerFactory] that will resolve once the Google APIs are loaded.
 *
 * This returns a new PickerFactory each call, but it only loads the global
 * `google` and `gapi` variables once.
 */
async function loadDefaultPickerFactory () {
  if (googleApiLoadedPromise === null) {
    googleApiLoadedPromise = new Promise((resolve, reject) => {
      const callbackName = `Gdrivefile_onload_${String(Math.random()).slice(2, 10)}`
      window[callbackName] = function () {
        delete window[callbackName]
        gapi.load('picker', function () {
          resolve()
        })
      }

      const script = document.createElement('script')
      script.async = true
      script.defer = true
      script.src = `https://apis.google.com/js/api.js?onload=${callbackName}`

      document.querySelector('head').appendChild(script)
    })
  }

  await googleApiLoadedPromise
  return new PickerFactory()
}

export default class Gdrivefile extends React.PureComponent {
  static propTypes = {
    createOauthAccessToken: PropTypes.func.isRequired, // func() => Promise[str or null]
    isReadOnly: PropTypes.bool.isRequired,
    secretMetadata: PropTypes.object, // when this changes, call createOauthAccessToken
    value: PropTypes.shape({
      id: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired,
      url: PropTypes.string.isRequired
    }), // may be empty/null
    onChange: PropTypes.func.isRequired, // func({ id, name, url }) => undefined
    loadPickerFactory: PropTypes.func // func() => Promise[PickerFactory], default uses Google APIs
  }

  state = {
    pickerFactory: null,
    loadingAccessToken: false,
    unauthenticated: false // true after the server says we're unauthenticated
  }

  /**
   * Return a Promise of an access token or null ("unauthenticated").
   *
   * Manages state: loadingAccessToken and unauthenticated.
   *
   * Access tokens are time-sensitive, so we can't just cache the return value:
   * we need to refresh from time to time. Simplest is to load on demand.
   *
   * Each call returns a new token. Only the most-recent returned token is
   * valid.
   */
  fetchAccessToken () {
    const secretMetadata = this.props.secretMetadata
    const secretName = secretMetadata.name

    if (!secretMetadata) {
      this.setState({
        loadingAccessToken: false,
        unauthenticated: true
      })
      return Promise.resolve(null)
    }

    this.setState({
      loadingAccessToken: true,
      unauthenticated: false
    })

    return this.props.createOauthAccessToken()
      .then(accessTokenOrNull => {
        if (secretName !== (this.props.secretMetadata && this.props.secretMetadata.name)) {
          // avoid race: another request is happening
          return null
        }
        if (this._isUnmounted) {
          // avoid race: we're closed
          return null
        }

        this.setState({
          loadingAccessToken: false,
          unauthenticated: accessTokenOrNull === null
        })
        return accessTokenOrNull
      })
  }

  loadPickerFactory () {
    const loadPickerFactory = this.props.loadPickerFactory || loadDefaultPickerFactory
    loadPickerFactory().then(pf => {
      if (this._isUnmounted) return
      this.setState({ pickerFactory: pf })
    })
  }

  componentDidMount () {
    this.loadPickerFactory()
  }

  componentWillUnmount () {
    if (this.state.pickerFactory) {
      this.state.pickerFactory.close()
      // we leak window.gapi, but that's probably fine
    }

    this._isUnmounted = true
  }

  openPicker () {
    const { pickerFactory } = this.state
    this.fetchAccessToken()
      .then(accessTokenOrNull => {
        if (accessTokenOrNull) {
          pickerFactory.open(accessTokenOrNull, this.handlePick, this.onCancel)
        }
        // otherwise, we've set this.state.unauthenticated
      })
  }

  handleClickOpenPicker = () => this.openPicker()

  handlePick = (data) => {
    this.props.onChange(data)
    this.props.onSubmit()
  }

  onCancel = () => {
    // do nothing
  }

  render () {
    const { pickerFactory, loadingAccessToken, unauthenticated } = this.state
    const { value, secretMetadata, isReadOnly } = this.props

    if (!isReadOnly) {
      if (loadingAccessToken || !pickerFactory) {
        return (
          <a className='file-info'><p className='loading'><Trans id='js.params.Gdrivefile.status.loading'>Loading...</Trans></p></a>
        )
      } else if (unauthenticated) {
        return (
          <a className='file-info'><p className='sign-in-error'><Trans id='js.params.Gdrivefile.status.failureRecconect'>failure: please reconnect</Trans></p></a>
        )
      } else if (!secretMetadata) {
        return (
          <a className='file-info'><p className='not-signed-in'><Trans id='js.params.Gdrivefile.status.pleaseSignin'>(please sign in)</Trans></p></a>
        )
      }
    }

    return (
      <>
        <FileInfo
          {...(value || {})}
        />
        {!isReadOnly ? (
          <button
            type='button'
            className='change-file'
            onClick={this.handleClickOpenPicker}
          >
            {value ? <Trans id='js.params.Gdrivefile.change.button'>Change</Trans> : <Trans id='js.params.Gdrivefile.choose.button'>Choose</Trans>}
          </button>
        ) : null}
      </>
    )
  }
}
