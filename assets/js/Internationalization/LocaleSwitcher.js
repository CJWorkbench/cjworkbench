import * as React from "react";
import { connect } from "react-redux";
import { withI18n } from "@lingui/react";
import { supportedLocales } from './locales' 
import { Trans } from "@lingui/macro"
import { setLocaleAction } from "./actions"

const LocaleSwitcher = ({ i18n, setLocale }) => {
    return (
      <select defaultValue={i18n.language}>
        {Object.keys(supportedLocales).map((locale) => (
          <option key={locale} onClick={() => setLocale(locale)} value={locale}>
            {i18n._(supportedLocales[locale])}
          </option>
        ))}
      </select>
    )
}

export default connect(null, {setLocale: setLocaleAction})(withI18n()(LocaleSwitcher));
