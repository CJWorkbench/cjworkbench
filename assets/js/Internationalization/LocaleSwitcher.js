import * as React from "react";
import { withI18n } from "@lingui/react";
import { supportedLocales } from './locales' 
import { Trans } from "@lingui/macro"

const LocaleSwitcher = ({ i18n }) => (
  <select defaultValue={i18n.language}>
    {Object.keys(supportedLocales).map((locale) => (
      <option key={locale} onClick={() => i18n.activate(locale)} value={locale}>
        {i18n._(supportedLocales[locale])}
      </option>
    ))}
  </select>
);

export default withI18n()(LocaleSwitcher);
