export default async function fetchCatalog(language){
    let catalog;
    if (process.env.NODE_ENV !== 'production') {
        // prettier-ignore
        catalog = await import(
          /* webpackMode: "lazy", webpackChunkName: "i18n-[index]" */
            `@lingui/loader!../locales/${language}/messages.po`
        )
    } else {
        // prettier-ignore
        catalog = await import(
          /* webpackMode: "lazy", webpackChunkName: "i18n-[index]" */
          `../locales/${language}/messages.js`
        )
    }
    
    return catalog;
}
