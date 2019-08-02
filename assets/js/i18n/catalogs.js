import enCatalog from '../locales/en/messages.js';
import elCatalog from '../locales/el/messages.js';

const catalogs = {
    en: enCatalog,
    el: elCatalog
}

export default function fetchCatalog(language){
    return catalogs[language];
}

/*
 * This function loads the requested catalog dynamically.
 * At this time, it is not used, since we use a static approach.
 * 
 */
//async function fetchCatalog(language){
    //let catalog;
    //if (process.env.NODE_ENV !== 'production') {
        //// prettier-ignore
        //catalog = await import(
          ///* webpackMode: "lazy", webpackChunkName: "i18n-[index]" */
            //`@lingui/loader!../locales/${language}/messages.po`
        //)
    //} else {
        //// prettier-ignore
        //catalog = await import(
          ///* webpackMode: "lazy", webpackChunkName: "i18n-[index]" */
          //`../locales/${language}/messages.js`
        //)
    //}
    
    //return catalog;
//}
