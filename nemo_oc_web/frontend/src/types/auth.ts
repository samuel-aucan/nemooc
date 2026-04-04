export interface AuthUser {
  id: number
  username: string
  nombre_completo: string
  rol: string
  activo: boolean
  last_login_at: string
  must_reset_password: boolean
}

export interface BootstrapStatus {
  requires_setup: boolean
}

export interface AuthCreateUserInput {
  username: string
  nombre_completo: string
  password: string
  password_confirm: string
  rol: string
}

export interface AuthUpdateUserInput {
  nombre_completo: string
  rol: string
  activo: boolean
}

export interface ResetAccessToken {
  reset_token: string
  expires_at: string
}
