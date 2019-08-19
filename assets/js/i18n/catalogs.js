import enCatalog from '../../locale/en/messages'
import elCatalog from '../../locale/el/messages'

const catalogs = {
  en: enCatalog,
  el: elCatalog
}

export default function fetchCatalog (language) {
  return catalogs[language]
}
