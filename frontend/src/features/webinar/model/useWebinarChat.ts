import { useCallback, useEffect, useRef, useState } from 'react';
import AgoraRTMDefault from 'agora-rtm-sdk';

const { RTM } = AgoraRTMDefault;

export interface ChatMessage {
  id: string;
  text: string;
  senderId: string;
  senderName: string;
  createdAt: number;
}

interface UseWebinarChatParams {
  appId: string;
  rtmToken: string;
  chatChannelName: string;
  uid: number;
  userName: string;
  onPeerLabel?: (rtcUid: number, label: string) => void;
}

interface UseWebinarChatReturn {
  messages: ChatMessage[];
  sendMessage: (text: string) => void;
  isConnected: boolean;
  debugLogs: string[];
}

// Publish own presence into the channel so peers can map uid → name.
// Retried PRESENCE_RETRIES times with PRESENCE_INTERVAL_MS delay to cover
// late-joining peers who weren't subscribed yet on first broadcast.
const PRESENCE_RETRIES = 3;
const PRESENCE_INTERVAL_MS = 8_000;

// Max reconnect attempts on connection drop before giving up.
const MAX_RECONNECT = 4;

async function withRetry<T>(
  fn: () => Promise<T>,
  retries: number,
  delayMs: number,
): Promise<T> {
  let attempt = 0;
  while (true) {
    try {
      return await fn();
    } catch (err) {
      if (++attempt > retries) throw err;
      await new Promise((r) => setTimeout(r, delayMs * attempt));
    }
  }
}

