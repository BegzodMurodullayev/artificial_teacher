// Telegram WebApp global types declaration

interface TelegramWebApp {
  initData:    string
  initDataUnsafe: {
    user?: {
      id:         number
      first_name: string
      last_name?: string
      username?:  string
      language_code?: string
    }
    chat_instance?: string
    auth_date:  number
    hash:       string
  }
  colorScheme: 'light' | 'dark'
  themeParams: Record<string, string>
  isExpanded:  boolean
  viewportHeight: number
  viewportStableHeight: number

  ready():   void
  expand():  void
  close():   void
  enableClosingConfirmation(): void
  disableClosingConfirmation(): void

  HapticFeedback: {
    impactOccurred(style: 'light' | 'medium' | 'heavy' | 'rigid' | 'soft'): void
    notificationOccurred(type: 'success' | 'warning' | 'error'): void
    selectionChanged(): void
  }

  MainButton: {
    text: string
    color: string
    isVisible: boolean
    isActive: boolean
    setText(text: string): void
    show(): void
    hide(): void
    onClick(fn: () => void): void
    offClick(fn: () => void): void
  }

  BackButton: {
    isVisible: boolean
    show(): void
    hide(): void
    onClick(fn: () => void): void
  }

  onEvent(eventType: string, handler: () => void): void
  offEvent(eventType: string, handler: () => void): void
  sendData(data: string): void
  openLink(url: string): void
  showPopup(params: {
    title?: string
    message: string
    buttons?: Array<{ id?: string; type?: string; text?: string }>
  }, callback?: (buttonId: string) => void): void
  showAlert(message: string, callback?: () => void): void
  showConfirm(message: string, callback?: (ok: boolean) => void): void
}

declare global {
  interface Window {
    Telegram?: {
      WebApp: TelegramWebApp
    }
  }
}

export {}
