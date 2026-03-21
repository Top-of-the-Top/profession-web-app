import { connectNotificationSSE, disconnectNotificationSSE } from "./notification.sse";

let isInitialized = false;

export function bootstrapNotifications() {
  if (isInitialized) {
    return;
  }

  connectNotificationSSE();
  isInitialized = true;
}

export function shutdownNotifications() {
  disconnectNotificationSSE();
  isInitialized = false;
}

export function restartNotifications() {
  disconnectNotificationSSE();
  connectNotificationSSE();
}