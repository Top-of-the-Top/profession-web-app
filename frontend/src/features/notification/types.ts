

export type ConnectionStatus =
  | 'idle'
  | 'connecting'
  | 'connected'
  | 'error'
  | 'disconnected'

export type Notification = {
	id: number,
	title: string,
	message: string,
	created_at: Date
}

export type NotificationState = {
	notifications: Array<Notification>,
	unreadCount: number,

	status: ConnectionStatus
  error: string | null

	setStatus: (status: ConnectionStatus) => void
  setError: (message: string | null) => void

	setInitial: (notifications: Notification[]) => void
  addNotification: (notification: Notification) => void
	removeNotification: (notificationId: number) => void
  markRead: () => void
  clear: () => void
} 