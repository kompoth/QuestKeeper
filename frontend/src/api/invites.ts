import type { InviteSummary, PendingInvite } from '@/types/invite'
import { apiFetch } from '@/api/client'

interface InviteSummaryDto {
  invitee_email: string
  invitee_name: string | null
  accepted: boolean
}

interface PendingInviteDto {
  world_id: string
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

export async function listMyPendingInvites (): Promise<PendingInvite[]> {
  const dtos = await apiFetch<PendingInviteDto[]>('/invites')
  return dtos.map(dto => ({ worldId: dto.world_id }))
}

export async function acceptInvite (worldId: string): Promise<void> {
  await apiFetch<void>(`/invites/${worldId}/accept`, { method: 'POST' })
}
