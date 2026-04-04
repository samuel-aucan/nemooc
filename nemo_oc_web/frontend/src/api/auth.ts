import api from './client'
import type { AuthCreateUserInput, AuthUpdateUserInput, AuthUser, BootstrapStatus, ResetAccessToken } from '../types/auth'

export function getCurrentUser() {
  return api.get<AuthUser>('/auth/me').then((r) => r.data)
}

export function getBootstrapStatus() {
  return api.get<BootstrapStatus>('/auth/bootstrap-status').then((r) => r.data)
}

export function login(username: string, password: string) {
  return api.post<AuthUser>('/auth/login', { username, password }).then((r) => r.data)
}

export function completeReset(username: string, token: string, password: string, passwordConfirm: string) {
  return api
    .post<AuthUser>('/auth/complete-reset', {
      username,
      token,
      password,
      password_confirm: passwordConfirm,
    })
    .then((r) => r.data)
}

export function bootstrapAdmin(username: string, nombreCompleto: string, password: string, passwordConfirm: string) {
  return api
    .post<AuthUser>('/auth/bootstrap', {
      username,
      nombre_completo: nombreCompleto,
      password,
      password_confirm: passwordConfirm,
    })
    .then((r) => r.data)
}

export function logout() {
  return api.post<{ ok: boolean }>('/auth/logout').then((r) => r.data)
}

export function getUsers() {
  return api.get<AuthUser[]>('/auth/users').then((r) => r.data)
}

export function createUser(payload: AuthCreateUserInput) {
  return api.post<AuthUser>('/auth/users', payload).then((r) => r.data)
}

export function updateUser(userId: number, payload: AuthUpdateUserInput) {
  return api.put<AuthUser>(`/auth/users/${userId}`, payload).then((r) => r.data)
}

export function resetUserPassword(userId: number, password: string, passwordConfirm: string) {
  return api
    .put<AuthUser>(`/auth/users/${userId}/password`, {
      password,
      password_confirm: passwordConfirm,
    })
    .then((r) => r.data)
}

export function restartUserAccess(userId: number) {
  return api.post<ResetAccessToken>(`/auth/users/${userId}/reset-access`).then((r) => r.data)
}
