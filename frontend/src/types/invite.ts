export interface InviteSummary {
  inviteeEmail: string
  inviteeName: string | null
  accepted: boolean
}

export interface PendingInvite {
  worldId: string
}
