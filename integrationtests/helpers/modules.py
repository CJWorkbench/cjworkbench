from integrationtests.browser import Browser

def import_workbench_module(browser: Browser, slug: str) -> None:
    """Import a module by clicking through the browser.
    
    Assumes there's a context menu with an "Import Module" modal.
    """
    browser.click_button('menu', wait=True) # wait for page to load
    browser.click_button('Import Module')
    browser.fill_in('url', f'http://git-server/{slug}.git', wait=True)
    browser.click_button('Import')
    browser.wait_for_element('.import-github-success', wait=True)
    browser.click_button('OK')
