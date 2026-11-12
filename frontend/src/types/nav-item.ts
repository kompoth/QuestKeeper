export interface NavItem {
  id: string
  title: string
  to?: string
  icon: string
  children?: NavItem[]
}
