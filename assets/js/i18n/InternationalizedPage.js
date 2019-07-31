import React from 'react'
import { Provider } from 'react-redux'
import { I18nLoader } from './I18nLoader'
import { currentLocale } from './locales'

export class InternationalizedPage extends React.Component {
  render () {
    if(this.props.store){
      return (
        <Provider store={this.props.store}>
          <I18nLoader language={currentLocale}>
            {this.props.children}
          </I18nLoader>
        </Provider>
      );
    } else {
      return (
          <I18nLoader language={currentLocale}>
            {this.props.children}
          </I18nLoader>
      );
    }
  }
}
