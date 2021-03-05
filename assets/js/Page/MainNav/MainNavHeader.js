import PropTypes from 'prop-types'
import { t } from '@lingui/macro'
import MenuIcon from '../../../icons/menu.svg'

export default function MainNavHeader (props) {
  const { href, onToggleOpen } = props

  return (
    <header>
      <a href={href}>
        <img
          src={`${window.STATIC_URL}images/workbench-logo-with-white-text.svg`}
          alt={t({
            id: 'js.Page.MainNav.Header.brandName',
            message: 'Workbench'
          })}
        />
      </a>
      <button
        className='toggle-open'
        onClick={onToggleOpen}
        title={t({
          id: 'js.WfHamburgerMenu.toggle.hoverText',
          message: 'menu'
        })}
      >
        <MenuIcon />
      </button>
    </header>
  )
}
MainNavHeader.propTypes = {
  href: PropTypes.string, // or null
  onToggleOpen: PropTypes.func.isRequired
}
