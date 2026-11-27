<template>
  <h1 class="text-h5 mb-4">Users</h1>

  <div class="d-flex align-center justify-space-between mb-4">
    <v-text-field
      v-model="search"
      clearable
      density="compact"
      hide-details
      label="Search by name or email"
      prepend-inner-icon="mdi-magnify"
      style="max-width: 320px;"
      variant="outlined"
    />

    <v-btn color="primary" prepend-icon="mdi-plus" variant="flat" @click="openAddUserDialog">Add user</v-btn>
  </div>

  <v-data-table-server
    :headers="headers"
    :items="users"
    :items-length="total"
    :items-per-page="pageSize"
    :loading="loading"
    :search="search"
    @update:options="handleOptionsUpdate"
  >
    <template #item.user="{ item }">
      <MemberItem :user="item" />
    </template>

    <template #item.role="{ item }">
      <v-select
        density="compact"
        :disabled="item.id === currentUser?.id"
        hide-details
        :items="roles"
        :model-value="item.role"
        style="max-width: 160px;"
        variant="outlined"
        @update:model-value="role => handleRoleChange(item, role)"
      />
    </template>

    <template #item.status="{ item }">
      <v-chip :color="statusColor(item.status)" size="small">{{ item.status }}</v-chip>
    </template>

    <template #item.joinedAt="{ item }">
      {{ formatDate(item.joinedAt) }}
    </template>

    <template #item.actions="{ item }">
      <v-btn class="mr-2" size="small" variant="tonal" @click="handleResetPassword(item)">Reset password</v-btn>

      <v-btn
        :color="item.status === 'banned' ? undefined : 'error'"
        :disabled="item.id === currentUser?.id || item.status === 'pending'"
        size="small"
        variant="tonal"
        @click="handleStatusToggle(item)"
      >
        {{ item.status === 'banned' ? 'Unban' : 'Ban' }}
      </v-btn>
    </template>
  </v-data-table-server>

  <v-dialog v-model="addUserDialog" max-width="480">
    <v-card title="Add user">
      <v-card-text>
        <v-text-field v-model="newUsername" autofocus label="Name" variant="outlined" />
        <v-text-field v-model="newUserEmail" label="Email" type="email" variant="outlined" />
        <v-select v-model="newUserRole" :items="roles" label="Role" variant="outlined" />

        <p class="text-body-2 text-medium-emphasis">
          A set-password email will be sent to this address. No password is entered here.
        </p>
      </v-card-text>

      <v-card-actions>
        <v-spacer />
        <v-btn variant="text" @click="addUserDialog = false">Cancel</v-btn>

        <v-btn
          color="primary"
          :disabled="!canCreateUser"
          :loading="creatingUser"
          variant="flat"
          @click="handleCreateUser"
        >
          Create
        </v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>

  <v-snackbar v-model="snackbar" :color="snackbarColor">{{ snackbarText }}</v-snackbar>
</template>

<script lang="ts" setup>
  import type { User, UserRole, UserStatus } from '@/types/user'
  import { computed, ref } from 'vue'
  import { changeUserRole, changeUserStatus, createUser, listUsers, triggerPasswordReset } from '@/api/admin'
  import { ApiError } from '@/api/client'
  import MemberItem from '@/components/MemberItem.vue'
  import { useAuth } from '@/composables/useAuth'
  import { useSnackbar } from '@/composables/useSnackbar'
  import { formatDate } from '@/utils/date'

  const { currentUser } = useAuth()

  const pageSize = 20

  const headers = [
    { title: 'User', key: 'user', sortable: false },
    { title: 'Joined', key: 'joinedAt' },
    { title: 'Role', key: 'role' },
    { title: 'Status', key: 'status', sortable: false },
    { title: 'Actions', key: 'actions', sortable: false },
  ]

  const roles: UserRole[] = ['admin', 'warden', 'member']

  const users = ref<User[]>([])
  const total = ref(0)
  const loading = ref(false)
  const search = ref('')
  const lastOptions = ref<{ page: number, itemsPerPage: number, search?: string }>()

  const addUserDialog = ref(false)
  const newUsername = ref('')
  const newUserEmail = ref('')
  const newUserRole = ref<UserRole>('member')
  const creatingUser = ref(false)

  const canCreateUser = computed(() => newUsername.value.trim() !== '' && newUserEmail.value.trim() !== '')

  const { snackbar, snackbarText, snackbarColor, notify } = useSnackbar()

  function statusColor (status: UserStatus) {
    if (status === 'banned') return 'error'
    if (status === 'pending') return 'warning'
    return 'success'
  }

  async function fetchPage (options: { page: number, itemsPerPage: number, search?: string }) {
    lastOptions.value = options
    loading.value = true
    try {
      const offset = (options.page - 1) * options.itemsPerPage
      const result = await listUsers(offset, options.itemsPerPage, options.search)
      users.value = result.users
      total.value = result.total
    } finally {
      loading.value = false
    }
  }

  async function handleOptionsUpdate (options: { page: number, itemsPerPage: number, search?: string }) {
    await fetchPage(options)
  }

  async function handleRoleChange (user: User, role: UserRole) {
    try {
      await changeUserRole(user.id, role)
      user.role = role
      notify(`${user.name}'s role changed to ${role}`, 'success')
    } catch {
      notify('Failed to change role', 'error')
    }
  }

  async function handleResetPassword (user: User) {
    try {
      await triggerPasswordReset(user.id)
      notify(`Password reset email sent to ${user.email}`, 'success')
    } catch (error) {
      notify(
        error instanceof ApiError && error.status === 503 ? error.detail : 'Failed to send password reset email',
        'error',
      )
    }
  }

  async function handleStatusToggle (user: User) {
    const nextStatus = user.status === 'banned' ? 'active' : 'banned'
    try {
      await changeUserStatus(user.id, nextStatus)
      user.status = nextStatus
      notify(`${user.name} ${nextStatus === 'banned' ? 'banned' : 'unbanned'}`, 'success')
    } catch {
      notify('Failed to change status', 'error')
    }
  }

  function openAddUserDialog () {
    newUsername.value = ''
    newUserEmail.value = ''
    newUserRole.value = 'member'
    addUserDialog.value = true
  }

  async function handleCreateUser () {
    creatingUser.value = true
    try {
      await createUser(newUsername.value.trim(), newUserEmail.value.trim(), newUserRole.value)
      addUserDialog.value = false
      notify(`Account created. Set-password email sent to ${newUserEmail.value.trim()}`, 'success')
      if (lastOptions.value) {
        await fetchPage(lastOptions.value)
      }
    } catch (error) {
      let message = 'Failed to create user'
      if (error instanceof ApiError && error.status === 409) {
        message = 'That email is already registered'
      } else if (error instanceof ApiError && error.status === 503) {
        message = error.detail
      }
      notify(message, 'error')
    } finally {
      creatingUser.value = false
    }
  }
</script>
