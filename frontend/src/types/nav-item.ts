export interface NavAction {
  title: string
  icon: string
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
