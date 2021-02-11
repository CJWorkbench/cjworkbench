import { PureComponent } from 'react'
import PropTypes from 'prop-types'
import memoize from 'memoize-one'
import { clusterByKey, clusterByKnn } from 'clustring'
import fingerprint from 'clustring/key/fingerprint'
import levenshtein from 'clustring/knn/levenshtein'
import { i18n } from '@lingui/core'
import { Trans, defineMessage } from '@lingui/macro'

const Algorithms = [
  {
    name: 'fingerprint',
    selectName: defineMessage({
      id: 'js.params.Custom.RefineClusterer.Algorithms.fingerprint.name',
      message: 'Fingerprint'
    }),
    description: defineMessage({
      id: 'js.params.Custom.RefineClusterer.Algorithms.fingerprint.description',
      message:
        'Group values by fingerprint. This method is effective when values are capitalized irregularly or if special characters are used in some and not others. For instance, "café" and "Cafe" both have the same fingerprint, "cafe".'
    }),
    defaultOptions: null,
    optionFields: null,
    buildClusterer: bucket => clusterByKey(bucket, fingerprint())
  },
  {
    name: 'levenshtein',
    selectName: defineMessage({
      comment:
        "This is not an editing action. It's a short description of how the levenstein algorithm works (i.e. it compares strings relative to the number of characters in which they differ, hence the term edit distance).",
      id: 'js.params.Custom.RefineClusterer.Algorithms.levenshtein.name',
      message: 'Edit distance'
    }),
    description: defineMessage({
      id: 'js.params.Custom.RefineClusterer.Algorithms.levenshtein.description',
      message:
        'Groups values if the number of characters added, edited or deleted to get from one value to the other is equal or inferior to ‘Maximum distance’. For instance, the distance between "Cafés" and "cafe" is 3.'
    }),
    defaultOptions: { maxDistance: 3 },
    optionFields: (handlers, options) => (
      <div className='form-group'>
        <label htmlFor='refine-clusterer-max-distance'>
          <Trans id='js.params.Custom.RefineClusterer.Algorithms.levenshtein.options.maxDistance.label'>
            Maximum distance
          </Trans>
        </label>
        <input
          className='form-control'
          id='refine-clusterer-max-distance'
          type='number'
          required
          name='maxDistance'
          size='2'
          value={options.maxDistance}
          min='1'
          max='999'
          placeholder='3'
          {...handlers}
        />
      </div>
    ),
    buildClusterer: (bucket, options) =>
      clusterByKnn(
        bucket,
        levenshtein(options.maxDistance),
        options.maxDistance
      )
  }
]

export default class RefineClusterer extends PureComponent {
  static propTypes = {
    bucket: PropTypes.object.isRequired, // { "str": Number(count), ... }
    onProgress: PropTypes.func.isRequired, // onProgress(0.2) => undefined (means 20% clustered)
    onComplete: PropTypes.func.isRequired // onComplete(bins) => undefined (bins is [ { name, count, bucket }, ... ])
  }

  // define _buildSortedBucket before using it in `state = { ... }`
  _buildSortedBucket = memoize(bucket => {
    // Turn Object into an Array, so we can sort it
    const arr = []
    for (const name in bucket) {
      arr.push({ name, count: bucket[name] })
    }

    // Sort the array
    arr.sort((a, b) => b.count - a.count || a.name.localeCompare(b.name))

    // Now rebuild an Object -- but with a sorted insertion order
    const ret = {}
    for (const item of arr) {
      ret[item.name] = item.count
    }
    return ret
  })

  state = {
    clusterer: this._startClusterer(
      Algorithms[0],
      Algorithms[0].defaultOptions
    ),
    algorithm: Algorithms[0],
    clustererOptions: Algorithms[0].defaultOptions
  }

  get sortedBucket () {
    return this._buildSortedBucket(this.props.bucket)
  }

  _startClusterer (algorithm, options) {
    const clusterer = algorithm.buildClusterer(this.sortedBucket, options)

    const reportProgressUntilDoneOrCanceled = () => {
      if (clusterer.canceled) return
      if (clusterer.progress >= 1) return

      this.props.onProgress(clusterer.progress)
      setTimeout(reportProgressUntilDoneOrCanceled, 20)
    }
    reportProgressUntilDoneOrCanceled()

    clusterer
      .cluster()
      .then(bins => {
        if (clusterer.canceled) {
          // the only way clusterer is canceled is if another is running --
          // meaning we don't want to hear from this one. Ignore the result.
          return
        }
        this.props.onComplete(bins)
      })
      .catch(_ => {
        // only error is "canceled". Ignore it.
      })
    return clusterer // so it can be canceled
  }

  componentWillUnmount () {
    this.state.clusterer.cancel() // it'll die asynchronously
  }

  /**
   * Kick off a new clusterer.
   */
  setClusterer (algorithm, clustererOptions) {
    // 1. Start a state transition, which is async.
    // (https://reactjs.org/docs/faq-state.html#when-is-setstate-asynchronous)
    this.setState(prevState => {
      if (prevState.clusterer !== null) {
        prevState.clusterer.cancel()
      }

      const clusterer = this._startClusterer(algorithm, clustererOptions)

      return {
        clusterer,
        algorithm,
        clustererOptions: clustererOptions
      }
    })
  }

  handleChangeAlgorithm = ev => {
    const name = ev.target.value
    const algorithm = Algorithms.find(a => a.name === name)
    this.setClusterer(algorithm, algorithm.defaultOptions || null)
  }

  onChangeOption = ev => {
    const { algorithm } = this.state

    const el = ev.target
    const name = el.name
    let value = el.value
    if (el.type === 'number') value = Number(value)

    const clustererOptions = {
      ...this.state.clustererOptions,
      [name]: value
    }

    this.setClusterer(algorithm, clustererOptions)
  }

  renderSelect = () => {
    const { algorithm } = this.state
    const options = Algorithms.map(({ name, selectName }) => (
      <option key={name} value={name}>
        {i18n._(selectName)}
      </option>
    ))

    return (
      <select
        name='algorithm'
        className='custom-select'
        value={algorithm.name}
        onChange={this.handleChangeAlgorithm}
      >
        {options}
      </select>
    )
  }

  renderOptions () {
    const { algorithm, clustererOptions } = this.state
    if (!algorithm.optionFields) return null

    const handlers = {
      onChange: this.onChangeOption
    }

    return (
      <div className='method-options form-inline'>
        {algorithm.optionFields(handlers, clustererOptions)}
      </div>
    )
  }

  render () {
    const { algorithm } = this.state

    return (
      <div className='refine-clusterer'>
        <legend>
          <Trans id='js.params.Custom.RefineClusterer.method'>Method</Trans>
        </legend>
        <div className='method'>
          <div className='method-select'>{this.renderSelect()}</div>
          <div className='method-form'>
            <div className='method-description'>
              {i18n._(algorithm.description)}
            </div>
            {this.renderOptions()}
          </div>
        </div>
      </div>
    )
  }
}
