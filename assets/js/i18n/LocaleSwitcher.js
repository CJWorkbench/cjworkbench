import * as React from "react";
import { connect } from "react-redux";
import { withI18n } from "@lingui/react";
import { supportedLocales, setLocale } from './locales' 
import { Trans } from "@lingui/macro"

const LocaleSwitcher = ({ i18n }) => {
    if(window.i18n && window.i18n.showSwitcher){
        return (
          <select defaultValue={i18n.language}>
            {Object.keys(supportedLocales).map((locale) => (
              <option key={locale} onClick={() => setLocale(locale)} value={locale}>
                {i18n._(supportedLocales[locale])}
              </option>
            ))}
          </select>
        )
    } else {
        return null
    }
}

export default withI18n()(LocaleSwitcher);
