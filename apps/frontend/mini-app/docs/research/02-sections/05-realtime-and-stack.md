# Секции 8-9: Real-time данные и Рекомендуемый стек (расширенное исследование)

> Глубокое исследование real-time паттернов, управляемых WebSocket-сервисов, AI-стриминга,
> мониторинга производительности и полных архитектурных рекомендаций для enterprise Next.js (App Router) 2025-2026.

---

## Содержание

- [Секции 8-9: Real-time данные и Рекомендуемый стек (расширенное исследование)](#секции-8-9-real-time-данные-и-рекомендуемый-стек-расширенное-исследование)
  - [Содержание](#содержание)
  - [8. Real-time данные](#8-real-time-данные)
    - [8.1 Сравнение подходов](#81-сравнение-подходов)
    - [8.2 SSE с автоматическим переподключением и типами событий](#82-sse-с-автоматическим-переподключением-и-типами-событий)
      - [Сервер: Route Handler с именованными событиями и Last-Event-ID](#сервер-route-handler-с-именованными-событиями-и-last-event-id)
      - [Клиент: хук с автоматическим переподключением и диспетчеризацией типов](#клиент-хук-с-автоматическим-переподключением-и-диспетчеризацией-типов)
    - [8.3 WebSocket-интеграция (Socket.IO + Next.js)](#83-websocket-интеграция-socketio--nextjs)
      - [Архитектура: отдельный WebSocket-сервер + Next.js клиент](#архитектура-отдельный-websocket-сервер--nextjs-клиент)
      - [Socket.IO сервер (отдельный процесс)](#socketio-сервер-отдельный-процесс)
      - [Next.js клиент: реюзабельный хук](#nextjs-клиент-реюзабельный-хук)
    - [8.4 PartyKit для совместной работы](#84-partykit-для-совместной-работы)
      - [PartyKit сервер: комнаты с presence](#partykit-сервер-комнаты-с-presence)
      - [Next.js клиент: хук для PartyKit](#nextjs-клиент-хук-для-partykit)
    - [8.5 AI-стриминг (Vercel AI SDK + ReadableStream)](#85-ai-стриминг-vercel-ai-sdk--readablestream)
      - [Server Action для AI-стриминга](#server-action-для-ai-стриминга)
      - [Клиент: useChat для ChatGPT-style интерфейса](#клиент-usechat-для-chatgpt-style-интерфейса)
      - [Низкоуровневый стриминг через Route Handler (без AI SDK)](#низкоуровневый-стриминг-через-route-handler-без-ai-sdk)
    - [8.6 Управляемые real-time сервисы: Pusher vs Ably vs Soketi](#86-управляемые-real-time-сервисы-pusher-vs-ably-vs-soketi)
      - [Когда что выбирать](#когда-что-выбирать)
      - [Пример: Pusher в Next.js](#пример-pusher-в-nextjs)
    - [8.7 Оптимизация поллинга (адаптивный, exponential backoff)](#87-оптимизация-поллинга-адаптивный-exponential-backoff)
      - [Адаптивный поллинг с TanStack Query](#адаптивный-поллинг-с-tanstack-query)
      - [Стратегия: выбор интервала поллинга](#стратегия-выбор-интервала-поллинга)
    - [8.8 Optimistic Updates для real-time ощущения](#88-optimistic-updates-для-real-time-ощущения)
      - [useOptimistic + Server Action](#useoptimistic--server-action)
      - [TanStack Query optimistic mutation](#tanstack-query-optimistic-mutation)
    - [8.9 Стоимостной анализ real-time сервисов](#89-стоимостной-анализ-real-time-сервисов)
    - [8.10 Пути миграции между технологиями](#810-пути-миграции-между-технологиями)
  - [9. Рекомендуемый стек](#9-рекомендуемый-стек)
    - [9.1 Дерево решений по state management](#91-дерево-решений-по-state-management)
    - [Краткая таблица решений](#краткая-таблица-решений)
    - [9.2 Полная enterprise-архитектура](#92-полная-enterprise-архитектура)
    - [9.3 Финальный стек с альтернативами](#93-финальный-стек-с-альтернативами)
    - [9.4 Мониторинг производительности](#94-мониторинг-производительности)
      - [OpenTelemetry: инструментация Next.js](#opentelemetry-инструментация-nextjs)
      - [Метрики, которые необходимо отслеживать](#метрики-которые-необходимо-отслеживать)
      - [Кастомные метрики TanStack Query](#кастомные-метрики-tanstack-query)
      - [Web Vitals: клиентский сбор](#web-vitals-клиентский-сбор)
    - [9.5 Архитектура проекта](#95-архитектура-проекта)
  - [Источники](#источники)

---

## 8. Real-time данные

### 8.1 Сравнение подходов

| Подход                       | Направление             | Latency            | Сложность | Serverless (Vercel) | Масштабирование        | Стоимость      |
| ---------------------------- | ----------------------- | ------------------ | --------- | ------------------- | ---------------------- | -------------- |
| **Polling (TanStack Query)** | Pull                    | Средняя (интервал) | Низкая    | Да                  | Линейно с клиентами    | Низкая         |
| **Adaptive Polling**         | Pull (умный)            | Средняя-Низкая     | Средняя   | Да                  | Хорошее                | Низкая         |
| **Long Polling**             | Pull (задержанный)      | Средняя            | Средняя   | Частично            | Среднее                | Низкая         |
| **SSE (Server-Sent Events)** | Push (server -> client) | Низкая             | Средняя   | Да (Route Handlers) | Хорошее                | Низкая         |
| **WebSocket (Socket.IO)**    | Bidirectional           | Очень низкая       | Высокая   | Нет (свой сервер)   | Требует инфраструктуру | Средняя        |
| **PartyKit**                 | Bidirectional (edge)    | Очень низкая       | Средняя   | Да (свой edge)      | Автоматическое         | Средняя        |
| **Managed (Pusher/Ably)**    | Bidirectional           | Низкая             | Низкая    | Да                  | Автоматическое         | Высокая        |
| **AI Streaming (AI SDK)**    | Push (stream)           | Реальное время     | Средняя   | Да                  | По модели              | Зависит от LLM |

### 8.2 SSE с автоматическим переподключением и типами событий

#### Сервер: Route Handler с именованными событиями и Last-Event-ID

```typescript
// app/api/events/route.ts
export const dynamic = 'force-dynamic';
export const runtime = 'nodejs';

interface SSEEvent {
  id: string;
  type: 'notification' | 'order-update' | 'price-change' | 'heartbeat';
  data: unknown;
}

export async function GET(request: Request) {
  const encoder = new TextEncoder();

  // Поддержка возобновления потока: клиент отправляет Last-Event-ID
  const lastEventId = request.headers.get('Last-Event-ID');

  const stream = new ReadableStream({
    async start(controller) {
      let eventCounter = parseInt(lastEventId ?? '0', 10);

      const send = (event: Omit<SSEEvent, 'id'>) => {
        eventCounter++;
        const id = String(eventCounter);
        // SSE-формат: id, event (тип), data, retry (мс до переподключения)
        const message = [
          `id: ${id}`,
          `event: ${event.type}`,
          `data: ${JSON.stringify(event.data)}`,
          `retry: 3000`, // клиент переподключится через 3с
          '',
          '', // пустая строка = конец сообщения
        ].join('\n');
        controller.enqueue(encoder.encode(message));
      };

      // Heartbeat каждые 30с для поддержания соединения (прокси/балансеры)
      const heartbeat = setInterval(() => {
        send({ type: 'heartbeat', data: { ts: Date.now() } });
      }, 30_000);

      // Подписка на источник данных (Redis Pub/Sub, DB change stream и т.д.)
      const unsubscribe = await subscribeToEvents(
        (event) => send(event),
        { afterId: lastEventId }, // отправляем пропущенные события
      );

      // Очистка при отключении клиента
      request.signal.addEventListener('abort', () => {
        clearInterval(heartbeat);
        unsubscribe();
        controller.close();
      });
    },
  });

  // ВАЖНО: Response возвращается немедленно, стриминг идёт асинхронно
  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-store, no-transform',
      Connection: 'keep-alive',
      'X-Accel-Buffering': 'no', // отключить буферизацию Nginx
    },
  });
}
```

#### Клиент: хук с автоматическим переподключением и диспетчеризацией типов

```typescript
// hooks/use-sse.ts
'use client';

import { useEffect, useCallback, useRef, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface UseSSEOptions {
  url: string;
  onNotification?: (data: unknown) => void;
  onOrderUpdate?: (data: unknown) => void;
  onPriceChange?: (data: unknown) => void;
  maxRetries?: number;
  enabled?: boolean;
}

interface SSEState {
  status: 'connecting' | 'connected' | 'disconnected' | 'error';
  retryCount: number;
  lastEventId: string | null;
}

export function useSSE({
  url,
  onNotification,
  onOrderUpdate,
  onPriceChange,
  maxRetries = 10,
  enabled = true,
}: UseSSEOptions) {
  const queryClient = useQueryClient();
  const sourceRef = useRef<EventSource | null>(null);
  const retryCountRef = useRef(0);
  const [state, setState] = useState<SSEState>({
    status: 'disconnected',
    retryCount: 0,
    lastEventId: null,
  });

  const connect = useCallback(() => {
    if (!enabled) return;

    // EventSource автоматически отправляет Last-Event-ID при переподключении
    const source = new EventSource(url);
    sourceRef.current = source;
    setState((s) => ({ ...s, status: 'connecting' }));

    source.addEventListener('open', () => {
      retryCountRef.current = 0;
      setState((s) => ({ ...s, status: 'connected', retryCount: 0 }));
    });

    // Именованные события — каждый тип обрабатывается отдельно
    source.addEventListener('notification', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onNotification?.(data);
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
    });

    source.addEventListener('order-update', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onOrderUpdate?.(data);
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    });

    source.addEventListener('price-change', (e) => {
      const data = JSON.parse(e.data);
      setState((s) => ({ ...s, lastEventId: e.lastEventId }));
      onPriceChange?.(data);
      queryClient.setQueryData(['prices'], (old: unknown[]) => (old ? [...old, data] : [data]));
    });

    source.addEventListener('heartbeat', () => {
      // Heartbeat — ничего не делаем, просто подтверждаем живое соединение
    });

    source.addEventListener('error', () => {
      source.close();
      // Exponential backoff с jitter для переподключения
      if (retryCountRef.current < maxRetries) {
        const baseDelay = Math.min(1000 * 2 ** retryCountRef.current, 30_000);
        const jitter = Math.random() * 1000;
        const delay = baseDelay + jitter;
        retryCountRef.current++;
        setState((s) => ({
          ...s,
          status: 'error',
          retryCount: retryCountRef.current,
        }));
        setTimeout(connect, delay);
      } else {
        setState((s) => ({ ...s, status: 'disconnected' }));
      }
    });
  }, [url, enabled, maxRetries, queryClient, onNotification, onOrderUpdate, onPriceChange]);

  useEffect(() => {
    connect();
    return () => sourceRef.current?.close();
  }, [connect]);

  return state;
}
```

**Ключевые принципы SSE в Next.js:**

1. `export const dynamic = 'force-dynamic'` — отключает кэширование Route Handler.
2. `Response` возвращается **немедленно** — стриминг идёт через `ReadableStream` асинхронно.
3. `X-Accel-Buffering: no` — критически важно для Nginx-прокси, иначе события буферизуются.
4. `retry: 3000` — указывает браузеру интервал автоматического переподключения.
5. `Last-Event-ID` — позволяет серверу отправить пропущенные события после reconnect.
6. Heartbeat каждые 30с предотвращает таймаут прокси/балансеров.

---

### 8.3 WebSocket-интеграция (Socket.IO + Next.js)

**Ограничение:** Vercel не поддерживает WebSocket-соединения. Socket.IO требует отдельного сервера
(Node.js, Docker, Railway, Fly.io и т.д.).

#### Архитектура: отдельный WebSocket-сервер + Next.js клиент

```
┌─────────────────┐    HTTP/SSR     ┌─────────────────┐
│   Next.js App   │◄──────────────►│   Vercel / CDN   │
│   (App Router)  │                │                  │
└────────┬────────┘                └──────────────────┘
         │
         │  WebSocket (wss://)
         ▼
┌─────────────────┐    Redis Pub/Sub  ┌──────────────┐
│  Socket.IO      │◄────────────────►│  Redis        │
│  Server         │                  │  (Upstash/    │
│  (Railway/Fly)  │                  │   Valkey)     │
└─────────────────┘                  └──────────────┘
```

#### Socket.IO сервер (отдельный процесс)

```typescript
// ws-server/index.ts
import { createServer } from 'http';
import { Server } from 'socket.io';
import { createAdapter } from '@socket.io/redis-adapter';
import { createClient } from 'redis';

const httpServer = createServer();
const io = new Server(httpServer, {
  cors: {
    origin: process.env.NEXT_PUBLIC_APP_URL,
    methods: ['GET', 'POST'],
    credentials: true,
  },
  // Fallback на long-polling если WebSocket недоступен
  transports: ['websocket', 'polling'],
  pingTimeout: 60_000,
  pingInterval: 25_000,
});

// Redis adapter для горизонтального масштабирования
const pubClient = createClient({ url: process.env.REDIS_URL });
const subClient = pubClient.duplicate();
await Promise.all([pubClient.connect(), subClient.connect()]);
io.adapter(createAdapter(pubClient, subClient));

// Middleware: аутентификация
io.use(async (socket, next) => {
  const token = socket.handshake.auth.token;
  try {
    const user = await verifyToken(token);
    socket.data.user = user;
    next();
  } catch {
    next(new Error('Authentication failed'));
  }
});

// Пространства имён (namespaces) для разделения логики
const chatNs = io.of('/chat');
const dashNs = io.of('/dashboard');

chatNs.on('connection', (socket) => {
  const userId = socket.data.user.id;

  socket.on('join-room', (roomId: string) => {
    socket.join(roomId);
    chatNs.to(roomId).emit('user-joined', { userId, roomId });
  });

  socket.on('message', async (payload: { roomId: string; text: string }) => {
    const message = await saveMessage(payload);
    chatNs.to(payload.roomId).emit('new-message', message);
  });

  socket.on('typing', (roomId: string) => {
    socket.to(roomId).emit('user-typing', { userId });
  });

  socket.on('disconnect', () => {
    // cleanup
  });
});

httpServer.listen(3001, () => console.log('WS server on :3001'));
```

#### Next.js клиент: реюзабельный хук

```typescript
// hooks/use-socket.ts
'use client';

import { useEffect, useRef, useState, useCallback } from 'react';
import { io, type Socket } from 'socket.io-client';
import { useAuthStore } from '@/stores/auth-store';

interface UseSocketOptions {
  namespace?: string;
  enabled?: boolean;
}

interface SocketState {
  isConnected: boolean;
  transport: string | null;
}

export function useSocket({ namespace = '/', enabled = true }: UseSocketOptions = {}) {
  const socketRef = useRef<Socket | null>(null);
  const token = useAuthStore((s) => s.token);
  const [state, setState] = useState<SocketState>({
    isConnected: false,
    transport: null,
  });

  useEffect(() => {
    if (!enabled || !token) return;

    const socket = io(`${process.env.NEXT_PUBLIC_WS_URL}${namespace}`, {
      auth: { token },
      transports: ['websocket', 'polling'],
      reconnection: true,
      reconnectionAttempts: 10,
      reconnectionDelay: 1000,
      reconnectionDelayMax: 30_000,
      randomizationFactor: 0.5, // jitter
    });

    socketRef.current = socket;

    socket.on('connect', () => {
      setState({
        isConnected: true,
        transport: socket.io.engine.transport.name,
      });
    });

    socket.on('disconnect', (reason) => {
      setState({ isConnected: false, transport: null });
      // Если сервер принудительно отключил — не переподключаемся
      if (reason === 'io server disconnect') {
        socket.connect();
      }
    });

    socket.io.engine.on('upgrade', (transport) => {
      setState((s) => ({ ...s, transport: transport.name }));
    });

    return () => {
      socket.disconnect();
    };
  }, [namespace, enabled, token]);

  const emit = useCallback(<T>(event: string, data: T) => socketRef.current?.emit(event, data), []);

  const on = useCallback(<T>(event: string, handler: (data: T) => void) => {
    socketRef.current?.on(event, handler);
    return () => {
      socketRef.current?.off(event, handler);
    };
  }, []);

  return { ...state, emit, on, socket: socketRef.current };
}
```

---

### 8.4 PartyKit для совместной работы

PartyKit — платформа для multiplayer/collaborative приложений на edge. Основные преимущества:

- **Edge Computing** — серверы ближе к пользователям, низкая задержка.
- **Интеграция с CRDT** — Y.js, Automerge для бесконфликтного совместного редактирования.
- **Совместимость** — работает с Vercel, Netlify, AWS, Cloudflare.
- **Managed инфраструктура** — не нужно управлять WebSocket-серверами.

#### PartyKit сервер: комнаты с presence

```typescript
// party/document.ts
import type * as Party from 'partykit/server';

interface CursorPosition {
  x: number;
  y: number;
  userId: string;
  userName: string;
}

interface DocumentState {
  content: string;
  cursors: Record<string, CursorPosition>;
  lastUpdated: number;
}

export default class DocumentParty implements Party.Server {
  state: DocumentState = { content: '', cursors: {}, lastUpdated: 0 };

  constructor(readonly room: Party.Room) {}

  // Загрузка состояния при создании комнаты
  async onStart() {
    const stored = await this.room.storage.get<DocumentState>('state');
    if (stored) this.state = stored;
  }

  // Обработка подключений
  onConnect(conn: Party.Connection) {
    // Отправляем текущее состояние новому подключению
    conn.send(JSON.stringify({ type: 'sync', state: this.state }));
    // Уведомляем всех о новом пользователе
    this.room.broadcast(
      JSON.stringify({ type: 'user-joined', connectionId: conn.id }),
      [conn.id], // исключаем отправителя
    );
  }

  // Обработка сообщений
  async onMessage(message: string, sender: Party.Connection) {
    const parsed = JSON.parse(message);

    switch (parsed.type) {
      case 'edit':
        this.state.content = parsed.content;
        this.state.lastUpdated = Date.now();
        await this.room.storage.put('state', this.state);
        this.room.broadcast(message, [sender.id]);
        break;

      case 'cursor':
        this.state.cursors[sender.id] = parsed.position;
        this.room.broadcast(
          JSON.stringify({ type: 'cursor', id: sender.id, position: parsed.position }),
          [sender.id],
        );
        break;
    }
  }

  onClose(conn: Party.Connection) {
    delete this.state.cursors[conn.id];
    this.room.broadcast(JSON.stringify({ type: 'user-left', connectionId: conn.id }));
  }
}
```

#### Next.js клиент: хук для PartyKit

```typescript
// hooks/use-party.ts
'use client';

import usePartySocket from 'partysocket/react';
import { useState, useCallback } from 'react';

interface UseDocumentPartyOptions {
  roomId: string;
  userId: string;
  userName: string;
}

export function useDocumentParty({ roomId, userId, userName }: UseDocumentPartyOptions) {
  const [content, setContent] = useState('');
  const [cursors, setCursors] = useState<Record<string, { x: number; y: number }>>({});

  const socket = usePartySocket({
    host: process.env.NEXT_PUBLIC_PARTYKIT_HOST!,
    room: roomId,
    party: 'document',
    onMessage(event) {
      const data = JSON.parse(event.data);
      switch (data.type) {
        case 'sync':
          setContent(data.state.content);
          setCursors(data.state.cursors);
          break;
        case 'edit':
          setContent(data.content);
          break;
        case 'cursor':
          setCursors((prev) => ({ ...prev, [data.id]: data.position }));
          break;
        case 'user-left':
          setCursors((prev) => {
            const next = { ...prev };
            delete next[data.connectionId];
            return next;
          });
          break;
      }
    },
  });

  const updateContent = useCallback(
    (newContent: string) => {
      setContent(newContent);
      socket.send(JSON.stringify({ type: 'edit', content: newContent }));
    },
    [socket],
  );

  const updateCursor = useCallback(
    (x: number, y: number) => {
      socket.send(JSON.stringify({ type: 'cursor', position: { x, y, userId, userName } }));
    },
    [socket, userId, userName],
  );

  return { content, cursors, updateContent, updateCursor };
}
```

**Когда использовать PartyKit:**

- Совместное редактирование документов (Google Docs-style).
- Multiplayer-игры и интерактивные элементы.
- Cursors, presence, live-указатели.
- Whiteboard, collaborative design.

---

### 8.5 AI-стриминг (Vercel AI SDK + ReadableStream)

AI SDK 6 (2025-2026) совершил ключевой архитектурный сдвиг: вместо REST API routes используются
**Server Actions** для AI inference, обеспечивая end-to-end типобезопасность.

#### Server Action для AI-стриминга

```typescript
// app/actions/chat.ts
'use server';

import { streamText } from 'ai';
import { openai } from '@ai-sdk/openai';
import { createStreamableValue } from 'ai/rsc';

export async function chat(messages: { role: string; content: string }[]) {
  const stream = createStreamableValue('');

  (async () => {
    const result = streamText({
      model: openai('gpt-4o'),
      system: 'You are a helpful assistant.',
      messages,
    });

    for await (const delta of result.textStream) {
      stream.update(delta);
    }

    stream.done();
  })();

  return { output: stream.value };
}
```

#### Клиент: useChat для ChatGPT-style интерфейса

```typescript
// components/ai-chat.tsx
'use client';

import { useChat } from 'ai/react';

export function AIChat() {
  const {
    messages,
    input,
    handleInputChange,
    handleSubmit,
    isLoading,
    stop,
    reload,
    error,
  } = useChat({
    api: '/api/chat', // или через Server Actions в AI SDK 6
    // Дедупликация: повторные клики не отправляют дубли при стриминге
    maxSteps: 5, // разрешить до 5 вызовов инструментов
    onError: (err) => console.error('Chat error:', err),
    onFinish: (message) => {
      // Сохранение в историю, аналитика
      console.log('Completed:', message.content.length, 'chars');
    },
  });

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-y-auto space-y-4 p-4">
        {messages.map((m) => (
          <div
            key={m.id}
            className={m.role === 'user' ? 'text-right' : 'text-left'}
          >
            <div className="inline-block p-3 rounded-lg max-w-[80%]">
              {m.content}
            </div>
          </div>
        ))}
      </div>

      {error && (
        <div className="p-2 text-red-500">
          Error occurred. <button onClick={() => reload()}>Retry</button>
        </div>
      )}

      <form onSubmit={handleSubmit} className="p-4 border-t flex gap-2">
        <input
          value={input}
          onChange={handleInputChange}
          placeholder="Type a message..."
          className="flex-1 border rounded px-3 py-2"
          disabled={isLoading}
        />
        {isLoading ? (
          <button type="button" onClick={stop}>Stop</button>
        ) : (
          <button type="submit">Send</button>
        )}
      </form>
    </div>
  );
}
```

#### Низкоуровневый стриминг через Route Handler (без AI SDK)

```typescript
// app/api/chat/route.ts — для случаев, когда AI SDK не подходит
export async function POST(request: Request) {
  const { messages } = await request.json();

  const response = await fetch('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Authorization: `Bearer ${process.env.OPENAI_API_KEY}`,
    },
    body: JSON.stringify({
      model: 'gpt-4o',
      messages,
      stream: true,
    }),
  });

  // TransformStream: преобразуем OpenAI SSE в клиентский формат
  const transformStream = new TransformStream({
    transform(chunk, controller) {
      const text = new TextDecoder().decode(chunk);
      const lines = text.split('\n').filter((line) => line.startsWith('data: '));

      for (const line of lines) {
        const data = line.slice(6);
        if (data === '[DONE]') return;

        try {
          const parsed = JSON.parse(data);
          const content = parsed.choices[0]?.delta?.content;
          if (content) {
            controller.enqueue(new TextEncoder().encode(content));
          }
        } catch {
          // skip malformed chunks
        }
      }
    },
  });

  return new Response(response.body!.pipeThrough(transformStream), {
    headers: { 'Content-Type': 'text/plain; charset=utf-8' },
  });
}
```

---

### 8.6 Управляемые real-time сервисы: Pusher vs Ably vs Soketi

| Характеристика             | Pusher Channels               | Ably                                      | Soketi (self-hosted)           |
| -------------------------- | ----------------------------- | ----------------------------------------- | ------------------------------ |
| **Тип**                    | Managed cloud                 | Managed cloud                             | Open-source, self-hosted       |
| **Протокол**               | WebSocket + fallback          | WebSocket + fallback                      | WebSocket (Pusher-совместимый) |
| **Глобальная сеть**        | Один дата-центр               | Множество дата-центров                    | Зависит от хостинга            |
| **Free tier**              | 100 connections, 200K msg/day | 200 connections, 100K msg/day (6M msg/mo) | Бесплатно (свой сервер)        |
| **Starter цена**           | $49/mo (500 conn, 30M msg)    | $29/mo (более гибкие лимиты)              | $5-10/mo (облачный VPS)        |
| **Масштабирование**        | Автоматическое                | Автоматическое + global                   | Ручное (горизонтальное)        |
| **Latency (глобально)**    | Средняя (один ДЦ)             | Низкая (edge-сеть)                        | Зависит от размещения          |
| **Pusher-совместимый SDK** | Нативный                      | Нет (свой SDK)                            | Да (drop-in замена)            |
| **Message ordering**       | Не гарантируется              | Гарантируется                             | Не гарантируется               |
| **Message history**        | Нет (только real-time)        | Да (до 72ч)                               | Нет                            |
| **Webhooks**               | Да                            | Да                                        | Да                             |
| **Присутствие (presence)** | Да                            | Да                                        | Да                             |
| **TypeScript SDK**         | Да                            | Да                                        | Pusher SDK                     |

#### Когда что выбирать

| Сценарий                                   | Рекомендация | Обоснование                                               |
| ------------------------------------------ | ------------ | --------------------------------------------------------- |
| MVP / стартап (скорость выхода)            | **Pusher**   | Простейшее API, обширная документация, быстрая интеграция |
| Enterprise / глобальная аудитория          | **Ably**     | Гарантия доставки, глобальная edge-сеть, message history  |
| Бюджетный проект / full control            | **Soketi**   | Бесплатно, Pusher-совместимый, полный контроль            |
| Уже используется Pusher, нужно удешевить   | **Soketi**   | Drop-in замена, тот же SDK, минимальные изменения         |
| Высокие требования к latency в Азии/Европе | **Ably**     | Мульти-регионная инфраструктура                           |

#### Пример: Pusher в Next.js

```typescript
// lib/pusher-server.ts
import Pusher from 'pusher';

export const pusherServer = new Pusher({
  appId: process.env.PUSHER_APP_ID!,
  key: process.env.NEXT_PUBLIC_PUSHER_KEY!,
  secret: process.env.PUSHER_SECRET!,
  cluster: process.env.NEXT_PUBLIC_PUSHER_CLUSTER!,
  useTLS: true,
});
```

```typescript
// lib/pusher-client.ts
import PusherClient from 'pusher-js';

export const pusherClient = new PusherClient(process.env.NEXT_PUBLIC_PUSHER_KEY!, {
  cluster: process.env.NEXT_PUBLIC_PUSHER_CLUSTER!,
  authEndpoint: '/api/pusher/auth',
  authTransport: 'ajax',
});
```

```typescript
// hooks/use-pusher-channel.ts
'use client';

import { useEffect } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { pusherClient } from '@/lib/pusher-client';

export function usePusherChannel(channelName: string) {
  const queryClient = useQueryClient();

  useEffect(() => {
    const channel = pusherClient.subscribe(channelName);

    channel.bind('order-created', (data: unknown) => {
      queryClient.invalidateQueries({ queryKey: ['orders'] });
    });

    channel.bind('order-updated', (data: unknown) => {
      queryClient.setQueryData(['orders', (data as { id: string }).id], data);
    });

    return () => {
      channel.unbind_all();
      pusherClient.unsubscribe(channelName);
    };
  }, [channelName, queryClient]);
}
```

---

### 8.7 Оптимизация поллинга (адаптивный, exponential backoff)

Даже при наличии push-технологий, поллинг остаётся важным fallback и основным подходом для
простых сценариев. Оптимизация критична для снижения нагрузки на сервер.

#### Адаптивный поллинг с TanStack Query

```typescript
// hooks/use-adaptive-polling.ts
'use client';

import { useQuery } from '@tanstack/react-query';
import { useState, useCallback } from 'react';
import { api } from '@/lib/api-client';

interface UseAdaptivePollingOptions {
  queryKey: readonly string[];
  url: string;
  minInterval: number; // мс — минимальный интервал (активная вкладка)
  maxInterval: number; // мс — максимальный интервал (при отсутствии изменений)
  backoffFactor: number; // множитель увеличения интервала
}

export function useAdaptivePolling<T>({
  queryKey,
  url,
  minInterval = 3_000,
  maxInterval = 60_000,
  backoffFactor = 1.5,
}: UseAdaptivePollingOptions) {
  const [interval, setInterval] = useState(minInterval);
  const [unchangedCount, setUnchangedCount] = useState(0);

  const adjustInterval = useCallback(
    (hasChanges: boolean) => {
      if (hasChanges) {
        // Данные изменились — сбрасываем на минимальный интервал
        setInterval(minInterval);
        setUnchangedCount(0);
      } else {
        // Данные не изменились — увеличиваем интервал (exponential backoff)
        setUnchangedCount((prev) => prev + 1);
        setInterval((prev) => Math.min(prev * backoffFactor, maxInterval));
      }
    },
    [minInterval, maxInterval, backoffFactor],
  );

  let previousDataHash: string | null = null;

  return useQuery({
    queryKey,
    queryFn: async () => {
      const data = await api.get<T>(url);
      const currentHash = JSON.stringify(data);
      const hasChanges = previousDataHash !== null && previousDataHash !== currentHash;
      previousDataHash = currentHash;
      adjustInterval(hasChanges);
      return data;
    },
    refetchInterval: () => {
      // Добавляем jitter для предотвращения "стада" (thundering herd)
      const jitter = Math.random() * interval * 0.2; // ±20%
      return interval + jitter;
    },
    // Не поллим когда вкладка неактивна
    refetchIntervalInBackground: false,
    // Refetch при фокусе окна
    refetchOnWindowFocus: true,
  });
}
```

#### Стратегия: выбор интервала поллинга

```
┌─────────────────────────────────────────────────┐
│            ДЕРЕВО РЕШЕНИЙ ПОЛЛИНГА               │
├─────────────────────────────────────────────────┤
│                                                  │
│  Данные меняются каждую секунду?                 │
│  ├── Да → SSE или WebSocket (не поллинг)         │
│  └── Нет ↓                                       │
│                                                  │
│  Пользователь активно смотрит на данные?         │
│  ├── Да (фокус) → 3-10с интервал                 │
│  └── Нет (фон) → отключить поллинг               │
│                                                  │
│  Данные часто меняются (каталог, биржа)?         │
│  ├── Да → Адаптивный: 5с → 15с → 30с             │
│  └── Нет ↓                                       │
│                                                  │
│  Данные редко меняются (настройки, профиль)?     │
│  ├── Да → 60с+ или invalidate после мутаций      │
│  └── Нет → 15-30с базовый интервал               │
│                                                  │
│  Много одновременных пользователей?              │
│  ├── Да → Jitter обязателен (+10-20% random)     │
│  └── Нет → Фиксированный интервал достаточен     │
│                                                  │
└─────────────────────────────────────────────────┘
```

---

### 8.8 Optimistic Updates для real-time ощущения

React 19 `useOptimistic` в сочетании с Server Actions и TanStack Query создаёт мгновенный отклик UI.

#### useOptimistic + Server Action

```typescript
// components/message-list.tsx
'use client';

import { useOptimistic, useTransition } from 'react';
import { sendMessage } from '@/app/actions/chat';

interface Message {
  id: string;
  text: string;
  userId: string;
  createdAt: string;
  pending?: boolean;
}

export function MessageList({ messages }: { messages: Message[] }) {
  const [isPending, startTransition] = useTransition();

  const [optimisticMessages, addOptimistic] = useOptimistic(
    messages,
    (state: Message[], newMessage: Message) => [
      ...state,
      { ...newMessage, pending: true },
    ],
  );

  const handleSend = (text: string) => {
    const tempMessage: Message = {
      id: `temp-${Date.now()}`,
      text,
      userId: 'current-user',
      createdAt: new Date().toISOString(),
      pending: true,
    };

    startTransition(async () => {
      // Мгновенно показываем сообщение (optimistic)
      addOptimistic(tempMessage);
      // Server Action отправляет на сервер + revalidatePath
      await sendMessage(text);
      // После завершения — React заменит optimistic на реальные данные
    });
  };

  return (
    <div>
      {optimisticMessages.map((msg) => (
        <div key={msg.id} className={msg.pending ? 'opacity-60' : ''}>
          {msg.text}
          {msg.pending && <span className="text-xs text-gray-400"> sending...</span>}
        </div>
      ))}
    </div>
  );
}
```

#### TanStack Query optimistic mutation

```typescript
// hooks/use-toggle-like.ts
import { useMutation, useQueryClient } from '@tanstack/react-query';

interface Post {
  id: string;
  title: string;
  likes: number;
  isLiked: boolean;
}

export function useToggleLike(postId: string) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => api.post(`/posts/${postId}/like`),

    // Optimistic update: обновляем UI до ответа сервера
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey: ['posts', postId] });
      const previous = queryClient.getQueryData<Post>(['posts', postId]);

      queryClient.setQueryData<Post>(['posts', postId], (old) =>
        old
          ? {
              ...old,
              likes: old.isLiked ? old.likes - 1 : old.likes + 1,
              isLiked: !old.isLiked,
            }
          : old,
      );

      return { previous };
    },

    // Rollback при ошибке
    onError: (_err, _vars, context) => {
      if (context?.previous) {
        queryClient.setQueryData(['posts', postId], context.previous);
      }
    },

    // Всегда синхронизируем с сервером
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['posts', postId] });
    },
  });
}
```

---

### 8.9 Стоимостной анализ real-time сервисов

| Сервис                   | Free tier               | ~1K пользователей | ~10K пользователей   | ~100K пользователей |
| ------------------------ | ----------------------- | ----------------- | -------------------- | ------------------- |
| **SSE (свой сервер)**    | --                      | $10-20/mo (VPS)   | $50-100/mo (2-3 VPS) | $200-500/mo (k8s)   |
| **Pusher**               | 100 conn / 200K msg/day | ~$49/mo           | ~$299/mo             | $999+/mo            |
| **Ably**                 | 200 conn / 6M msg/mo    | ~$29-99/mo        | ~$199-399/mo         | Индивидуально       |
| **Soketi (self-hosted)** | Безлимит                | $5-10/mo (VPS)    | $30-60/mo (кластер)  | $100-300/mo (k8s)   |
| **PartyKit**             | 1K conn бесплатно       | ~$25/mo           | ~$100/mo             | Индивидуально       |
| **Socket.IO (свой)**     | --                      | $10-20/mo (VPS)   | $50-100/mo (+ Redis) | $200-500/mo (k8s)   |

**Формула оценки:** для managed-сервисов стоимость растёт с количеством одновременных подключений
и объёмом сообщений. Для self-hosted — с требованиями к серверам и инфраструктуре (Redis, мониторинг).

---

### 8.10 Пути миграции между технологиями

```
┌────────────────────────────────────────────────────────────────────────┐
│                    ПУТИ МИГРАЦИИ REAL-TIME                             │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ЭТАП 1 (MVP / Простые уведомления):                                   │
│  ┌─────────────────┐                                                   │
│  │  Polling         │  refetchInterval: 5000                           │
│  │  (TanStack Query)│  Минимум кода, работает везде                    │
│  └────────┬────────┘                                                   │
│           │ Нужен push (задержка неприемлема)                          │
│           ▼                                                            │
│  ЭТАП 2 (Push-уведомления):                                            │
│  ┌─────────────────┐                                                   │
│  │  SSE             │  Route Handler + EventSource                     │
│  │  (Server-Sent)   │  + TanStack Query invalidation                   │
│  └────────┬────────┘                                                   │
│           │ Нужна двусторонняя связь (чат, совместное ред.)            │
│           ▼                                                            │
│  ЭТАП 3a (Быстрый старт):      ЭТАП 3b (Полный контроль):              │
│  ┌─────────────────┐           ┌─────────────────┐                     │
│  │  Pusher / Ably  │           │  Socket.IO      │                     │
│  │  (Managed)      │           │  (свой сервер)  │                     │
│  └────────┬────────┘           └────────┬────────┘                     │
│           │ Расходы растут              │ Нужна коллаборация           │
│           ▼                             ▼                              │
│  ЭТАП 4 (Оптимизация):         ┌─────────────────┐                     │
│  ┌──────────────────┐          │  PartyKit       │                     │
│  │  Soketi          │          │  (edge + CRDT)  │                     │
│  │  (self-hosted    │          └─────────────────┘                     │
│  │   Pusher-замена) │                                                  │
│  └──────────────────┘                                                  │
│                                                                        │
│  ПРИНЦИП: начинайте с простого, мигрируйте по необходимости            │
│  Pusher → Soketi: замена SDK не нужна (совместимый протокол)           │
│  Polling → SSE: замена refetchInterval на useSSE + invalidation        │
│  SSE → WebSocket: добавление ws-сервера, SSE остаётся для уведомлений  │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 9. Рекомендуемый стек

### 9.1 Дерево решений по state management

```
┌────────────────────────────────────────────────────────────────────────┐
│               ДЕРЕВО РЕШЕНИЙ: STATE MANAGEMENT                         │
├────────────────────────────────────────────────────────────────────────┤
│                                                                        │
│  ┌─ Какие данные нужно хранить?                                        │
│  │                                                                     │
│  ├─► СЕРВЕРНЫЕ данные (API, БД, внешние сервисы)                       │
│  │   │                                                                 │
│  │   ├─ Нужны DevTools + optimistic updates + prefetch?                │
│  │   │  ├── Да → TanStack Query v5                                     │
│  │   │  └── Нет, проект маленький → SWR v2 (4 KB)                      │
│  │   │                                                                 │
│  │   ├─ Данные только для Server Components?                           │
│  │   │  └── Да → async/await + fetch (0 KB, встроенный)                │
│  │   │                                                                 │
│  │   └─ Real-time обновления?                                          │
│  │      ├── Уведомления → SSE + TanStack Query invalidation            │
│  │      ├── Чат/коллаборация → WebSocket / PartyKit                    │
│  │      └── Дашборд → Adaptive polling (TanStack Query)                │
│  │                                                                     │
│  ├─► КЛИЕНТСКИЕ данные (UI state, формы, настройки)                    │
│  │   │                                                                 │
│  │   ├─ Глобальный стейт (auth, theme, sidebar)?                       │
│  │   │  ├── Простой проект / 1-5 разработчиков → Zustand v5            │
│  │   │  ├── Много независимых атомов (фильтры, UI) → Jotai v2          │
│  │   │  └── Большая команда (10+), строгие стандарты → Redux Toolkit   │
│  │   │                                                                 │
│  │   ├─ Локальный стейт компонента?                                    │
│  │   │  └── useState / useReducer (всегда предпочтительно)             │
│  │   │                                                                 │
│  │   ├─ Стейт доступен за пределами React?                             │
│  │   │  └── Zustand (единственный выбор — getState() вне компонентов)  │
│  │   │                                                                 │
│  │   └─ Нужна персистенция (localStorage)?                             │
│  │      ├── Zustand → persist middleware                               │
│  │      └── Jotai → atomWithStorage                                    │
│  │                                                                     │
│  └─► ФОРМЫ (ввод, валидация, отправка)                                 │
│      │                                                                 │
│      ├─ Сложные формы (много полей, вложенные массивы)?                │
│      │  └── React Hook Form + Zod                                      │
│      │                                                                 │
│      ├─ Простая форма (1-3 поля)?                                      │
│      │  └── useActionState + Zod (встроенный React 19)                 │
│      │                                                                 │
│      └─ Нужен optimistic UI при отправке?                              │
│         └── useOptimistic + Server Action                              │
│                                                                        │
└────────────────────────────────────────────────────────────────────────┘
```

### Краткая таблица решений

| Сценарий                             | Решение                     | Bundle impact |
| ------------------------------------ | --------------------------- | ------------- |
| Один компонент, простой стейт        | `useState` / `useReducer`   | 0 KB          |
| Серверные данные, кэш, мутации       | TanStack Query v5           | ~13 KB        |
| Серверные данные, минимальный бандл  | SWR v2                      | ~4 KB         |
| Серверные данные в Server Components | `fetch()` + ISR             | 0 KB          |
| Глобальный клиентский стейт          | Zustand v5                  | ~1.2 KB       |
| Множество независимых атомов         | Jotai v2                    | ~2.1 KB       |
| Строгие паттерны, большая команда    | Redux Toolkit               | ~13.8 KB      |
| Сложные формы                        | React Hook Form + Zod       | ~10 KB        |
| Простые формы                        | `useActionState` (React 19) | 0 KB          |
| Обмен данными: Server → Client       | props / `HydrationBoundary` | 0 KB          |
| Context для DI (не для стейта)       | React Context               | 0 KB          |

---

### 9.2 Полная enterprise-архитектура

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     ENTERPRISE NEXT.JS ARCHITECTURE                         │
│                          (App Router 2025-2026)                             │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─── CDN / EDGE ──────────────────────────────────────────────────────┐    │
│  │  Vercel Edge Network / Cloudflare                                   │    │
│  │  ├── Static assets (ISR pages, images, fonts)                       │    │
│  │  ├── Edge Middleware (auth check, geo-redirect, A/B test)           │    │
│  │  └── Cache-Control headers (stale-while-revalidate)                 │    │
│  └──────────────────────────────┬──────────────────────────────────────┘    │
│                                 │                                           │
│  ┌─── NEXT.JS APP (SSR/RSC) ────┴──────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  ┌── Server Layer ──────────────────────────────────────────────┐   │    │
│  │  │  Server Components (async/await, 0 KB JS)                    │   │    │
│  │  │  ├── page.tsx — fetch + prefetchQuery + HydrationBoundary    │   │    │
│  │  │  ├── layout.tsx — auth session, shared data                  │   │    │
│  │  │  └── loading.tsx — Suspense fallback (streaming)             │   │    │
│  │  │                                                              │   │    │
│  │  │  Server Actions ('use server')                               │   │    │
│  │  │  ├── Мутации (CRUD) с Zod-валидацией                         │   │    │
│  │  │  ├── AI streaming (AI SDK 6 streamText)                      │   │    │
│  │  │  └── createSafeAction — auth + validation wrapper            │   │    │
│  │  │                                                              │   │    │
│  │  │  Route Handlers (app/api/)                                   │   │    │
│  │  │  ├── SSE endpoints (text/event-stream)                       │   │    │
│  │  │  ├── Webhook receivers (Stripe, GitHub)                      │   │    │
│  │  │  └── File upload / download endpoints                        │   │    │
│  │  └──────────────────────────────────────────────────────────────┘   │    │
│  │                                                                     │    │
│  │  ┌── Client Layer ─────────────────────────────────────────────┐    │    │
│  │  │  Client Components ('use client')                           │    │    │
│  │  │  ├── TanStack Query (server state, cache, mutations)        │    │    │
│  │  │  ├── Zustand (client state: auth, UI, settings)             │    │    │
│  │  │  ├── React Hook Form + Zod (forms)                          │    │    │
│  │  │  ├── useSSE / useSocket / useParty (real-time)              │    │    │
│  │  │  └── useOptimistic + useTransition (instant feedback)       │    │    │
│  │  └─────────────────────────────────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                 │                                           │
│  ┌─── DATA LAYER ───────────────┴──────────────────────────────────────┐    │
│  │                                                                     │    │
│  │  Data Access Layer (lib/data/)                                      │    │
│  │  ├── Authorization checks ближе к данным (не middleware!)           │    │
│  │  ├── Drizzle ORM / Prisma — type-safe DB access                     │    │
│  │  └── Zod schemas — shared validation (client + server)              │    │
│  │                                                                     │    │
│  │  ┌── Databases ────────────┐  ┌── Real-time Infra ──────────────┐   │    │
│  │  │  PostgreSQL (primary)   │  │  Redis / Valkey (Pub/Sub, cache)│   │    │
│  │  │  Redis (cache, sessions)│  │  SSE Route Handlers             │   │    │
│  │  │  S3 (file storage)      │  │  Socket.IO / PartyKit (ws)      │   │    │
│  │  └─────────────────────────┘  └─────────────────────────────────┘   │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
│  ┌─── OBSERVABILITY ───────────────────────────────────────────────────┐    │
│  │  OpenTelemetry (traces, spans)                                      │    │
│  │  ├── Sentry (errors + performance)                                  │    │
│  │  ├── Vercel Analytics / Speed Insights (Web Vitals)                 │    │
│  │  └── Custom metrics (TanStack Query timing, SSE health)             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

### 9.3 Финальный стек с альтернативами

| Слой                  | Основной выбор            | Альтернатива 1        | Альтернатива 2          | Когда альтернатива                                              |
| --------------------- | ------------------------- | --------------------- | ----------------------- | --------------------------------------------------------------- |
| **Server state**      | TanStack Query v5         | SWR v2                | fetch (встроен)         | SWR: минимальный бандл; fetch: только RSC                       |
| **Client state**      | Zustand v5                | Jotai v2              | Redux Toolkit           | Jotai: атомарный UI; RTK: команда 10+                           |
| **Формы**             | React Hook Form + Zod     | useActionState + Zod  | Conform                 | useActionState: простые формы; Conform: progressive enhancement |
| **HTTP-клиент**       | ky                        | ofetch (unjs)         | fetch (нативный)        | ofetch: edge runtimes; fetch: без зависимостей                  |
| **Мутации**           | Server Actions + TQ       | tRPC                  | GraphQL (urql)          | tRPC: fullstack TS monorepo; GraphQL: сложные связи данных      |
| **Кэширование**       | ISR + TQ cache            | unstable_cache + tags | SWR cache               | По сложности приложения                                         |
| **Real-time (push)**  | SSE + TQ invalidation     | Pusher / Ably         | PartyKit                | Pusher: быстрый старт; PartyKit: коллаборация                   |
| **Real-time (bidir)** | Socket.IO + Redis         | PartyKit              | Ably                    | PartyKit: edge + CRDT; Ably: managed + global                   |
| **AI streaming**      | Vercel AI SDK 6           | Raw ReadableStream    | LangChain.js            | Raw: без vendor lock-in; LangChain: complex chains              |
| **Валидация**         | Zod                       | Valibot               | ArkType                 | Valibot: tree-shakeable (~1 KB); ArkType: performance           |
| **ORM**               | Drizzle                   | Prisma                | Kysely                  | Prisma: зрелая экосистема; Kysely: SQL-first                    |
| **Auth**              | Auth.js (NextAuth v5)     | Clerk                 | Lucia                   | Clerk: managed + UI; Lucia: lightweight                         |
| **Стилизация**        | Tailwind CSS v4           | CSS Modules           | Panda CSS               | CSS Modules: без runtime; Panda: type-safe tokens               |
| **Мониторинг**        | Sentry + Vercel Analytics | Datadog               | OpenTelemetry + Grafana | Datadog: enterprise APM; OTel: self-hosted                      |

---

### 9.4 Мониторинг производительности

#### OpenTelemetry: инструментация Next.js

```typescript
// instrumentation.ts (корень проекта — Next.js автоматически подхватывает)
import { NodeSDK } from '@opentelemetry/sdk-node';
import { getNodeAutoInstrumentations } from '@opentelemetry/auto-instrumentations-node';
import { OTLPTraceExporter } from '@opentelemetry/exporter-trace-otlp-http';

export function register() {
  const sdk = new NodeSDK({
    traceExporter: new OTLPTraceExporter({
      url: process.env.OTEL_EXPORTER_OTLP_ENDPOINT,
    }),
    instrumentations: [
      getNodeAutoInstrumentations({
        // Next.js автоматически создаёт спаны для fetch, route handlers
        '@opentelemetry/instrumentation-fs': { enabled: false }, // слишком шумно
      }),
    ],
  });
  sdk.start();
}
```

#### Метрики, которые необходимо отслеживать

| Категория         | Метрика                          | Инструмент                    | Порог             |
| ----------------- | -------------------------------- | ----------------------------- | ----------------- |
| **Web Vitals**    | LCP (Largest Contentful Paint)   | Vercel Analytics / web-vitals | < 2.5с            |
| **Web Vitals**    | INP (Interaction to Next Paint)  | Vercel Analytics / web-vitals | < 200мс           |
| **Web Vitals**    | CLS (Cumulative Layout Shift)    | Vercel Analytics / web-vitals | < 0.1             |
| **Data fetching** | Время ответа API (p50, p95, p99) | OpenTelemetry spans           | p95 < 500мс       |
| **Data fetching** | TanStack Query cache hit rate    | Custom metric                 | > 80%             |
| **Data fetching** | Количество waterfall-запросов    | React DevTools Profiler       | 0 (ideal)         |
| **Real-time**     | SSE reconnection rate            | Custom counter                | < 5%/час          |
| **Real-time**     | WebSocket message latency        | Custom metric                 | < 100мс           |
| **Real-time**     | Concurrent SSE connections       | Server metric                 | По лимиту сервера |
| **Bundle**        | First Load JS                    | next build output             | < 100 KB          |
| **Bundle**        | Client component JS per route    | @next/bundle-analyzer         | < 50 KB/route     |
| **Errors**        | Unhandled error rate             | Sentry                        | < 0.1%            |
| **Server**        | Server Action duration           | OpenTelemetry                 | p95 < 1с          |

#### Кастомные метрики TanStack Query

```typescript
// lib/query-metrics.ts
'use client';

import { type QueryClient } from '@tanstack/react-query';

export function setupQueryMetrics(queryClient: QueryClient) {
  // Подписка на все события кэша
  const queryCache = queryClient.getQueryCache();

  queryCache.subscribe((event) => {
    if (event.type === 'updated' && event.action.type === 'success') {
      const query = event.query;
      const fetchTime =
        query.state.dataUpdatedAt -
        (query.state.fetchFailureCount > 0
          ? query.state.errorUpdatedAt
          : query.state.dataUpdatedAt - 1);

      // Отправляем в аналитику
      reportMetric({
        name: 'tanstack_query_fetch_duration',
        value: fetchTime,
        tags: {
          queryKey: JSON.stringify(query.queryKey).slice(0, 100),
          status: query.state.status,
          fromCache: String(query.state.dataUpdateCount > 1),
        },
      });
    }

    if (event.type === 'updated' && event.action.type === 'error') {
      reportMetric({
        name: 'tanstack_query_error',
        value: 1,
        tags: {
          queryKey: JSON.stringify(event.query.queryKey).slice(0, 100),
          error: String(event.action.error),
        },
      });
    }
  });
}

function reportMetric(metric: { name: string; value: number; tags: Record<string, string> }) {
  // Интеграция с вашей системой мониторинга
  // Datadog, Sentry, custom OpenTelemetry exporter и т.д.
  if (typeof window !== 'undefined' && 'sendBeacon' in navigator) {
    navigator.sendBeacon('/api/metrics', JSON.stringify(metric));
  }
}
```

#### Web Vitals: клиентский сбор

```typescript
// app/providers.tsx — добавить в Providers
'use client';

import { useReportWebVitals } from 'next/web-vitals';

export function WebVitalsReporter() {
  useReportWebVitals((metric) => {
    // Отправка в аналитику (Vercel Analytics делает это автоматически)
    const body = {
      name: metric.name, // LCP, INP, CLS, FCP, TTFB
      value: metric.value,
      rating: metric.rating, // 'good' | 'needs-improvement' | 'poor'
      id: metric.id,
      page: window.location.pathname,
    };

    // Используем sendBeacon для гарантированной отправки (даже при закрытии вкладки)
    if (navigator.sendBeacon) {
      navigator.sendBeacon('/api/vitals', JSON.stringify(body));
    }
  });

  return null;
}
```

---

### 9.5 Архитектура проекта

```
src/
├── app/                              # Next.js App Router
│   ├── (auth)/                       # Route group: аутентификация
│   │   ├── login/page.tsx
│   │   └── register/page.tsx
│   ├── (dashboard)/                  # Route group: основное приложение
│   │   ├── layout.tsx                # Sidebar, nav (Server Component)
│   │   ├── page.tsx                  # Dashboard home
│   │   ├── orders/
│   │   │   ├── page.tsx              # SSR + prefetchQuery
│   │   │   ├── [id]/page.tsx         # Dynamic route
│   │   │   └── loading.tsx           # Streaming skeleton
│   │   └── settings/page.tsx
│   ├── api/                          # Route Handlers
│   │   ├── events/route.ts           # SSE endpoint
│   │   ├── webhooks/stripe/route.ts  # Webhook receiver
│   │   ├── pusher/auth/route.ts      # Pusher auth endpoint
│   │   └── metrics/route.ts          # Custom metrics receiver
│   ├── actions/                      # Server Actions
│   │   ├── orders.ts
│   │   ├── chat.ts                   # AI streaming
│   │   └── auth.ts
│   ├── providers.tsx                 # QueryClient, Theme, WebVitals
│   └── layout.tsx                    # Root layout
├── components/
│   ├── ui/                           # Базовые (Button, Input, Modal, Card)
│   ├── features/                     # Бизнес-компоненты (OrderTable, ChatWindow)
│   └── providers/                    # Context providers
├── hooks/
│   ├── queries/                      # TanStack Query hooks (use-orders.ts)
│   ├── mutations/                    # TanStack Mutation hooks (use-create-order.ts)
│   ├── use-sse.ts                    # SSE подключение
│   ├── use-socket.ts                 # WebSocket подключение
│   ├── use-party.ts                  # PartyKit подключение
│   └── use-adaptive-polling.ts       # Адаптивный поллинг
├── stores/                           # Zustand stores
│   ├── auth-store.ts                 # Аутентификация
│   ├── ui-store.ts                   # UI state (sidebar, modals)
│   └── settings-store.ts            # Пользовательские настройки
├── lib/
│   ├── api-client.ts                 # ky instance с interceptors
│   ├── query-client.ts               # TanStack Query client factory
│   ├── pusher-server.ts              # Pusher server instance
│   ├── pusher-client.ts              # Pusher client instance
│   ├── schemas/                      # Zod-схемы (клиент + сервер)
│   │   ├── order.ts
│   │   ├── user.ts
│   │   └── common.ts
│   ├── safe-action.ts                # Обёртка безопасных Server Actions
│   └── data/                         # Data Access Layer
│       ├── orders.ts                 # DB queries + authorization
│       └── users.ts
├── types/                            # Общие TypeScript типы
│   ├── api.ts                        # API response types
│   └── domain.ts                     # Domain entities
└── instrumentation.ts                # OpenTelemetry setup
```

---

## Источники

- [Server-Sent Events don't work in Next API routes — GitHub Discussion](https://github.com/vercel/next.js/discussions/48427)
- [Real-Time Notifications with SSE in Next.js — Pedro Alonso](https://www.pedroalonso.net/blog/sse-nextjs-real-time-notifications/)
- [Fixing Slow SSE Streaming in Next.js and Vercel — Medium](https://medium.com/@oyetoketoby80/fixing-slow-sse-server-sent-events-streaming-in-next-js-and-vercel-99f42fbdb996)
- [Using SSE to stream LLM responses in Next.js — Upstash Blog](https://upstash.com/blog/sse-streaming-llm-responses)
- [How to use with Next.js — Socket.IO](https://socket.io/how-to/use-with-nextjs)
- [How to Handle WebSocket in Next.js — OneUptime](https://oneuptime.com/blog/post/2026-01-24-nextjs-websocket-handling/view)
- [PartyKit — Real-time Multiplayer Platform](https://www.partykit.io/)
- [Add PartyKit to a Next.js app — PartyKit Docs](https://docs.partykit.io/tutorials/add-partykit-to-a-nextjs-app/)
- [Pusher vs Ably vs PubNub Comparison 2026 — index.dev](https://www.index.dev/skill-vs-skill/pusher-vs-ably-vs-pubnub)
- [Ably vs Pusher 2026 — Ably](https://ably.com/compare/ably-vs-pusher)
- [Pusher pricing 2025 — Ably](https://ably.com/topic/pusher-pricing)
- [Soketi — Open-source WebSocket server — GitHub](https://github.com/soketi/soketi)
- [TanStack Query: Query Invalidation — Docs](https://tanstack.com/query/v5/docs/framework/react/guides/query-invalidation)
- [TanStack Query: Optimistic Updates — Docs](https://tanstack.com/query/v5/docs/react/guides/optimistic-updates)
- [Vercel AI SDK 6: Streaming Chat — DigitalApplied](https://www.digitalapplied.com/blog/vercel-ai-sdk-6-streaming-chat-nextjs-guide)
- [Real-time AI in Next.js: Streaming with Vercel AI SDK — LogRocket](https://blog.logrocket.com/nextjs-vercel-ai-sdk-streaming/)
- [AI SDK: Stream Text — Cookbook](https://ai-sdk.dev/cookbook/next/stream-text)
- [useOptimistic — React Docs](https://react.dev/reference/react/useOptimistic)
- [Implement Optimistic UI in Next.js — egghead.io](https://egghead.io/lessons/next-js-implement-optimistic-ui-with-the-react-useoptimistic-hook-in-next-js)
- [Modern Full Stack Architecture Using Next.js 15+ — SoftwareMill](https://softwaremill.com/modern-full-stack-application-architecture-using-next-js-15/)
- [React Stack Patterns 2026 — patterns.dev](https://www.patterns.dev/react/react-2026/)
- [Next.js State Management: Zustand vs Jotai — BetterLink Blog](https://eastondev.com/blog/en/posts/dev/20251219-nextjs-state-management/)
- [React State Management in 2025 — developerway.com](https://www.developerway.com/posts/react-state-management-2025)
- [State Management Trends in React 2025 — Makers Den](https://makersden.io/blog/react-state-management-in-2025)
- [OpenTelemetry Guide — Next.js Docs](https://nextjs.org/docs/app/guides/open-telemetry)
- [Next.js Performance Optimisation 2025 — Pagepro](https://pagepro.co/blog/nextjs-performance-optimization-in-9-steps/)
- [Sentry for Next.js — Monitoring](https://sentry.io/for/nextjs/)
- [Scaling Responsibly: Smarter API Requests with React Query — Medium](https://medium.com/@karamarkonikolina/scaling-responsibly-smarter-api-requests-with-react-query-apollo-client-part-2-4cef233454a3)
- [Server-Sent Events — MDN](https://developer.mozilla.org/en-US/docs/Web/API/Server-sent_events/Using_server-sent_events)
- [EventSource Automatic Reconnection — javascript.info](https://javascript.info/server-sent-events)
- [Reconnecting EventSource — GitHub (fanout)](https://github.com/fanout/reconnecting-eventsource)
