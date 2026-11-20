export interface NavAction {
  title: string
  icon: string
  color?: string
  onClick: () => void
}

export interface NavItem {
  id: string
  title: string
  to?: string
  icon: string
  children?: NavItem[]
  actions?: NavAction[]
  onClick?: () => void
}
