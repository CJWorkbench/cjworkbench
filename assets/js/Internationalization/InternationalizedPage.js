import React from 'react'
import { Provider } from 'react-redux'
import { I18nLoader } from './I18nLoader'

export default class InternationalizedPage extends React.Component {
  render () {
      return (
        <Provider store={this.props.store}>
          <I18nLoader>
            {this.props.children}
          </I18nLoader>
        </Provider>
      );
  }
}
