import React from 'react'
import PropTypes from 'prop-types'
import { Trans, t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

const numberFormat = new Intl.NumberFormat()

const RefineBin = withI18n()(class RefineBin extends React.PureComponent {
  static propTypes = {
    i18n: PropTypes.shape({
      // i18n object injected by LinguiJS withI18n()
      _: PropTypes.func.isRequired
    }),
    index: PropTypes.number.isRequired,
    bin: PropTypes.shape({
      name: PropTypes.string.isRequired, // editable by user
      isSelected: PropTypes.bool.isRequired,
      count: PropTypes.number.isRequired,
      bucket: PropTypes.object.isRequired // { "str": Number(count), ... }
    }).isRequired,
    onChange: PropTypes.func.isRequired // onChange(index, { name?, isSelected? }) => undefined
  }

  get bucketList () {
    const bucket = this.props.bin.bucket
    const values = Object.keys(bucket).map(k => ({ value: k, count: bucket[k] }))
    values.sort((a, b) => b.count - a.count || a.value.localeCompare(b.value))
    return values
  }

  handleChangeIsSelected = (ev) => {
    this.props.onChange(this.props.index, {
      isSelected: ev.target.checked
    })
  }

  handleChangeName = (ev) => {
    this.props.onChange(this.props.index, {
      name: ev.target.value
    })
  }

  render () {
    const { index, i18n } = this.props
    const { name, isSelected, count } = this.props.bin
    const values = this.bucketList

    return (
      <>
        <tr className='bin'>
          <td rowSpan={values.length} className='is-selected'>
            <input type='checkbox' name={`selected-${index}`} checked={isSelected} onChange={this.handleChangeIsSelected} placeholder={i18n._(t('js.params.Custom.RefineBins.newValue.placeholder')`New Value`)} />
          </td>
          <td rowSpan={values.length} className='cluster-size'>{numberFormat.format(count)}</td>
          <td className='value'>{values[0].value}</td>
          <td className='count'>{numberFormat.format(values[0].count)}</td>
          <td className='new-value'>
            <div className='autosize-cluster-input'>
              <span className='autosize-cluster-text'>{name}</span>
              <textarea
                name={`value-${index}`}
                placeholder={i18n._(t('js.params.Custom.RefineBins.RefineBin.newValue.placeholder')`New Value`)}
                value={name}
                onChange={this.handleChangeName}
              />
            </div>
          </td>
        </tr>
        {values.slice(1).map(({ value, count }, i) => (
          <tr key={i} className='value'>
            <td className='value'>{value}</td>
            <td className='count'>{numberFormat.format(count)}</td>
          </tr>
        ))}
      </>
    )
  }
})

class RefineBins extends React.PureComponent {
  static propTypes = {
    bins: PropTypes.arrayOf(PropTypes.shape({
      name: PropTypes.string.isRequired, // editable by user
      isSelected: PropTypes.bool.isRequired,
      count: PropTypes.number.isRequired,
      bucket: PropTypes.object.isRequired // { "str": Number(count), ... }
    })),
    onChange: PropTypes.func.isRequired // func(newBins) => undefined
  }

  handleChange = (index, attrs) => {
    const oldBins = this.props.bins
    const newBins = oldBins.slice()
    newBins[index] = {
      ...oldBins[index],
      ...attrs
    }

    this.props.onChange(newBins)
  }

  render () {
    const { bins } = this.props

    if (bins.length === 0) {
      return (
        <div className='refine-bins'>
          <div className='no-bins'><Trans id='js.params.Custom.RefineBins.noClustersFound'>No clusters found. Try different settings.</Trans></div>
        </div>
      )
    }

    return (
      <div className='refine-bins'>
        <table>
          <thead>
            <tr>
              <th className='is-selected' />
              <th className='cluster-size'><Trans id='js.params.Custom.RefineBins.clusterSize.heading'>Cluster size</Trans></th>
              <th className='value'><Trans id='js.params.Custom.RefineBins.values.heading'>Values</Trans></th>
              <th className='count'><Trans id='js.params.Custom.RefineBins.countRows.heading'># rows</Trans></th>
              <th className='new-value'><Trans id='js.params.Custom.RefineBins.newValue.heading'>New value</Trans></th>
            </tr>
          </thead>
          <tbody>
            {bins.map((bin, i) => <RefineBin key={i} index={i} onChange={this.handleChange} bin={bin} />)}
          </tbody>
        </table>
      </div>
    )
  }
}

export default withI18n()(RefineBins)
