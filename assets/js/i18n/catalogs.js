import enCatalog from '../../locales/en/messages'
import elCatalog from '../../locales/el/messages'

const catalogs = {
  en: enCatalog,
  el: elCatalog
}

export default function fetchCatalog (language) {
  return catalogs[language]
}
