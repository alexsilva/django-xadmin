import React from 'react'
import app from 'xadmin'

const C = args => {
  if(typeof args == 'string') {
    return app.get('components')[args]
  } else {
    const { is, ...props } = args
    const Component = C(is)
    if(Component) 
      return <Component {...props} />
    else
      return <div>Component {is} not found.</div>
  }
}

C.lazy = is => props => C({ is, ...props })

const Main = C.lazy('Main')
const App = C.lazy('App')
const Dashboard = C.lazy('Dashboard')
const Page = C.lazy('Page')
const Icon = C.lazy('Icon')
const Loading = C.lazy('Loading')

const Dropdown = C.lazy('Dropdown')
const Menu = C.lazy('Menu')
Menu.SubMenu = C.lazy('Menu.SubMenu')
Menu.Item = C.lazy('Menu.Item')
/** UI Components */
const Badge = C.lazy('Badge')
const Card = C.lazy('Card')
const Modal = C.lazy('Modal')
const Button = C.lazy('Button')
const Popover = C.lazy('Popover')
const Tooltip = C.lazy('Tooltip')
const Table = C.lazy('Table')
const Tabs = C.lazy('Tabs')
Tabs.Item = C.lazy('Tabs.Item')
const Empty = C.lazy('Empty')
const List = C.lazy('List')
List.Item = C.lazy('List.Item')
const Alert = C.lazy('Alert')

export default {
  name: 'xadmin.ui',
  items: {
    components: { type: 'map' }
  },
  routers: {
    '@' : {
      path: '/',
      component: Main,
      indexRoute: {
        onEnter: (_, replace) => replace({ pathname: '/app/' })
      }
    },
    '/' : {
      path: 'app/',
      component: App,
      indexRoute: {
        onEnter: (_, replace) => replace({ pathname: '/app/dashboard' })
      }
    },
    '/app/': {
      path: 'dashboard',
      component: Dashboard
    }
  }
}

export {
  C,
  Page, Icon, Loading,
  Main, Dashboard, App,
  Dropdown, Menu, Badge, Card,
  Modal, Button, Popover, Tooltip, 
  Table, Tabs, Empty, List, Alert
}