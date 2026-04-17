// LocalStorage con namespace para evitar colisiones entre múltiples instancias
const PREFIX = "nemooc_"

export const storage = {
  getItem: (key: string): string | null => localStorage.getItem(`${PREFIX}${key}`),
  setItem: (key: string, value: string): void => localStorage.setItem(`${PREFIX}${key}`, value),
  removeItem: (key: string): void => localStorage.removeItem(`${PREFIX}${key}`),
  clear: (): void => {
    const keys = Object.keys(localStorage)
    keys.forEach(k => {
      if (k.startsWith(PREFIX)) localStorage.removeItem(k)
    })
  },
}
