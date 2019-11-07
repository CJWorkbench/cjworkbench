import React from 'react'
import PropTypes from 'prop-types'
import ReactSelect from './common/react-select'
import { MaybeLabel } from './util'
import { t } from '@lingui/macro'
import { withI18n } from '@lingui/react'

export class MultitabParam extends React.PureComponent {
  static propTypes = {
    isReadOnly: PropTypes.bool.isRequired,
    onChange: PropTypes.func.isRequired, // func(['tab-1', 'tab-2']) => undefined
    name: PropTypes.string.isRequired, // <input name=...>
    fieldId: PropTypes.string.isRequired,
    label: PropTypes.string.isRequired,
    value: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // ['tab-slug', ...] or []
    upstreamValue: PropTypes.arrayOf(PropTypes.string.isRequired).isRequired, // ['tab-slug', ...] or []
    placeholder: PropTypes.string, // default 'Select Tab'
    tabs: PropTypes.arrayOf(PropTypes.shape({
      slug: PropTypes.string.isRequired,
      name: PropTypes.string.isRequired
    }).isRequired).isRequired,
    currentTab: PropTypes.string.isRequired // 'tab-slug'
  }

  render () {
    const { name, value, upstreamValue, placeholder, isReadOnly, fieldId, label, tabs, currentTab, onChange, i18n } = this.props

    const tabOptions = tabs
      .filter(({ slug }) => slug !== currentTab)
      .map(({ slug, name }) => ({ label: name, value: slug }))

    return (
      <>
        <MaybeLabel fieldId={fieldId} label={label} />
        <ReactSelect
          name={name}
          key={upstreamValue.join('|')}
          inputId={fieldId}
          options={tabOptions}
          value={value}
          onChange={onChange}
          isReadOnly={isReadOnly}
          placeholder={placeholder || i18n._(t('js.params.MultitabParam.selectTabs.placeholder')`Select Tabs`)}
          isMulti
        />
      </>
    )
  }
}

export default withI18n()(MultitabParam)