export function useWebinarChat({
  appId,
  rtmToken,
  chatChannelName,
  uid,
  userName,
  onPeerLabel,
}: UseWebinarChatParams): UseWebinarChatReturn {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isConnected, setIsConnected] = useState(false);

  const rtmRef = useRef<InstanceType<typeof RTM> | null>(null);
  // Always-current refs so closures inside the effect don't go stale.
  const onPeerLabelRef = useRef(onPeerLabel);
  onPeerLabelRef.current = onPeerLabel;
  const userNameRef = useRef(userName);
  userNameRef.current = userName;

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const appendLog = useCallback((message: string) => {
    if (!mountedRef.current) return;
    const time = new Date().toLocaleTimeString('ru-RU', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
    setDebugLogs((prev) => {
      const next = [...prev, `[${time}] ${message}`];
      return next.slice(-80);
    });
  }, []);

  const disabled = !rtmToken || !chatChannelName || !appId || !uid;

  useEffect(() => {
    if (disabled) {
      appendLog(
        `RTM disabled: appId=${Boolean(appId)} token=${Boolean(rtmToken)} channel=${Boolean(chatChannelName)} uid=${uid}`,
      );
      return;
    }

    let mounted = true;
    let reconnectCount = 0;
    const presenceTimers: ReturnType<typeof setTimeout>[] = [];
    // Track peers we've already replied to so we don't cause reply loops.
    const repliedTo = new Set<string>();

    const rtm = new RTM(appId, String(uid));
    rtmRef.current = rtm;
    appendLog(`RTM instance created for uid=${uid}`);

    // --- helpers ---

    const publishPresence = () => {
      if (!mounted) return;
      rtm
        .publish(
          chatChannelName,
          JSON.stringify({ type: 'presence', rtcUid: uid, userName: userNameRef.current }),
          { channelType: 'MESSAGE' },
        )
        .then(() => appendLog('presence sent'))
        .catch((err: unknown) => appendLog(`presence send failed: ${String(err)}`));
    };

    // Broadcast own presence, then repeat a few times for late joiners.
    const schedulePresenceBroadcast = () => {
      publishPresence();
      for (let i = 1; i <= PRESENCE_RETRIES; i++) {
        presenceTimers.push(
          setTimeout(() => {
            if (mounted) publishPresence();
          }, PRESENCE_INTERVAL_MS * i),
        );
      }
    };

    const clearPresenceTimers = () => {
      presenceTimers.forEach(clearTimeout);
      presenceTimers.length = 0;
    };

    // --- message handler ---

    const messageHandler = (event: { message: string | Uint8Array; publisher: string }) => {
      if (!mounted) return;
      // Ignore own echoes (RTM may echo back to sender in some configs).
      if (event.publisher === String(uid)) return;

      let payload: Record<string, unknown>;
      try {
        payload = JSON.parse(event.message as string) as Record<string, unknown>;
      } catch {
        return;
      }

      if (payload['type'] === 'presence') {
        const peerRtcUid = payload['rtcUid'];
        const peerName = payload['userName'];
        if (
          typeof peerRtcUid === 'number' &&
          typeof peerName === 'string' &&
          peerName
        ) {
          onPeerLabelRef.current?.(peerRtcUid, peerName);
          // Reply once so the newcomer learns our name too.
          if (!repliedTo.has(event.publisher)) {
            repliedTo.add(event.publisher);
            publishPresence();
          }
        }
        return;
      }

      const text = typeof payload['text'] === 'string' ? payload['text'] : '';
      const senderName =
        typeof payload['senderName'] === 'string' ? payload['senderName'] : event.publisher;
      const createdAt =
        typeof payload['createdAt'] === 'number' && Number.isFinite(payload['createdAt'])
          ? payload['createdAt']
          : Date.now();

      if (!text) return;

      setMessages((prev) => [
        ...prev,
        {
          id: `${Date.now()}-${Math.random()}`,
          text,
          senderId: event.publisher,
          senderName,
          createdAt,
        },
      ]);
    };

    // --- connect / reconnect ---

    const connect = async () => {
      try {
        await withRetry(() => rtm.login({ token: rtmToken }), 3, 1_000);
        await withRetry(() => rtm.subscribe(chatChannelName), 3, 1_000);
        if (!mounted) return;
        reconnectCount = 0;
        setIsConnected(true);
        schedulePresenceBroadcast();
      } catch (err) {
        console.error('[RTM] connect failed', err);
      }
    };

    const statusHandler = (event: { state: string }) => {
      if (!mounted) return;
      if (event.state === 'DISCONNECTED' || event.state === 'FAILED') {
        setIsConnected(false);
        clearPresenceTimers();
        if (reconnectCount < MAX_RECONNECT) {
          reconnectCount++;
          const delay = 1_000 * reconnectCount;
          console.warn(`[RTM] disconnected, reconnect attempt ${reconnectCount} in ${delay}ms`);
          setTimeout(() => {
            if (mounted) void connect();
          }, delay);
        } else {
          console.error('[RTM] max reconnect attempts reached');
        }
      } else if (event.state === 'CONNECTED') {
        setIsConnected(true);
      }
    };

    rtm.addEventListener('message', messageHandler);
    rtm.addEventListener('status', statusHandler as Parameters<typeof rtm.addEventListener<'status'>>[1]);

    void connect();

    return () => {
      mounted = false;
      clearPresenceTimers();
      rtmRef.current = null;
      rtm.removeEventListener('message', messageHandler);
      rtm.removeEventListener('status', statusHandler as Parameters<typeof rtm.addEventListener<'status'>>[1]);
      rtm.unsubscribe(chatChannelName).catch(() => {}).finally(() => rtm.logout().catch(() => {}));
      setIsConnected(false);
    };
  }, [appId, rtmToken, chatChannelName, uid, userName, disabled, appendLog]);

  const sendMessage = useCallback(
    (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || !rtmRef.current || !isConnected) return;

      const createdAt = Date.now();

      // Optimistic local append.
      setMessages((prev) => [
        ...prev,
        {
          id: `${createdAt}-own`,
          text: trimmed,
          senderId: String(uid),
          senderName: userNameRef.current,
          createdAt,
        },
      ]);

      rtmRef.current
        .publish(
          chatChannelName,
          JSON.stringify({ text: trimmed, senderName: userNameRef.current, createdAt }),
          { channelType: 'MESSAGE' },
        )
        .then(() => appendLog(`publish success: ${trimmed.slice(0, 40)}`))
        .catch((err: unknown) => {
          appendLog(`publish error: ${String(err)}`);
          console.error('[RTM] publish error', err);
        });
    },
    [chatChannelName, isConnected, uid],
  );

  return { messages, sendMessage, isConnected, debugLogs };
}
