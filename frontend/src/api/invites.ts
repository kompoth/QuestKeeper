import type { InviteSummary } from '@/types/invite'
import { apiFetch } from '@/api/client'

interface InviteSummaryDto {
  invitee_email: string
  invitee_name: string | null
  accepted: boolean
}

function toInviteSummary (dto: InviteSummaryDto): InviteSummary {
  return { inviteeEmail: dto.invitee_email, inviteeName: dto.invitee_name, accepted: dto.accepted }
}

export async function listInvites (worldId: string): Promise<InviteSummary[]> {
  const dtos = await apiFetch<InviteSummaryDto[]>(`/worlds/${worldId}/invites`)
  return dtos.map(dto => toInviteSummary(dto))
}

export async function createInvite (worldId: string, inviteeEmail: string): Promise<InviteSummary> {
  const dto = await apiFetch<InviteSummaryDto>(`/worlds/${worldId}/invites`, {
    method: 'POST',
    body: { invitee_email: inviteeEmail },
  })
  return toInviteSummary(dto)
}

export async function expelInvitee (worldId: string, inviteeEmail: string): Promise<void> {
  await apiFetch<void>(`/worlds/${worldId}/invites?email=${encodeURIComponent(inviteeEmail)}`, { method: 'DELETE' })
}
