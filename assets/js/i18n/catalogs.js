import enCatalog from '../../locale/en/messages.po'
import elCatalog from '../../locale/el/messages.po'

const catalogs = {
  en: enCatalog,
  el: elCatalog
}

export default function fetchCatalog (language) {
  return catalogs[language]
}
