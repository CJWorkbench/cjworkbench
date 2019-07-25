import catalogEl from '../locales/el/messages.js'
import catalogEn from '../locales/en/messages.js'

const catalogs = { el: catalogEl, en: catalogEn };

//TODO: load catalogs dynamically
export default function fetchCatalog(language){
    //const catalog = await import(
      ///* webpackMode: "lazy", webpackChunkName: "i18n-[index]" */
      //`@lingui/loader!locales/${language}/messages.po`)
    return catalogs[language];
}
